import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "dry_run_results.json"
LOG_PATH = ROOT / "dry_run.log"

REQUIRED_FIELDS = {
    "ticker",
    "market_phase",
    "final_decision",
    "decision_reason",
    "decision_flags",
    "required_next_action",
    "decision_timestamp",
    "source_signal_type",
}


def main() -> None:
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    log_text = LOG_PATH.read_text(encoding="utf-8")

    assert payload["order_api_called"] is False, "order_api_called must remain false"
    assert "ORDER_API_CALLED=false" in log_text, "dry_run.log must include ORDER_API_CALLED=false"

    results = payload.get("results", [])
    assert len(results) >= 4, "dry-run results must contain at least 4 rows"

    decisions = {"pass": 0, "hold": 0, "block": 0, "review": 0}

    for idx, row in enumerate(results, start=1):
        missing = REQUIRED_FIELDS - row.keys()
        assert not missing, f"result[{idx}] missing fields: {sorted(missing)}"
        assert row["market_phase"] in ("intraday", "post_close"), f"result[{idx}] invalid market_phase"
        assert row["source_signal_type"] in ("intraday_temporary", "post_close_confirmed"), f"result[{idx}] invalid source_signal_type"
        decisions[row["final_decision"]] += 1

    for decision, count in decisions.items():
        assert count >= 1, f"at least one {decision} case required"

    print("PASS: dry-run 시뮬레이션 검증 완료")


if __name__ == "__main__":
    main()
