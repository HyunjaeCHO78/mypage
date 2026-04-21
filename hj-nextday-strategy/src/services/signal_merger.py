from __future__ import annotations

from typing import Any

from src.services.execution_score_engine import ExecutionIntradayState, classify_execution_score


class SignalMerger:
    """장중/장후 분류 혼합을 방지하는 병합기.

    - 장중 임시 분류(intraday_classification)는 post_close 확정 분류(final_classification)와 분리한다.
    - INTEGRATED_SIGNAL_BOARD 확정 구조는 유지하고, 장중은 intraday_payload / intraday_board 로 분리한다.
    """

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
            merged["intraday_payload"] = SignalMerger._build_intraday_payload(merged, intraday_state)
            return merged

        return SignalMerger._strip_intraday_fields(merged)

    @staticmethod
    def build_intraday_board(merged_items: list[dict[str, Any]], market_phase: str) -> dict[str, Any]:
        if market_phase != "intraday":
            return {
                "market_phase": market_phase,
                "intraday_board": [],
            }

        intraday_rows = []
        for item in merged_items:
            payload = item.get("intraday_payload") or {}
            classification = payload.get("intraday_classification") or {}
            intraday_rows.append(
                {
                    "ticker": item.get("ticker"),
                    "intraday_classification": classification.get("label") or item.get("intraday_classification"),
                    "execution_intraday_score": item.get("execution_intraday_score"),
                    "status": classification.get("status", "unchanged"),
                    "change_reason": classification.get("change_reason"),
                    "updated_at": item.get("intraday_updated_at"),
                }
            )

        intraday_rows.sort(key=lambda row: row.get("execution_intraday_score") or 0, reverse=True)
        return {
            "market_phase": "intraday",
            "intraday_board": intraday_rows,
        }

    @staticmethod
    def _build_intraday_payload(
        merged_item: dict[str, Any],
        intraday_state: ExecutionIntradayState,
    ) -> dict[str, Any]:
        latest_event = intraday_state.intraday_event_history[-1] if intraday_state.intraday_event_history else None

        latest_reason = None
        if intraday_state.score_change_reasons:
            latest_reason = intraday_state.score_change_reasons[0]

        classification_status = "unchanged"
        previous_label = None
        if len(intraday_state.intraday_event_history) >= 2:
            previous_score = float(intraday_state.intraday_event_history[-2].get("after") or 0.0)
            previous_label = classify_execution_score(previous_score)
            if previous_label != intraday_state.intraday_classification:
                classification_status = "changed"
            else:
                classification_status = "suppressed"

        return {
            "market_phase": "intraday",
            "ticker": merged_item.get("ticker") or intraday_state.ticker,
            "intraday_score": round(intraday_state.execution_intraday_score, 2),
            "intraday_classification": {
                "label": intraday_state.intraday_classification,
                "previous_label": previous_label,
                "status": classification_status,
                "change_reason": latest_reason,
                "updated_at": intraday_state.last_intraday_update_at,
            },
            "history": {
                "recent_changes": intraday_state.intraday_event_history[-3:],
                "last_event": latest_event,
            },
        }

    @staticmethod
    def _strip_intraday_fields(merged: dict[str, Any]) -> dict[str, Any]:
        merged.pop("intraday_classification", None)
        merged.pop("execution_intraday_score", None)
        merged.pop("intraday_updated_at", None)
        merged.pop("intraday_score_change_reasons", None)
        merged.pop("intraday_payload", None)
        return merged
