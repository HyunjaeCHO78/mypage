import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
INTRADAY_PATH = ROOT / "INTRADAY_SIGNAL_BRIDGE.json"
POST_CLOSE_PATH = ROOT / "INTEGRATED_SIGNAL_BOARD.json"
SCENARIO_PATH = ROOT / "examples" / "dry_run_scenarios.sample.json"
OUTPUT_JSON_PATH = ROOT / "dry_run_results.json"
OUTPUT_LOG_PATH = ROOT / "dry_run.log"

TOTAL_SCORE_PASS_MIN = 70
INTRADAY_EXEC_PASS_MIN = 65
EXECUTION_PRIORITY_PASS_MIN = 70
EXECUTION_PRIORITY_HOLD_MIN = 40
EXECUTION_PRIORITY_HOLD_MAX = 69

NEXT_ACTION_MAP = {
    "pass": "주문검토",
    "hold": "관찰지속",
    "block": "당일제외",
    "review": "수동검토",
}


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_intraday_signal(signal: Dict) -> Dict:
    classification = signal.get("intraday_classification", "후보")
    return {
        "ticker": signal["ticker"],
        "market_phase": "intraday",
        "source_signal_type": "intraday_temporary",
        "final_classification": classification,
        "intraday_classification": classification,
        "total_score": int(signal.get("intraday_execution_score", 0) * 8),
        "intraday_execution_score": int(signal.get("intraday_execution_score", 0) * 8),
        "execution_priority": max(0, 100 - ((signal.get("execution_priority", 5) - 1) * 15)),
        "priority_reason": signal.get("priority_reason", ""),
        "industry_stage": 3,
        "leader_follower_alignment": "aligned" if signal.get("role") == "대표주" else "mixed",
        "recent_change_summary": signal.get("recent_change_summary", ""),
        "foreign_flow_signal": "none",
        "intraday_noise_flag": "급등" in signal.get("recent_change_summary", ""),
        "evidence_strength": "medium",
        "required_fields_complete": True,
        "phase_consistency": True,
        "decision_timestamp": signal.get("last_updated") or now_iso(),
    }


def normalize_post_close_signal(signal: Dict) -> Dict:
    adjustments = signal.get("adjustments", [])
    if "foreign_flow_standalone_cap" in adjustments:
        foreign_flow_signal = "foreign_only_strong"
    elif signal.get("scores", {}).get("foreign_flow", 0) >= 20:
        foreign_flow_signal = "broad_participation"
    else:
        foreign_flow_signal = "none"

    evidence_strength = "strong" if signal.get("scores", {}).get("total", 0) >= 75 else "medium"

    return {
        "ticker": signal["ticker"],
        "market_phase": "post_close",
        "source_signal_type": "post_close_confirmed",
        "final_classification": signal.get("final_classification", "후보"),
        "intraday_classification": "not_provided",
        "total_score": signal.get("scores", {}).get("total", 0),
        "intraday_execution_score": signal.get("scores", {}).get("execution", 0) * 8,
        "execution_priority": max(0, 100 - ((signal.get("execution_priority", 5) - 1) * 15)),
        "priority_reason": signal.get("next_action", ""),
        "industry_stage": signal.get("industry_stage", 3),
        "leader_follower_alignment": signal.get("leader_alignment", "mixed"),
        "recent_change_summary": ", ".join(signal.get("evidence_summary", [])),
        "foreign_flow_signal": foreign_flow_signal,
        "intraday_noise_flag": False,
        "evidence_strength": evidence_strength,
        "required_fields_complete": True,
        "phase_consistency": True,
        "decision_timestamp": signal.get("last_updated") or now_iso(),
    }


def evaluate_final_decision(payload: Dict) -> Tuple[str, List[str], str]:
    flags: List[str] = []

    if not payload.get("required_fields_complete", False):
        flags.append("REQUIRED_FIELDS_INCOMPLETE")
    if not payload.get("phase_consistency", False):
        flags.append("PHASE_INCONSISTENT")
    if payload.get("industry_stage", 0) >= 4:
        flags.append("INDUSTRY_STAGE_HIGH")
    if payload.get("foreign_flow_signal") == "foreign_only_strong":
        flags.append("FOREIGN_FLOW_ONLY_STRONG")
    if payload.get("leader_follower_alignment") == "broken":
        flags.append("LEADER_ALIGNMENT_BROKEN")
    if payload.get("intraday_noise_flag") is True:
        flags.append("INTRADAY_NOISE")
    if ("급변" in payload.get("recent_change_summary", "") and payload.get("evidence_strength") == "weak"):
        flags.append("RAPID_CHANGE_WEAK_EVIDENCE")

    if flags:
        reason = "차단 규칙 충족: " + ", ".join(flags)
        return "block", flags, reason

    review_conditions = [
        payload.get("total_score", 0) >= 75,
        payload.get("intraday_execution_score", 0) >= 75,
        payload.get("leader_follower_alignment") != "aligned",
    ]
    if all(review_conditions):
        flags.append("REVIEW_SCORE_ALIGNMENT_CONFLICT")
        reason = "점수는 상위권이나 정렬 상태가 엇갈려 수동 검토 필요"
        return "review", flags, reason

    hold_flags: List[str] = []
    if payload.get("final_classification") == "후보":
        hold_flags.append("FINAL_CLASSIFICATION_CANDIDATE")
    if payload.get("intraday_execution_score", 0) >= INTRADAY_EXEC_PASS_MIN and payload.get("total_score", 0) < TOTAL_SCORE_PASS_MIN:
        hold_flags.append("TOTAL_SCORE_BELOW_PASS")
    if EXECUTION_PRIORITY_HOLD_MIN <= payload.get("execution_priority", 0) <= EXECUTION_PRIORITY_HOLD_MAX:
        hold_flags.append("EXECUTION_PRIORITY_MID_BAND")
    if payload.get("leader_follower_alignment") == "mixed":
        hold_flags.append("LEADER_ALIGNMENT_MIXED")
    if not payload.get("priority_reason") or len(payload.get("recent_change_summary", "")) < 8:
        hold_flags.append("LOW_REASON_QUALITY")

    if hold_flags:
        reason = "보류 규칙 충족: " + ", ".join(hold_flags)
        return "hold", hold_flags, reason

    pass_conditions = [
        payload.get("market_phase") == "post_close",
        payload.get("source_signal_type") == "post_close_confirmed",
        payload.get("final_classification") in ("실행검토", "매수대기"),
        payload.get("intraday_execution_score", 0) >= INTRADAY_EXEC_PASS_MIN,
        payload.get("execution_priority", 0) >= EXECUTION_PRIORITY_PASS_MIN,
        bool(payload.get("priority_reason")) and bool(payload.get("recent_change_summary")),
        payload.get("leader_follower_alignment") == "aligned",
        payload.get("required_fields_complete") is True,
        payload.get("phase_consistency") is True,
    ]

    if all(pass_conditions):
        return "pass", ["PASS_RULES_CONFIRMED"], "장중/장후 근거와 정합성이 모두 충족되어 주문 검토 가능"

    return "hold", ["FALLBACK_HOLD"], "명확한 통과/차단 조건이 부족하여 보류"


def run_dry_run() -> Dict:
    intraday = load_json(INTRADAY_PATH)
    post_close = load_json(POST_CLOSE_PATH)
    scenarios = load_json(SCENARIO_PATH)

    records: List[Dict] = []

    for signal in intraday.get("signals", []):
        records.append(normalize_intraday_signal(signal))

    for signal in post_close.get("signals", []):
        records.append(normalize_post_close_signal(signal))

    for scenario in scenarios.get("scenarios", []):
        records.append(scenario)

    results = []
    for record in records:
        decision, flags, reason = evaluate_final_decision(record)
        results.append(
            {
                "ticker": record["ticker"],
                "market_phase": record["market_phase"],
                "final_decision": decision,
                "decision_reason": reason,
                "decision_flags": flags,
                "required_next_action": NEXT_ACTION_MAP[decision],
                "decision_timestamp": record.get("decision_timestamp", now_iso()),
                "source_signal_type": record["source_signal_type"],
                "input_snapshot": {
                    "final_classification": record.get("final_classification"),
                    "intraday_classification": record.get("intraday_classification"),
                    "total_score": record.get("total_score"),
                    "intraday_execution_score": record.get("intraday_execution_score"),
                    "execution_priority": record.get("execution_priority"),
                    "industry_stage": record.get("industry_stage"),
                    "leader_follower_alignment": record.get("leader_follower_alignment"),
                },
            }
        )

    summary = {
        "generated_at": now_iso(),
        "order_api_called": False,
        "result_count": len(results),
        "decision_counts": {
            "pass": sum(1 for r in results if r["final_decision"] == "pass"),
            "hold": sum(1 for r in results if r["final_decision"] == "hold"),
            "block": sum(1 for r in results if r["final_decision"] == "block"),
            "review": sum(1 for r in results if r["final_decision"] == "review"),
        },
        "results": results,
    }

    return summary


def write_outputs(summary: Dict) -> None:
    OUTPUT_JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"dry-run generated_at={summary['generated_at']}",
        "ORDER_API_CALLED=false",
        f"result_count={summary['result_count']}",
        "decision_counts=" + json.dumps(summary["decision_counts"], ensure_ascii=False),
    ]
    for row in summary["results"]:
        lines.append(
            " | ".join(
                [
                    row["ticker"],
                    row["market_phase"],
                    row["source_signal_type"],
                    row["final_decision"],
                    row["required_next_action"],
                    row["decision_reason"],
                ]
            )
        )

    OUTPUT_LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    summary = run_dry_run()
    write_outputs(summary)
    print(f"Generated: {OUTPUT_JSON_PATH}")
    print(f"Generated: {OUTPUT_LOG_PATH}")
    print(f"Decision counts: {summary['decision_counts']}")


if __name__ == "__main__":
    main()
