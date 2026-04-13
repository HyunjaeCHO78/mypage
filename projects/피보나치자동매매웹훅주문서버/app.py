import hashlib
import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

try:
    from eth_account import Account
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
except Exception:  # SDK optional for DRY_RUN mode
    Account = None
    Exchange = None
    Info = None

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8787"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
ENABLE_TRADING = os.getenv("ENABLE_TRADING", "false").lower() == "true"
SYMBOLS_ALLOWED = [s.strip().upper() for s in os.getenv("SYMBOLS_ALLOWED", "BTC").split(",") if s.strip()]
TIMEFRAME = os.getenv("TIMEFRAME", "")
STRATEGY_NAME = os.getenv("STRATEGY_NAME", "")
POSITION_SIZE_PCT = float(os.getenv("POSITION_SIZE_PCT", "10"))
MAX_ORDER_USD = float(os.getenv("MAX_ORDER_USD", "100"))
DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "1"))
HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
HYPERLIQUID_ACCOUNT_ADDRESS = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "")
HYPERLIQUID_TESTNET = os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true"
LOG_PATH = Path(os.getenv("LOG_PATH", "trade_logs.jsonl"))
POSITION_STATE_PATH = Path(os.getenv("POSITION_STATE_PATH", "position_state.json"))
DEDUPE_STATE_PATH = Path(os.getenv("DEDUPE_STATE_PATH", "dedupe_state.json"))
MAX_DEDUP_KEYS = int(os.getenv("MAX_DEDUP_KEYS", "2000"))

ALL_ACTIONS = {
    "LONG_ENTRY",
    "LONG_CLOSE",
    "SHORT_ENTRY",
    "SHORT_CLOSE",
    "LONG_REVERSE_TO_SHORT",
    "SHORT_REVERSE_TO_LONG",
}

APP_LOCK = threading.Lock()
app = Flask(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_log(record: Dict[str, Any]) -> None:
    ensure_parent(LOG_PATH)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def make_dedupe_key(payload: Dict[str, Any]) -> str:
    explicit = payload.get("dedupe_key") or payload.get("signal_id")
    if explicit:
        return str(explicit)

    src = {
        "action": payload.get("action", ""),
        "symbol": payload.get("symbol", ""),
        "strategy": payload.get("strategy", payload.get("strategy_name", "")),
        "timeframe": payload.get("timeframe", ""),
        "bar_time": payload.get("bar_time", payload.get("timestamp", "")),
        "price": payload.get("price", ""),
    }
    raw = json.dumps(src, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_dedupe_queue() -> Deque[str]:
    data = load_json(DEDUPE_STATE_PATH, {"keys": []})
    keys = data.get("keys", []) if isinstance(data, dict) else []
    return deque(keys[-MAX_DEDUP_KEYS :], maxlen=MAX_DEDUP_KEYS)


def save_dedupe_queue(queue: Deque[str]) -> None:
    save_json(DEDUPE_STATE_PATH, {"keys": list(queue)})


def parse_and_validate_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    action = str(payload.get("action", "")).strip().upper()
    symbol = str(payload.get("symbol", "BTC")).strip().upper().replace("/USDT", "")
    timeframe = str(payload.get("timeframe", TIMEFRAME)).strip()
    strategy_name = str(payload.get("strategy_name", payload.get("strategy", STRATEGY_NAME))).strip()

    if action not in ALL_ACTIONS:
        return {}, f"invalid action: {action}"
    if symbol not in SYMBOLS_ALLOWED:
        return {}, f"symbol not allowed: {symbol}"

    normalized = {
        "action": action,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_name": strategy_name,
        "price": float(payload.get("price", 0.0) or 0.0),
        "timestamp": payload.get("timestamp") or utc_now_iso(),
        "raw": payload,
    }
    return normalized, None


class HyperliquidClient:
    def __init__(self) -> None:
        self.base_url = "https://api.hyperliquid-testnet.xyz" if HYPERLIQUID_TESTNET else "https://api.hyperliquid.xyz"
        self.ready = False
        self.info = None
        self.exchange = None
        self.account_address = HYPERLIQUID_ACCOUNT_ADDRESS
        self.error = ""

        if DRY_RUN:
            self.error = "dry-run mode"
            return
        if not ENABLE_TRADING:
            self.error = "ENABLE_TRADING=false"
            return
        if not HYPERLIQUID_PRIVATE_KEY or not HYPERLIQUID_ACCOUNT_ADDRESS:
            self.error = "missing api credentials"
            return
        if Account is None or Exchange is None or Info is None:
            self.error = "hyperliquid sdk or eth-account not installed"
            return

        try:
            wallet = Account.from_key(HYPERLIQUID_PRIVATE_KEY)
            self.info = Info(self.base_url, skip_ws=True)
            self.exchange = Exchange(wallet, self.base_url, account_address=HYPERLIQUID_ACCOUNT_ADDRESS)
            self.ready = True
        except Exception as exc:
            self.error = f"init failed: {exc}"

    def get_mid_price(self, symbol: str) -> float:
        mids = self.info.all_mids()
        px = mids.get(symbol)
        if px is None:
            raise ValueError(f"mid price missing for symbol {symbol}")
        return float(px)

    def get_account_value(self) -> float:
        state = self.info.user_state(self.account_address)
        margin = state.get("marginSummary", {})
        return float(margin.get("accountValue", 0.0) or 0.0)

    def get_position(self, symbol: str) -> Dict[str, Any]:
        state = self.info.user_state(self.account_address)
        for p in state.get("assetPositions", []):
            pos = p.get("position", {})
            coin = str(pos.get("coin", "")).upper()
            if coin != symbol:
                continue
            size = float(pos.get("szi", 0.0) or 0.0)
            entry_px = float(pos.get("entryPx", 0.0) or 0.0)
            side = "LONG" if size > 0 else "SHORT" if size < 0 else "FLAT"
            return {"side": side, "size": abs(size), "signed_size": size, "entry_price": entry_px}
        return {"side": "FLAT", "size": 0.0, "signed_size": 0.0, "entry_price": 0.0}

    def set_leverage(self, symbol: str, leverage: int) -> None:
        if leverage > 0:
            self.exchange.update_leverage(leverage, symbol)

    def _extract_price(self, resp: Dict[str, Any], fallback: float) -> float:
        status = resp.get("response", {}).get("data", {}).get("statuses", [])
        for st in status:
            if "filled" in st:
                fill = st["filled"]
                return float(fill.get("avgPx", fallback) or fallback)
            if "resting" in st:
                rest = st["resting"]
                return float(rest.get("px", fallback) or fallback)
        return fallback

    def place_market_order(self, symbol: str, is_buy: bool, size: float, reduce_only: bool) -> Dict[str, Any]:
        if size <= 0:
            return {"ok": False, "error": "size <= 0"}

        mid = self.get_mid_price(symbol)
        slippage = 1.01 if is_buy else 0.99
        ioc_px = round(mid * slippage, 6)

        order_resp = self.exchange.order(
            name=symbol,
            is_buy=is_buy,
            sz=round(size, 6),
            limit_px=ioc_px,
            order_type={"limit": {"tif": "Ioc"}},
            reduce_only=reduce_only,
        )

        ok = bool(order_resp.get("status") == "ok")
        exec_px = self._extract_price(order_resp, fallback=mid)
        return {
            "ok": ok,
            "symbol": symbol,
            "is_buy": is_buy,
            "size": size,
            "reduce_only": reduce_only,
            "request_price": ioc_px,
            "executed_price": exec_px,
            "raw_response": order_resp,
        }


def calc_order_usd(client: HyperliquidClient) -> float:
    cap = max(MAX_ORDER_USD, 0.0)
    if POSITION_SIZE_PCT <= 0:
        return cap

    if client.ready:
        try:
            equity_usd = client.get_account_value()
            pct_usd = equity_usd * (POSITION_SIZE_PCT / 100.0)
            if cap > 0:
                return min(cap, pct_usd)
            return pct_usd
        except Exception:
            return cap
    return cap


def update_local_state(position_state: Dict[str, Any], symbol: str, side: str, size: float, price: float) -> Dict[str, Any]:
    position_state["positions"] = position_state.get("positions", {})
    position_state["positions"][symbol] = {
        "side": side,
        "size": round(size, 8),
        "last_price": price,
        "updated_at": utc_now_iso(),
    }
    position_state["updated_at"] = utc_now_iso()
    return position_state


def execute_action(normalized: Dict[str, Any], client: HyperliquidClient, position_state: Dict[str, Any]) -> Dict[str, Any]:
    action = normalized["action"]
    symbol = normalized["symbol"]

    result: Dict[str, Any] = {
        "ok": True,
        "action": action,
        "symbol": symbol,
        "orders": [],
        "notes": [],
    }

    try:
        current = client.get_position(symbol) if client.ready else position_state.get("positions", {}).get(symbol, {"side": "FLAT", "size": 0.0})
        side = current.get("side", "FLAT")
        size = float(current.get("size", 0.0) or 0.0)

        order_usd = calc_order_usd(client)
        if order_usd <= 0 and action.endswith("ENTRY"):
            raise ValueError("order_usd is 0. Set MAX_ORDER_USD or POSITION_SIZE_PCT.")

        if client.ready:
            client.set_leverage(symbol, DEFAULT_LEVERAGE)
            px = client.get_mid_price(symbol)
        else:
            px = normalized.get("price", 0.0) or 0.0

        entry_size = round(order_usd / px, 6) if px > 0 else 0.0

        def maybe_order(is_buy: bool, sz: float, reduce_only: bool) -> Dict[str, Any]:
            if DRY_RUN or not ENABLE_TRADING:
                return {
                    "ok": True,
                    "dry_run": True,
                    "symbol": symbol,
                    "is_buy": is_buy,
                    "size": sz,
                    "reduce_only": reduce_only,
                    "executed_price": px,
                    "raw_response": {"status": "dry_run"},
                }
            return client.place_market_order(symbol, is_buy, sz, reduce_only)

        if action == "LONG_ENTRY":
            if side == "SHORT" and size > 0:
                result["orders"].append(maybe_order(True, size, True))
                side, size = "FLAT", 0.0
            result["orders"].append(maybe_order(True, entry_size, False))
            side, size = "LONG", entry_size

        elif action == "LONG_CLOSE":
            if side != "LONG" or size <= 0:
                result["notes"].append("no-op: no long position")
            else:
                result["orders"].append(maybe_order(False, size, True))
                side, size = "FLAT", 0.0

        elif action == "SHORT_ENTRY":
            if side == "LONG" and size > 0:
                result["orders"].append(maybe_order(False, size, True))
                side, size = "FLAT", 0.0
            result["orders"].append(maybe_order(False, entry_size, False))
            side, size = "SHORT", entry_size

        elif action == "SHORT_CLOSE":
            if side != "SHORT" or size <= 0:
                result["notes"].append("no-op: no short position")
            else:
                result["orders"].append(maybe_order(True, size, True))
                side, size = "FLAT", 0.0

        elif action == "LONG_REVERSE_TO_SHORT":
            if side == "LONG" and size > 0:
                result["orders"].append(maybe_order(False, size, True))
            elif side == "SHORT":
                result["notes"].append("existing short kept; adding new short entry")
            result["orders"].append(maybe_order(False, entry_size, False))
            side, size = "SHORT", entry_size

        elif action == "SHORT_REVERSE_TO_LONG":
            if side == "SHORT" and size > 0:
                result["orders"].append(maybe_order(True, size, True))
            elif side == "LONG":
                result["notes"].append("existing long kept; adding new long entry")
            result["orders"].append(maybe_order(True, entry_size, False))
            side, size = "LONG", entry_size

        for ord_res in result["orders"]:
            if not ord_res.get("ok", False):
                raise RuntimeError(f"order failed: {ord_res}")

        result["position_after"] = {"side": side, "size": size}
        update_local_state(position_state, symbol, side, size, px)
        result["executed_price"] = px
        return result

    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)
        return result


@app.get("/health")
def health() -> Any:
    return jsonify(
        {
            "ok": True,
            "time": utc_now_iso(),
            "dry_run": DRY_RUN,
            "enable_trading": ENABLE_TRADING,
            "symbols_allowed": SYMBOLS_ALLOWED,
        }
    )


@app.post("/webhook")
def webhook() -> Any:
    payload = request.get_json(silent=True) or {}
    now = utc_now_iso()

    with APP_LOCK:
        position_state = load_json(POSITION_STATE_PATH, {"positions": {}, "updated_at": now})
        dedupe_queue = load_dedupe_queue()

        normalized, err = parse_and_validate_payload(payload)
        dedupe_key = make_dedupe_key(payload if payload else normalized)

        if dedupe_key in dedupe_queue:
            log_rec = {
                "time": now,
                "status": "deduped",
                "dedupe_key": dedupe_key,
                "payload": payload,
            }
            append_log(log_rec)
            return jsonify({"ok": True, "deduped": True, "dedupe_key": dedupe_key})

        if err:
            log_rec = {
                "time": now,
                "status": "invalid_payload",
                "error": err,
                "payload": payload,
            }
            append_log(log_rec)
            return jsonify({"ok": False, "error": err}), 400

        client = HyperliquidClient()
        exec_result = execute_action(normalized, client, position_state)

        dedupe_queue.append(dedupe_key)
        save_dedupe_queue(dedupe_queue)
        save_json(POSITION_STATE_PATH, position_state)

        log_rec = {
            "time": now,
            "status": "ok" if exec_result.get("ok") else "error",
            "dedupe_key": dedupe_key,
            "config": {
                "dry_run": DRY_RUN,
                "enable_trading": ENABLE_TRADING,
                "testnet": HYPERLIQUID_TESTNET,
                "max_order_usd": MAX_ORDER_USD,
                "position_size_pct": POSITION_SIZE_PCT,
                "default_leverage": DEFAULT_LEVERAGE,
            },
            "normalized": normalized,
            "execution": exec_result,
            "payload": payload,
        }
        if not client.ready and not DRY_RUN:
            log_rec["client_error"] = client.error

        append_log(log_rec)

        code = 200 if exec_result.get("ok") else 500
        return jsonify({"ok": exec_result.get("ok"), "result": exec_result, "dedupe_key": dedupe_key}), code


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
