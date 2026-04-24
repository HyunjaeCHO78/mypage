import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "dry_run_results.json"
LOG_PATH = ROOT / "dry_run.log"
TEST_ORDER_RESULT_PATH = ROOT / "dry_run_test_order_results.json"
TEST_ORDER_LOG_PATH = ROOT / "dry_run_test_order.log"

REQUIRED_FIELDS = {
    "ticker",
    "market_phase",
    "final_decision",
    "decision_reason",
    "decision_flags",
    "required_next_action",
    "decision_timestamp",
    "source_signal_type",
    "test_order_allowed",
    "allowed_reason",
    "blocked_reason",
    "max_order_amount",
    "max_order_quantity",
    "daily_limit",
    "eligible_for_test_order",
}


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    log_text = LOG_PATH.read_text(encoding="utf-8")
    test_payload = json.loads(TEST_ORDER_RESULT_PATH.read_text(encoding="utf-8"))
    test_log_text = TEST_ORDER_LOG_PATH.read_text(encoding="utf-8")

    assert payload["order_api_called"] is False, "order_api_called must remain false"
    assert "ORDER_API_CALLED=false" in log_text, "dry_run.log must include ORDER_API_CALLED=false"
    assert test_payload["order_api_called"] is False, "test order flow must not call order API"
    assert "ORDER_API_CALLED=false" in test_log_text, "dry_run_test_order.log must include ORDER_API_CALLED=false"

    results = payload.get("results", [])
    assert len(results) >= 4, "dry-run results must contain at least 4 rows"
    assert payload["test_order_counts"]["allowed"] >= 1, "at least one test order allowed case required"
    assert payload["test_order_counts"]["blocked"] >= 1, "at least one test order blocked case required"

    decisions = {"pass": 0, "hold": 0, "block": 0, "review": 0}

    for idx, row in enumerate(results, start=1):
        missing = REQUIRED_FIELDS - row.keys()
        assert not missing, f"result[{idx}] missing fields: {sorted(missing)}"
        assert row["market_phase"] in ("intraday", "post_close"), f"result[{idx}] invalid market_phase"
        assert row["source_signal_type"] in ("intraday_temporary", "post_close_confirmed"), f"result[{idx}] invalid source_signal_type"
        assert isinstance(row["allowed_reason"], list), f"result[{idx}] allowed_reason must be list"
        assert isinstance(row["blocked_reason"], list), f"result[{idx}] blocked_reason must be list"
        assert row["max_order_amount"] == 300000, f"result[{idx}] max_order_amount mismatch"
        assert row["max_order_quantity"] == 1, f"result[{idx}] max_order_quantity mismatch"
        assert row["eligible_for_test_order"] == row["test_order_allowed"], f"result[{idx}] eligibility mismatch"
        decisions[row["final_decision"]] += 1

    for decision, count in decisions.items():
        assert count >= 1, f"at least one {decision} case required"

    print("PASS: dry-run 시뮬레이션 검증 완료")


if __name__ == "__main__":
    main()
