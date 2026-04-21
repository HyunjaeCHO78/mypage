from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class WatchItem:
    ticker: str
    name: str
    industry: str
    role: str


class WatchlistService:
    """장중 감시용 종목 리스트를 로딩한다.

    우선순위:
    1) data/watchlist.yaml
    2) Trading/INTEGRATED_SIGNAL_BOARD.json (bridge_ready=true 또는 실행 우선순위 존재)
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.watchlist_path = root_dir / "data" / "watchlist.yaml"
        self.integrated_board_path = root_dir / "Trading" / "INTEGRATED_SIGNAL_BOARD.json"

    def load_watch_items(self) -> list[WatchItem]:
        if self.watchlist_path.exists():
            return self._load_from_yaml(self.watchlist_path)
        return self._load_from_integrated_board(self.integrated_board_path)

    def load_tickers(self) -> list[str]:
        seen: set[str] = set()
        tickers: list[str] = []
        for item in self.load_watch_items():
            if item.ticker in seen:
                continue
            seen.add(item.ticker)
            tickers.append(item.ticker)
        return tickers

    def _load_from_yaml(self, path: Path) -> list[WatchItem]:
        if yaml is None:
            raise RuntimeError("PyYAML 패키지가 필요합니다. requirements.txt 기준으로 설치하세요.")
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        items: list[WatchItem] = []

        for group in payload.get("groups", []):
            industry = group.get("industry", "unknown")
            for stock in group.get("stocks", []):
                items.append(
                    WatchItem(
                        ticker=str(stock["ticker"]),
                        name=str(stock.get("name", stock["ticker"])),
                        industry=industry,
                        role=str(stock.get("role", "unknown")),
                    )
                )
        return items

    def _load_from_integrated_board(self, path: Path) -> list[WatchItem]:
        if not path.exists():
            return []
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        items: list[WatchItem] = []
        for signal in payload.get("signals", []):
            bridge_ready = bool(signal.get("bridge_ready", False))
            has_priority = signal.get("execution_priority") is not None
            if not (bridge_ready or has_priority):
                continue
            items.append(
                WatchItem(
                    ticker=str(signal["ticker"]),
                    name=str(signal.get("name", signal["ticker"])),
                    industry=str(signal.get("industry", "unknown")),
                    role=str(signal.get("leader_follower_type", "unknown")),
                )
            )
        return items
