from __future__ import annotations

from pathlib import Path
import json

from src.services.execution_score_engine import ExecutionIntradayState


class ExecutionScoreStateService:
    def __init__(self, root_dir: Path) -> None:
        self.state_path = root_dir / "data" / "state" / "execution_score_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> dict[str, ExecutionIntradayState]:
        if not self.state_path.exists():
            return {}
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return {ticker: ExecutionIntradayState(**state) for ticker, state in payload.items()}

    def save_all(self, states: dict[str, ExecutionIntradayState]) -> None:
        serializable = {ticker: state.__dict__ for ticker, state in states.items()}
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)
