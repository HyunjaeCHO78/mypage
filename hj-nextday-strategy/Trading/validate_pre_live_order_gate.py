import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
DRY_RUN_RESULT_PATH = ROOT / "dry_run_results.json"
DRY_RUN_LOG_PATH = ROOT / "dry_run.log"
INTRADAY_BRIDGE_PATH = ROOT / "INTRADAY_SIGNAL_BRIDGE.json"
POST_CLOSE_BRIDGE_PATH = ROOT / "INTEGRATED_SIGNAL_BOARD.json"
REPORT_PATH = ROOT / "pre_live_order_gate_report.json"

VALID_DECISIONS = {"pass", "hold", "block", "review"}
VALID_PHASES = {"intraday", "post_close"}
VALID_SIGNAL_TYPES = {"intraday_temporary", "post_close_confirmed"}
BLOCKING_FLAGS = {
    "INDUSTRY_STAGE_HIGH",
    "FOREIGN_FLOW_ONLY_STRONG",
    "LEADER_ALIGNMENT_BROKEN",
    "PHASE_INCONSISTENT",
    "REQUIRED_FIELDS_INCOMPLETE",
    "INTRADAY_NOISE",
}
REQUIRED_RESULT_FIELDS = {
    "ticker",
    "market_phase",
    "source_signal_type",
    "final_decision",
    "decision_reason",
    "decision_flags",
    "required_next_action",
    "decision_timestamp",
    "input_snapshot",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bridge_format(payload: Dict, bridge_name: str) -> List[str]:
    reasons: List[str] = []
    signals = payload.get("signals")
    if not isinstance(signals, list):
        reasons.append(f"{bridge_name}: signals must be a list")
        return reasons

    for index, row in enumerate(signals, start=1):
        if not isinstance(row, dict):
            reasons.append(f"{bridge_name}: signals[{index}] must be an object")
            continue
        if "ticker" not in row or not row.get("ticker"):
            reasons.append(f"{bridge_name}: signals[{index}] missing ticker")
    return reasons


def validate_result_rows(results: List[Dict]) -> Tuple[List[str], List[Dict]]:
    failures: List[str] = []
    live_candidates: List[Dict] = []

    for idx, row in enumerate(results, start=1):
        missing = REQUIRED_RESULT_FIELDS - set(row.keys())
        if missing:
            failures.append(f"result[{idx}] missing fields: {sorted(missing)}")
            continue

        phase = row.get("market_phase")
        signal_type = row.get("source_signal_type")
        decision = row.get("final_decision")

        if phase not in VALID_PHASES:
            failures.append(f"result[{idx}] invalid market_phase={phase}")
        if signal_type not in VALID_SIGNAL_TYPES:
            failures.append(f"result[{idx}] invalid source_signal_type={signal_type}")
        if decision not in VALID_DECISIONS:
            failures.append(f"result[{idx}] invalid final_decision={decision}")

        if phase == "intraday" and signal_type != "intraday_temporary":
            failures.append(f"result[{idx}] phase/source mismatch: intraday must map to intraday_temporary")
        if phase == "post_close" and signal_type != "post_close_confirmed":
            failures.append(f"result[{idx}] phase/source mismatch: post_close must map to post_close_confirmed")

        reason = str(row.get("decision_reason", "")).strip()
        flags = row.get("decision_flags")
        if not reason:
            failures.append(f"result[{idx}] decision_reason is empty")
        if not isinstance(flags, list):
            failures.append(f"result[{idx}] decision_flags must be a list")
            flags = []

        snapshot = row.get("input_snapshot")
        if not isinstance(snapshot, dict):
            failures.append(f"result[{idx}] input_snapshot must be an object")
            snapshot = {}

        if decision == "pass":
            pass_failures: List[str] = []
            if phase != "post_close":
                pass_failures.append("pass decision requires post_close phase")
            if signal_type != "post_close_confirmed":
                pass_failures.append("pass decision requires post_close_confirmed source")
            if any(flag in BLOCKING_FLAGS for flag in flags):
                pass_failures.append("blocking flags present in pass decision")
            if snapshot.get("industry_stage", 99) >= 4:
                pass_failures.append("industry_stage must be lower than 4")
            if snapshot.get("leader_follower_alignment") != "aligned":
                pass_failures.append("leader_follower_alignment must be aligned")

            if pass_failures:
                failures.append(f"result[{idx}] pass safety check failed: {', '.join(pass_failures)}")
            else:
                live_candidates.append(
                    {
                        "ticker": row.get("ticker"),
                        "decision_timestamp": row.get("decision_timestamp"),
                        "decision_reason": reason,
                    }
                )

    return failures, live_candidates


def build_report(is_pass: bool, failures: List[str], checks: Dict[str, bool], live_candidates: List[Dict]) -> Dict:
    return {
        "validated_at": now_iso(),
        "status": "pass" if is_pass else "fail",
        "checks": checks,
        "failure_reasons": failures,
        "live_order_connection_allowed": is_pass and len(live_candidates) > 0,
        "eligible_candidates": live_candidates,
        "note": "실주문 API는 본 검증에서 호출하지 않으며, 허용 기준 점검만 수행한다.",
    }


def main() -> None:
    failures: List[str] = []

    dry_run = load_json(DRY_RUN_RESULT_PATH)
    intraday_bridge = load_json(INTRADAY_BRIDGE_PATH)
    post_close_bridge = load_json(POST_CLOSE_BRIDGE_PATH)
    log_text = DRY_RUN_LOG_PATH.read_text(encoding="utf-8")

    checks = {
        "phase_separation": True,
        "required_fields": True,
        "decision_fields": True,
        "bridge_format": True,
        "dry_run_result": True,
        "order_api_guard": True,
        "log_written": True,
    }

    if dry_run.get("order_api_called") is not False:
        checks["order_api_guard"] = False
        failures.append("dry_run_results.json: order_api_called must be false")

    if "ORDER_API_CALLED=false" not in log_text:
        checks["order_api_guard"] = False
        failures.append("dry_run.log must contain ORDER_API_CALLED=false")

    if not log_text.strip():
        checks["log_written"] = False
        failures.append("dry_run.log is empty")

    bridge_failures = validate_bridge_format(intraday_bridge, "INTRADAY_SIGNAL_BRIDGE")
    bridge_failures.extend(validate_bridge_format(post_close_bridge, "INTEGRATED_SIGNAL_BOARD"))
    if bridge_failures:
        checks["bridge_format"] = False
        failures.extend(bridge_failures)

    results = dry_run.get("results")
    if not isinstance(results, list) or not results:
        checks["dry_run_result"] = False
        failures.append("dry_run_results.json: results must be a non-empty list")
        results = []

    row_failures, live_candidates = validate_result_rows(results)
    failures.extend(row_failures)

    for reason in row_failures:
        if "missing fields" in reason or "input_snapshot" in reason:
            checks["required_fields"] = False
        if "final_decision" in reason or "decision_reason" in reason or "decision_flags" in reason:
            checks["decision_fields"] = False
        if "phase/source mismatch" in reason or "invalid market_phase" in reason or "invalid source_signal_type" in reason:
            checks["phase_separation"] = False

    is_pass = len(failures) == 0
    report = build_report(is_pass, failures, checks, live_candidates)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if is_pass:
        print("PASS: pre-live order gate validation completed")
        print(f"eligible_candidates={len(live_candidates)}")
        sys.exit(0)

    print("FAIL: pre-live order gate validation failed")
    for reason in failures:
        print(f"- {reason}")
    sys.exit(1)


if __name__ == "__main__":
    main()
