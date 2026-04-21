from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


_CLASSIFICATION_BANDS = (
    (70, "실행검토"),
    (55, "매수대기"),
    (40, "후보"),
    (25, "관찰"),
    (0, "제외"),
)


@dataclass
class ExecutionIntradayState:
    ticker: str
    execution_score: float = 0.0
    execution_intraday_score: float = 0.0
    intraday_classification: str = "관찰"
    last_intraday_update_at: str | None = None
    score_change_reasons: list[str] = field(default_factory=list)
    intraday_event_history: list[dict[str, Any]] = field(default_factory=list)
    last_event_fingerprint: str | None = None


class ExecutionScoreEngine:
    """장중 입력을 임시 실행점수로 변환한다.

    - 장중 임시 점수(execution_intraday_score)는 장후 확정 execution_score와 분리 유지한다.
    - 같은 신호 반복으로 과도 갱신되지 않도록 fingerprint 기준 중복 방지를 적용한다.
    """

    def apply_intraday_payload(
        self,
        payload: dict[str, Any],
        previous: ExecutionIntradayState | None = None,
    ) -> ExecutionIntradayState:
        ticker = payload.get("ticker") or "UNKNOWN"
        market_phase = payload.get("market_phase")

        state = previous or ExecutionIntradayState(ticker=ticker)
        if payload.get("execution_score") is not None:
            state.execution_score = float(payload["execution_score"])
        if previous is None and state.execution_intraday_score == 0.0:
            state.execution_intraday_score = state.execution_score

        if market_phase != "intraday":
            return state

        features = payload.get("features") or {}
        fingerprint = self._fingerprint(features)
        if fingerprint == state.last_event_fingerprint:
            return state

        delta, reasons = self._score_delta(features)
        if delta == 0:
            return state

        before = state.execution_intraday_score
        after = max(0.0, min(100.0, before + delta))
        state.execution_intraday_score = after
        state.intraday_classification = classify_execution_score(after)
        state.last_intraday_update_at = _now_iso()
        state.score_change_reasons = reasons
        state.last_event_fingerprint = fingerprint

        state.intraday_event_history.append(
            {
                "at": state.last_intraday_update_at,
                "delta": delta,
                "before": before,
                "after": after,
                "reasons": reasons,
                "features": features,
            }
        )
        state.intraday_event_history = state.intraday_event_history[-10:]
        return state

    @staticmethod
    def _fingerprint(features: dict[str, Any]) -> str:
        return "|".join(
            [
                str(bool(features.get("breakout_detected"))),
                str(bool(features.get("trading_value_spike"))),
                str(round(float(features.get("trade_strength_change") or 0.0), 1)),
                str(features.get("leader_follower_alignment_hint") or "mixed"),
            ]
        )

    @staticmethod
    def _score_delta(features: dict[str, Any]) -> tuple[float, list[str]]:
        delta = 0.0
        reasons: list[str] = []

        if bool(features.get("breakout_detected")):
            delta += 12.0
            reasons.append("breakout_detected:+12")

        if bool(features.get("trading_value_spike")):
            delta += 10.0
            reasons.append("trading_value_spike:+10")

        strength = float(features.get("trade_strength_change") or 0.0)
        if strength >= 120.0:
            delta += 8.0
            reasons.append("trade_strength_change>=120:+8")
        elif 0 < strength <= 85.0:
            delta -= 8.0
            reasons.append("trade_strength_change<=85:-8")

        alignment_hint = features.get("leader_follower_alignment_hint")
        if alignment_hint == "aligned":
            delta += 5.0
            reasons.append("leader_follower_alignment_hint=aligned:+5")
        elif alignment_hint == "lagging":
            delta -= 4.0
            reasons.append("leader_follower_alignment_hint=lagging:-4")

        return delta, reasons


def classify_execution_score(score: float) -> str:
    for min_score, label in _CLASSIFICATION_BANDS:
        if score >= min_score:
            return label
    return "제외"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
