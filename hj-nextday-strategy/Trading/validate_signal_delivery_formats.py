import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INTRADAY_PATH = ROOT / "INTRADAY_SIGNAL_BRIDGE.json"
POST_CLOSE_PATH = ROOT / "INTEGRATED_SIGNAL_BOARD.json"
INTRADAY_SAMPLE_PATH = ROOT / "examples" / "intraday_signal_bridge.sample.json"
POST_CLOSE_SAMPLE_PATH = ROOT / "examples" / "post_close_signal_bridge.sample.json"

INTRADAY_REQUIRED = {
    "ticker",
    "name",
    "industry",
    "role",
    "intraday_execution_score",
    "intraday_classification",
    "execution_priority",
    "priority_reason",
    "last_updated",
    "recent_change_summary",
}

POST_CLOSE_REQUIRED = {
    "ticker",
    "name",
    "industry",
    "scores",
    "final_classification",
    "bridge_ready",
    "next_action",
    "execution_priority",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_intraday(payload: dict, label: str) -> None:
    assert payload["market_phase"] == "intraday", f"{label}: market_phase must be intraday"
    assert payload["signal_type"] == "temporary", f"{label}: signal_type must be temporary"
    assert isinstance(payload.get("signals"), list) and payload["signals"], f"{label}: signals must be non-empty"

    for idx, signal in enumerate(payload["signals"], start=1):
        missing = INTRADAY_REQUIRED - signal.keys()
        assert not missing, f"{label}: signal[{idx}] missing fields: {sorted(missing)}"


def validate_post_close(payload: dict, label: str) -> None:
    assert payload["market_phase"] == "post_close", f"{label}: market_phase must be post_close"
    assert isinstance(payload.get("signals"), list) and payload["signals"], f"{label}: signals must be non-empty"

    for idx, signal in enumerate(payload["signals"], start=1):
        missing = POST_CLOSE_REQUIRED - signal.keys()
        assert not missing, f"{label}: signal[{idx}] missing fields: {sorted(missing)}"
        assert "total" in signal["scores"], f"{label}: signal[{idx}] scores.total required"


def validate_separation(intraday_payload: dict, post_close_payload: dict) -> None:
    assert intraday_payload["market_phase"] != post_close_payload["market_phase"], "phase collision detected"


def main() -> None:
    intraday = load_json(INTRADAY_PATH)
    post_close = load_json(POST_CLOSE_PATH)
    intraday_sample = load_json(INTRADAY_SAMPLE_PATH)
    post_close_sample = load_json(POST_CLOSE_SAMPLE_PATH)

    validate_intraday(intraday, "INTRADAY_SIGNAL_BRIDGE")
    validate_intraday(intraday_sample, "intraday sample")
    validate_post_close(post_close, "INTEGRATED_SIGNAL_BOARD")
    validate_post_close(post_close_sample, "post_close sample")
    validate_separation(intraday, post_close)

    print("PASS: intraday/post_close 전달 포맷 검증 완료")


if __name__ == "__main__":
    main()
