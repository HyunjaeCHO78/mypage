from __future__ import annotations

from datetime import datetime, timezone
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
            history = payload.get("history") or {}
            recent_changes = history.get("recent_changes") or []
            latest_event = history.get("last_event") or {}
            latest_features = latest_event.get("features") or {}

            current_label = classification.get("label") or item.get("intraday_classification")
            score = float(item.get("execution_intraday_score") or 0.0)
            recent_change_strength = _recent_change_strength(recent_changes)
            classification_change_bonus = _classification_change_bonus(classification)
            trading_value_bonus = 6.0 if bool(latest_features.get("trading_value_spike")) else 0.0
            trade_strength_bonus = _trade_strength_bonus(float(latest_features.get("trade_strength_change") or 0.0))
            alignment_bonus = _alignment_bonus(latest_features.get("leader_follower_alignment_hint"))
            base_priority = _intraday_execution_priority(current_label)
            priority_score = _priority_score(
                score=score,
                base_priority=base_priority,
                recent_change_strength=recent_change_strength,
                classification_change_bonus=classification_change_bonus,
                trading_value_bonus=trading_value_bonus,
                trade_strength_bonus=trade_strength_bonus,
                alignment_bonus=alignment_bonus,
            )
            stabilized_priority = _stabilize_priority(
                priority_score=priority_score,
                base_priority=base_priority,
                recent_change_strength=recent_change_strength,
                status=classification.get("status", "unchanged"),
            )
            priority_reasons = _priority_reason(
                score=score,
                base_priority=base_priority,
                recent_change_strength=recent_change_strength,
                classification_change_bonus=classification_change_bonus,
                trading_value_bonus=trading_value_bonus,
                trade_strength_bonus=trade_strength_bonus,
                alignment_bonus=alignment_bonus,
                stabilized_priority=stabilized_priority,
            )

            intraday_rows.append(
                {
                    "ticker": item.get("ticker"),
                    "name": item.get("name"),
                    "industry": item.get("industry"),
                    "role": item.get("role"),
                    "intraday_execution_score": item.get("execution_intraday_score"),
                    "intraday_classification": current_label,
                    "execution_priority": stabilized_priority,
                    "priority_score": round(priority_score, 2),
                    "priority_reasons": priority_reasons,
                    "priority_reason": " / ".join(priority_reasons[:2]),
                    "status": classification.get("status", "unchanged"),
                    "change_reason": _human_readable_reason(
                        classification.get("change_reason"),
                        classification.get("status", "unchanged"),
                        classification.get("previous_label"),
                        current_label,
                    ),
                    "last_updated": item.get("intraday_updated_at"),
                    "recent_status": _recent_status(recent_changes),
                    "recent_change_strength": recent_change_strength,
                    "priority_history": item.get("priority_history")
                    or payload.get("priority_history")
                    or [],
                }
            )

        intraday_rows.sort(
            key=lambda row: (
                row.get("execution_priority") or 99,
                -(row.get("priority_score") or 0.0),
                -(row.get("intraday_execution_score") or 0.0),
                -(row.get("recent_change_strength") or 0.0),
                row.get("ticker") or "",
            )
        )
        for rank, row in enumerate(intraday_rows, start=1):
            history_rows = row.get("priority_history") or []
            history_rows.append(
                {
                    "at": row.get("last_updated") or _now_iso(),
                    "execution_priority": row.get("execution_priority"),
                    "priority_score": row.get("priority_score"),
                }
            )
            row["priority_history"] = history_rows[-5:]
            row["priority_rank"] = rank
            row.pop("recent_change_strength", None)

        return {
            "market_phase": "intraday",
            "generated_at": _now_iso(),
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


def _intraday_execution_priority(label: str | None) -> int:
    return {
        "실행검토": 1,
        "매수대기": 2,
        "후보": 3,
        "관찰": 4,
        "제외": 5,
    }.get(label or "", 99)


def _priority_score(
    score: float,
    base_priority: int,
    recent_change_strength: float,
    classification_change_bonus: float,
    trading_value_bonus: float,
    trade_strength_bonus: float,
    alignment_bonus: float,
) -> float:
    base_priority_weight = max(0.0, (6 - base_priority) * 8.0)
    return (
        base_priority_weight
        + (score * 0.42)
        + (recent_change_strength * 0.6)
        + classification_change_bonus
        + trading_value_bonus
        + trade_strength_bonus
        + alignment_bonus
    )


def _stabilize_priority(
    priority_score: float,
    base_priority: int,
    recent_change_strength: float,
    status: str,
) -> int:
    candidate = max(1, min(5, 6 - int(priority_score // 18)))
    if candidate < base_priority and recent_change_strength < 9.0 and status != "changed":
        return base_priority
    if candidate < base_priority and (base_priority - candidate) >= 2 and recent_change_strength < 12.0:
        return base_priority - 1
    return candidate


def _classification_change_bonus(classification: dict[str, Any]) -> float:
    status = classification.get("status")
    previous = classification.get("previous_label")
    current = classification.get("label")
    if status != "changed" or not previous or not current:
        return 0.0
    if _intraday_execution_priority(current) < _intraday_execution_priority(previous):
        return 8.0
    return -6.0


def _trade_strength_bonus(strength: float) -> float:
    if strength >= 130:
        return 4.0
    if strength >= 115:
        return 2.5
    if strength <= 80:
        return -4.0
    if strength <= 90:
        return -2.0
    return 0.0


def _alignment_bonus(hint: str | None) -> float:
    if hint == "aligned":
        return 3.0
    if hint == "lagging":
        return -3.5
    if hint == "broken":
        return -6.0
    return 0.0


def _recent_change_strength(recent_changes: list[dict[str, Any]]) -> float:
    if not recent_changes:
        return 0.0
    return abs(float(recent_changes[-1].get("delta") or 0.0))


def _recent_status(recent_changes: list[dict[str, Any]]) -> list[str]:
    rows = []
    for event in recent_changes[-5:]:
        reasons = event.get("reasons") or []
        reasons_text = ", ".join(_reason_label(reason) for reason in reasons) if reasons else "사유 없음"
        rows.append(
            f"{event.get('at')} | {float(event.get('before') or 0):.1f}→{float(event.get('after') or 0):.1f} ({float(event.get('delta') or 0):+,.1f}) | {reasons_text}"
        )
    return rows


def _human_readable_reason(
    reason_code: str | None,
    status: str,
    previous_label: str | None,
    current_label: str | None,
) -> str:
    messages: list[str] = []
    if status == "changed" and previous_label and current_label:
        messages.append(f"분류 변경: {previous_label} → {current_label}")
    elif status == "suppressed":
        messages.append("동일 분류 유지 (과도 갱신 억제)")

    if reason_code:
        messages.append(_reason_label(reason_code))

    return " / ".join(messages) if messages else "변화 없음"


def _reason_label(reason_code: str) -> str:
    mapping = {
        "breakout_detected:+12": "돌파 감지로 점수 상승(+12)",
        "trading_value_spike:+10": "거래대금 급증으로 점수 상승(+10)",
        "trade_strength_change>=120:+8": "체결강도 강세(120 이상)로 점수 상승(+8)",
        "trade_strength_change<=85:-8": "체결강도 약화(85 이하)로 점수 하락(-8)",
        "leader_follower_alignment_hint=aligned:+5": "대표/후발 정렬 양호로 점수 상승(+5)",
        "leader_follower_alignment_hint=lagging:-4": "대표/후발 정렬 약화로 점수 하락(-4)",
    }
    return mapping.get(reason_code, reason_code)


def _priority_reason(
    score: float,
    base_priority: int,
    recent_change_strength: float,
    classification_change_bonus: float,
    trading_value_bonus: float,
    trade_strength_bonus: float,
    alignment_bonus: float,
    stabilized_priority: int,
) -> list[str]:
    reasons = [
        f"기본분류 우선순위 {base_priority}",
        f"장중점수 {score:.1f}",
    ]
    if recent_change_strength >= 9:
        reasons.append(f"최근 변화강도 반영(+{recent_change_strength:.1f})")
    else:
        reasons.append("최근 변화강도 낮아 변동 억제")
    if classification_change_bonus > 0:
        reasons.append("최근 분류 상향 반영")
    elif classification_change_bonus < 0:
        reasons.append("최근 분류 하향 반영")
    if trading_value_bonus > 0:
        reasons.append("거래대금 급증 가산")
    if trade_strength_bonus > 0:
        reasons.append("체결강도 개선 가산")
    elif trade_strength_bonus < 0:
        reasons.append("체결강도 약화 감점")
    if alignment_bonus > 0:
        reasons.append("대표/후발 정렬 양호 가산")
    elif alignment_bonus < 0:
        reasons.append("대표/후발 정렬 불량 감점")
    reasons.append(f"최종 실행 우선순위 {stabilized_priority}")
    return reasons


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
