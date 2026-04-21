from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

from src.services.execution_score_engine import ExecutionScoreEngine
from src.services.execution_score_state_service import ExecutionScoreStateService
from src.services.realtime_state_service import RealtimeStateService
from src.services.intraday_board_state_service import IntradayBoardStateService
from src.services.signal_merger import SignalMerger
from src.services.watchlist_service import WatchlistService

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None


@dataclass(frozen=True)
class KISWebsocketConfig:
    app_key: str
    app_secret: str
    approval_key: str
    ws_url: str = "ws://ops.koreainvestment.com:21000"
    reconnect_delay_sec: int = 5
    max_reconnect_delay_sec: int = 60
    channels: tuple[str, ...] = ("execution", "orderbook", "trading_value")


class KISWebsocketBridge:
    """KIS websocket 실시간 수신 브릿지.

    이번 단계는 자동주문 없이 실시간 감시 상태/점수 입력 반영 기반만 제공한다.
    """

    def __init__(self, root_dir: Path, config: KISWebsocketConfig) -> None:
        self.root_dir = root_dir
        self.config = config
        self.watchlist_service = WatchlistService(root_dir)
        self.state_service = RealtimeStateService(root_dir)
        self.execution_score_engine = ExecutionScoreEngine()
        self.execution_score_state_service = ExecutionScoreStateService(root_dir)
        self.signal_merger = SignalMerger()
        self.intraday_board_state_service = IntradayBoardStateService(root_dir)
        self.logger = self._build_logger(root_dir)

    @staticmethod
    def _build_logger(root_dir: Path) -> logging.Logger:
        log_dir = root_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "websocket_bridge.log"

        logger = logging.getLogger("kis_websocket_bridge")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            logger.addHandler(handler)
        return logger

    async def run_forever(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets 패키지가 필요합니다. requirements.txt에 추가 후 설치하세요.")

        backoff = self.config.reconnect_delay_sec
        state = self.state_service.load()
        score_states = self.execution_score_state_service.load_all()

        while True:
            try:
                self.logger.info("KIS websocket 연결 시도: %s", self.config.ws_url)
                async with websockets.connect(self.config.ws_url, ping_interval=20, ping_timeout=10) as ws:
                    state = self.state_service.mark_connected(state)
                    backoff = self.config.reconnect_delay_sec
                    await self._subscribe_watchlist(ws, state)
                    await self._listen(ws, state, score_states)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("연결/수신 중 오류 발생: %s", exc)
                state = self.state_service.mark_disconnected(state, error=str(exc))
                state = self.state_service.increment_reconnect(state)
                self.logger.info("%s초 후 재연결 시도", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.config.max_reconnect_delay_sec)

    async def _subscribe_watchlist(self, ws: Any, state: Any) -> None:
        items = self.watchlist_service.load_watch_items()
        if not items:
            self.logger.warning("watchlist 종목이 없어 websocket 구독을 건너뜁니다.")
            return

        for item in items:
            for channel in self.config.channels:
                payload = self._build_subscribe_payload(item.ticker, channel)
                await ws.send(json.dumps(payload, ensure_ascii=False))
                self.logger.info("구독 요청: ticker=%s channel=%s", item.ticker, channel)
            state = self.state_service.update_subscription(state, item.ticker, list(self.config.channels))

    async def _listen(self, ws: Any, state: Any, score_states: dict[str, Any]) -> None:
        async for raw_message in ws:
            parsed = self._parse_message(raw_message)
            if not parsed:
                continue

            ticker = parsed.get("ticker", "unknown")
            state = self.state_service.append_message(state, ticker, parsed)
            score_input = self._to_execution_score_input(parsed)
            intraday_state = self.execution_score_engine.apply_intraday_payload(
                score_input,
                previous=score_states.get(ticker),
            )
            score_states[ticker] = intraday_state
            self.execution_score_state_service.save_all(score_states)

            market_phase = score_input.get("market_phase", "intraday")
            merged_view = self.signal_merger.merge_for_phase(
                board_item={"ticker": ticker},
                market_phase=market_phase,
                intraday_state=intraday_state,
            )
            merged_items = [
                self.signal_merger.merge_for_phase(
                    board_item={"ticker": state_ticker},
                    market_phase=market_phase,
                    intraday_state=state_value,
                )
                for state_ticker, state_value in score_states.items()
            ]
            intraday_board = self.signal_merger.build_intraday_board(merged_items, market_phase=market_phase)
            self.intraday_board_state_service.save(intraday_board)

            self.logger.info(
                "수신 ticker=%s channel=%s intraday_signal=%s score_input=%s intraday_score=%.2f intraday_classification=%s reasons=%s",
                ticker,
                parsed.get("channel"),
                score_input.get("intraday_signal_type"),
                json.dumps(score_input, ensure_ascii=False),
                intraday_state.execution_intraday_score,
                merged_view.get("intraday_classification"),
                ",".join(intraday_state.score_change_reasons),
            )

    def _build_subscribe_payload(self, ticker: str, channel: str) -> dict[str, Any]:
        return {
            "header": {
                "approval_key": self.config.approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": self._tr_id_for_channel(channel),
                    "tr_key": ticker,
                }
            },
        }

    @staticmethod
    def _tr_id_for_channel(channel: str) -> str:
        mapping = {
            "execution": "H0STCNT0",      # 체결
            "orderbook": "H0STASP0",      # 호가
            "trading_value": "H0STCNT0",  # 체결 기반 누적 거래대금 계산
        }
        return mapping[channel]

    def _parse_message(self, raw_message: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            self.logger.debug("JSON 파싱 실패 메시지 스킵")
            return None

        body = payload.get("body") or {}
        output = body.get("output") or {}
        ticker = output.get("stck_shrn_iscd") or output.get("tr_key")

        return {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "channel": self._infer_channel(payload),
            "price": _to_float(output.get("stck_prpr")),
            "change_rate": _to_float(output.get("prdy_ctrt")),
            "trade_strength": _to_float(output.get("tday_rltv")),
            "acc_trading_value": _to_float(output.get("acml_tr_pbmn")),
            "ask_total": _to_float(output.get("total_askp_rsqn")),
            "bid_total": _to_float(output.get("total_bidp_rsqn")),
            "raw": payload,
        }

    @staticmethod
    def _infer_channel(payload: dict[str, Any]) -> str:
        tr_id = (((payload.get("body") or {}).get("input") or {}).get("tr_id") or "")
        if tr_id == "H0STASP0":
            return "orderbook"
        return "execution"

    def _to_execution_score_input(self, parsed: dict[str, Any]) -> dict[str, Any]:
        trading_value = parsed.get("acc_trading_value") or 0.0
        trade_strength = parsed.get("trade_strength") or 0.0
        ask_total = parsed.get("ask_total") or 0.0
        bid_total = parsed.get("bid_total") or 0.0

        return {
            "market_phase": "intraday",
            "ticker": parsed.get("ticker"),
            "intraday_signal_type": "temporary",
            "features": {
                "breakout_detected": bool((parsed.get("change_rate") or 0.0) >= 2.0),
                "trading_value_spike": bool(trading_value >= 1_000_000_000),
                "trade_strength_change": trade_strength,
                "leader_follower_alignment_hint": "aligned" if bid_total >= ask_total else "mixed",
            },
            "source": {
                "channel": parsed.get("channel"),
                "received_at": parsed.get("received_at"),
            },
        }


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
