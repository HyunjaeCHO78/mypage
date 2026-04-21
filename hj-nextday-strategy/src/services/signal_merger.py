from __future__ import annotations

from typing import Any

from src.services.execution_score_engine import ExecutionIntradayState


class SignalMerger:
    """장중/장후 분류 혼합을 방지하는 최소 병합기."""

    @staticmethod
    def merge_for_phase(
        board_item: dict[str, Any],
        market_phase: str,
        intraday_state: ExecutionIntradayState | None = None,
    ) -> dict[str, Any]:
        merged = dict(board_item)

        if market_phase == "intraday" and intraday_state is not None:
            merged["intraday_classification"] = intraday_state.intraday_classification
            merged["execution_intraday_score"] = round(intraday_state.execution_intraday_score, 2)
            merged["intraday_updated_at"] = intraday_state.last_intraday_update_at
            merged["intraday_score_change_reasons"] = intraday_state.score_change_reasons
            return merged

        merged.pop("intraday_classification", None)
        merged.pop("execution_intraday_score", None)
        merged.pop("intraday_updated_at", None)
        merged.pop("intraday_score_change_reasons", None)
        return merged
