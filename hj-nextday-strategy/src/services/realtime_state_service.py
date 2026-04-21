from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any


@dataclass
class RealtimeState:
    market_phase: str = "intraday"
    is_connected: bool = False
    last_connected_at: str | None = None
    last_message_at: str | None = None
    subscriptions: dict[str, dict[str, Any]] = field(default_factory=dict)
    recent_messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_error: dict[str, Any] | None = None
    reconnect_count: int = 0


class RealtimeStateService:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.state_path = root_dir / "data" / "state" / "websocket_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> RealtimeState:
        if not self.state_path.exists():
            state = RealtimeState()
            self.save(state)
            return state
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return RealtimeState(**payload)

    def save(self, state: RealtimeState) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(state.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.state_path)

    def mark_connected(self, state: RealtimeState) -> RealtimeState:
        state.is_connected = True
        state.last_connected_at = self._now_iso()
        self.save(state)
        return state

    def mark_disconnected(self, state: RealtimeState, error: str | None = None) -> RealtimeState:
        state.is_connected = False
        if error:
            state.last_error = {"timestamp": self._now_iso(), "message": error}
        self.save(state)
        return state

    def update_subscription(self, state: RealtimeState, ticker: str, channels: list[str]) -> RealtimeState:
        state.subscriptions[ticker] = {
            "channels": channels,
            "updated_at": self._now_iso(),
        }
        self.save(state)
        return state

    def append_message(self, state: RealtimeState, ticker: str, payload: dict[str, Any]) -> RealtimeState:
        state.last_message_at = self._now_iso()
        state.recent_messages[ticker] = {
            "received_at": state.last_message_at,
            "payload": payload,
        }
        self.save(state)
        return state

    def increment_reconnect(self, state: RealtimeState) -> RealtimeState:
        state.reconnect_count += 1
        self.save(state)
        return state

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=timezone.utc).isoformat()
