import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
INTRADAY_PATH = ROOT / "INTRADAY_SIGNAL_BRIDGE.json"
POST_CLOSE_PATH = ROOT / "INTEGRATED_SIGNAL_BOARD.json"
INTRADAY_SAMPLE_PATH = ROOT / "examples" / "intraday_signal_bridge.sample.json"
POST_CLOSE_SAMPLE_PATH = ROOT / "examples" / "post_close_signal_bridge.sample.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_intraday_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = ["ticker", "intraday_classification", "intraday_execution_score", "execution_priority", "priority_reason", "last_updated"]
    for key in required_fields:
        ensure(key in signal, f"intraday signal missing required field: {key}")

    ensure(isinstance(signal["ticker"], str), "intraday ticker must be string")
    ensure(isinstance(signal["intraday_classification"], str), "intraday classification must be string")
    ensure(isinstance(signal["intraday_execution_score"], (int, float)), "intraday score must be number")
    ensure(isinstance(signal["execution_priority"], int), "intraday priority must be int")
    ensure(isinstance(signal["priority_reason"], str), "intraday reason must be string")
    ensure(isinstance(signal["last_updated"], str), "intraday last_updated must be string")

    return {
        "ticker": signal["ticker"],
        "classification": signal["intraday_classification"],
        "score": signal["intraday_execution_score"],
        "priority": signal["execution_priority"],
        "reason": signal["priority_reason"],
        "last_updated": signal["last_updated"],
        "phase": "intraday",
    }


def parse_post_close_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = ["ticker", "final_classification", "scores", "execution_priority", "next_action", "last_updated"]
    for key in required_fields:
        ensure(key in signal, f"post_close signal missing required field: {key}")

    ensure("total" in signal["scores"], "post_close scores.total required")
    ensure(isinstance(signal["ticker"], str), "post_close ticker must be string")
    ensure(isinstance(signal["final_classification"], str), "post_close classification must be string")
    ensure(isinstance(signal["scores"]["total"], (int, float)), "post_close score must be number")
    ensure(isinstance(signal["execution_priority"], int), "post_close priority must be int")
    ensure(isinstance(signal["next_action"], str), "post_close reason(next_action) must be string")
    ensure(isinstance(signal["last_updated"], str), "post_close last_updated must be string")

    return {
        "ticker": signal["ticker"],
        "classification": signal["final_classification"],
        "score": signal["scores"]["total"],
        "priority": signal["execution_priority"],
        "reason": signal["next_action"],
        "last_updated": signal["last_updated"],
        "phase": "post_close",
    }


def parse_payload(payload: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
    ensure("market_phase" in payload, f"{source}: market_phase required")
    ensure("generated_at" in payload and isinstance(payload["generated_at"], str), f"{source}: generated_at required")
    ensure(isinstance(payload.get("signals"), list) and payload["signals"], f"{source}: signals must be non-empty list")

    phase = payload["market_phase"]
    signals = payload["signals"]

    if phase == "intraday":
        ensure(payload.get("signal_type") == "temporary", f"{source}: intraday signal_type must be temporary")
        return [parse_intraday_signal(signal) for signal in signals]

    if phase == "post_close":
        return [parse_post_close_signal(signal) for signal in signals]

    raise AssertionError(f"{source}: unsupported market_phase={phase}")


def validate_samples() -> None:
    intraday_sample = load_json(INTRADAY_SAMPLE_PATH)
    post_close_sample = load_json(POST_CLOSE_SAMPLE_PATH)

    intraday_rows = parse_payload(intraday_sample, "intraday sample")
    post_close_rows = parse_payload(post_close_sample, "post_close sample")

    ensure(len(intraday_rows) >= 2, "intraday sample must have at least 2 rows")
    ensure(len(post_close_rows) >= 1, "post_close sample must have at least 1 row")


def validate_phase_guard() -> None:
    intraday = load_json(INTRADAY_PATH)
    post_close = load_json(POST_CLOSE_PATH)

    parse_payload(intraday, "INTRADAY_SIGNAL_BRIDGE")
    parse_payload(post_close, "INTEGRATED_SIGNAL_BOARD")

    # phase 혼용 방지 가드
    ensure(intraday["market_phase"] != post_close["market_phase"], "phase collision detected")


def main() -> None:
    validate_samples()
    validate_phase_guard()
    print("PASS: 실매매 읽기/해석/매핑 검증 완료")


if __name__ == "__main__":
    main()
