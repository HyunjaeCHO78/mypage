from __future__ import annotations

from pathlib import Path
import json
from typing import Any


class IntradayBoardStateService:
    """장중 임시 보드 스냅샷 저장 서비스."""

    def __init__(self, root_dir: Path) -> None:
        self.board_path = root_dir / "data" / "state" / "intraday_signal_board.json"
        self.board_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, board: dict[str, Any]) -> None:
        tmp_path = self.board_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.board_path)
