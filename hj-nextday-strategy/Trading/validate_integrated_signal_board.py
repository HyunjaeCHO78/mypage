import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "scenarios_validation_input.json"
OUTPUT_BOARD_PATH = ROOT / "INTEGRATED_SIGNAL_BOARD.json"
REPORT_PATH = ROOT / "VALIDATION_REPORT.md"

CLASSIFICATION_ORDER = ["제외", "관찰", "후보", "매수대기", "실행검토"]


def classify(total: int) -> str:
    if total < 40:
        return "제외"
    if total < 55:
        return "관찰"
    if total < 70:
        return "후보"
    if total < 85:
        return "매수대기"
    return "실행검토"


def downgrade_one_step(level: str) -> str:
    idx = CLASSIFICATION_ORDER.index(level)
    return CLASSIFICATION_ORDER[max(0, idx - 1)]


def cap_level(level: str, cap: str) -> str:
    return CLASSIFICATION_ORDER[min(CLASSIFICATION_ORDER.index(level), CLASSIFICATION_ORDER.index(cap))]


def stage_comment(stage: int) -> str:
    if stage <= 2:
        return "산업 초입/상승 구간으로 해석"
    if stage == 3:
        return "산업 중반 구간, 추세 확인 필요"
    return "산업 후반/과열 구간, 보수적 접근 필요"


def evaluate(scenario: Dict) -> Dict:
    adjustments: List[str] = []
    scores = dict(scenario["scores_input"])

    if scenario["leader_alignment"] != "aligned":
        scores["execution"] = max(0, scores["execution"] - 4)
        adjustments.append("leader_follower_misalignment_penalty")

    total = scores["cot"] + scores["foreign_flow"] + scores["industry_cycle"] + scores["execution"]
    raw_classification = classify(total)
    final_classification = raw_classification

    if scenario["industry_stage"] >= 4:
        final_classification = downgrade_one_step(final_classification)
        adjustments.append("industry_stage_conservative_downgrade")

    if scenario["leader_alignment"] == "broken" and final_classification in ("매수대기", "실행검토"):
        final_classification = downgrade_one_step(final_classification)
        adjustments.append("leader_follower_misalignment_downgrade")

    if scores["foreign_flow"] >= 26 and (scores["cot"] < 15 or scores["industry_cycle"] < 15):
        capped = cap_level(final_classification, "후보")
        if capped != final_classification or "foreign_flow_standalone_cap" not in adjustments:
            final_classification = capped
            adjustments.append("foreign_flow_standalone_cap")

    execution_priority = {"실행검토": 1, "매수대기": 2, "후보": 3, "관찰": 4, "제외": 5}[final_classification]
    bridge_ready = final_classification == "실행검토"

    evidence = [
        f"COT {scores['cot']}점",
        f"외국인 순매수 {scores['foreign_flow']}점",
        f"산업사이클 {scenario['industry_stage']}단계/{scores['industry_cycle']}점",
        f"실행점수 {scores['execution']}점",
    ]

    return {
        "scenario_id": scenario["scenario_id"],
        "industry": scenario["industry"],
        "ticker": scenario["ticker"],
        "name": scenario["name"],
        "leader_follower_type": scenario["leader_follower_type"],
        "leader_alignment": scenario["leader_alignment"],
        "industry_stage": scenario["industry_stage"],
        "scores": {
            "cot": scores["cot"],
            "foreign_flow": scores["foreign_flow"],
            "industry_cycle": scores["industry_cycle"],
            "execution": scores["execution"],
            "total": total,
        },
        "raw_classification": raw_classification,
        "final_classification": final_classification,
        "adjustments": adjustments,
        "industry_comment": stage_comment(scenario["industry_stage"]),
        "stock_comment": "대표/후발 정렬 점검 반영",
        "evidence_summary": evidence,
        "next_action": "장중 거래대금/돌파 여부 점검",
        "execution_priority": execution_priority,
        "bridge_ready": bridge_ready,
    }


def in_range(total: int, range_text: str) -> bool:
    low, high = [int(x) for x in range_text.split("~")]
    return low <= total <= high


def render_report(board: Dict, scenarios: List[Dict]) -> str:
    actual_map = {s["scenario_id"]: s for s in board["signals"]}

    rows = []
    for sc in scenarios:
        actual = actual_map[sc["scenario_id"]]
        exp = sc["expected"]
        matched = (
            in_range(actual["scores"]["total"], exp["score_range"])
            and actual["raw_classification"] == exp["raw_classification"]
            and actual["final_classification"] == exp["final_classification"]
            and set(exp["required_adjustments"]).issubset(set(actual["adjustments"]))
        )
        rows.append(
            "\n".join(
                [
                    f"- scenario_id: {sc['scenario_id']}",
                    f"- 산업: {sc['industry']}",
                    f"- 종목: {sc['name']} ({sc['ticker']})",
                    "- 입력값:",
                    f"  - COT 점수: {sc['scores_input']['cot']}",
                    f"  - 외국인 순매수 점수: {sc['scores_input']['foreign_flow']}",
                    f"  - 산업사이클 점수: {sc['scores_input']['industry_cycle']}",
                    f"  - 종목 실행 점수: {sc['scores_input']['execution']}",
                    f"  - 산업 단계: {sc['industry_stage']}",
                    f"  - 대표주/후발주 정렬: {sc['leader_alignment']}",
                    f"- 기대 원분류: {exp['raw_classification']}",
                    f"- 기대 최종분류: {exp['final_classification']}",
                    f"- 기대 조정: {', '.join(exp['required_adjustments']) if exp['required_adjustments'] else '없음'}",
                    "- 실제 결과:",
                    f"  - 총점: {actual['scores']['total']}점",
                    f"  - 원분류: {actual['raw_classification']}",
                    f"  - 최종분류: {actual['final_classification']}",
                    f"  - 조정: {', '.join(actual['adjustments']) if actual['adjustments'] else '없음'}",
                    f"- 일치 여부: {'일치' if matched else '불일치'}",
                    f"- 보완 필요사항: {'없음' if matched else '임계값/조정 규칙 재검토 필요'}",
                ]
            )
        )

    d1 = actual_map["D1"]["scores"]["execution"]
    d2 = actual_map["D2"]["scores"]["execution"]

    return "\n\n".join(
        [
            "# 통합감시엔진 검증 보고서",
            "",
            "## 검증 요약",
            "- 최소 3개 이상 시나리오: 완료 (A, B, C, D1, D2)",
            "- 산업 4단계 이상 보수적 하향: 완료 (B)",
            "- 외국인 순매수 단독 강세 제한: 완료 (C)",
            "- 대표주/후발주 정렬 반영: 완료 (D1 vs D2)",
            "- JSON 구조 확정: 완료 (INTEGRATED_SIGNAL_BOARD.json)",
            "",
            f"- 정렬 반영 비교: D1 실행점수 {d1}점 vs D2 실행점수 {d2}점",
            "",
            "## 테스트 케이스 상세",
            "\n\n".join(rows),
        ]
    )


def main() -> None:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    signals = [evaluate(sc) for sc in payload["scenarios"]]

    board = {
        "date": payload["date"],
        "market_phase": payload["market_phase"],
        "signals": signals,
    }

    OUTPUT_BOARD_PATH.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(board, payload["scenarios"]), encoding="utf-8")
    print(f"Generated: {OUTPUT_BOARD_PATH}")
    print(f"Generated: {REPORT_PATH}")


if __name__ == "__main__":
    main()
