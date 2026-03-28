#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORTS_DIR = Path("reports")
DAILY_DIR = REPORTS_DIR / "daily"
WEEKLY_DIR = REPORTS_DIR / "weekly"
DECISION_LOG_DIR = Path("logs/daily_decisions")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUTPUT_PATH = WEEKLY_DIR / f"{TODAY}_weekly_conservative_report.md"


def find_conservative_files() -> list[Path]:
    paths: list[Path] = []
    if DAILY_DIR.exists():
        paths.extend(sorted(DAILY_DIR.glob("*_conservative_top3.json")))
    legacy_paths = sorted(REPORTS_DIR.glob("*conservative*.json"))
    for path in legacy_paths:
        if path.parent == WEEKLY_DIR:
            continue
        if path not in paths:
            paths.append(path)
    return paths


def find_decision_logs() -> list[Path]:
    if not DECISION_LOG_DIR.exists():
        return []
    return sorted(DECISION_LOG_DIR.glob("*_decision_log.csv"))


def load_candidate_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"후보 결과 파일 읽기 실패: {path} ({exc})")
            continue
        if not isinstance(data, list):
            warnings.append(f"후보 결과 파일 형식 오류: {path}")
            continue
        for item in data:
            if isinstance(item, dict):
                row = dict(item)
                row["__source_file"] = path.name
                rows.append(row)
            else:
                warnings.append(f"후보 결과 행 형식 오류: {path}")
    return rows, warnings


def load_decision_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in paths:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    normalized = {key: (value or "").strip() for key, value in row.items()}
                    normalized["__source_file"] = path.name
                    if any(normalized.values()):
                        rows.append(normalized)
        except Exception as exc:
            warnings.append(f"decision log 읽기 실패: {path} ({exc})")
    return rows, warnings


def average_float(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_review_notes(rows: list[dict[str, Any]]) -> list[str]:
    notes = [row.get("review_note", "") for row in rows if row.get("review_note", "")]
    if not notes:
        return []
    counter = Counter(notes)
    return [f"{note} ({count}회)" for note, count in counter.most_common(3)]


def build_report(
    candidate_paths: list[Path],
    candidate_rows: list[dict[str, Any]],
    decision_paths: list[Path],
    decision_rows: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    candidate_theme_counter = Counter(
        row.get("theme", "").strip()
        for row in candidate_rows
        if isinstance(row.get("theme"), str) and row.get("theme", "").strip()
    )
    candidate_name_counter = Counter(
        row.get("name", "").strip()
        for row in candidate_rows
        if isinstance(row.get("name"), str) and row.get("name", "").strip()
    )

    total_runs = len(candidate_paths)
    total_candidates = len(candidate_rows)
    total_passed = sum(1 for row in candidate_rows if bool(row.get("passed")))
    candidate_scores = [safe_float(row.get("total_score")) for row in candidate_rows]
    avg_score = average_float([score for score in candidate_scores if score is not None])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    top_theme = candidate_theme_counter.most_common(1)[0][0] if candidate_theme_counter else "없음"
    top_name = candidate_name_counter.most_common(1)[0][0] if candidate_name_counter else "없음"

    entered_rows = [row for row in decision_rows if row.get("entered", "").lower() == "yes"]
    not_entered_rows = [row for row in decision_rows if row.get("entered", "").lower() == "no"]
    result_pct_values = [safe_float(row.get("result_pct")) for row in decision_rows]
    result_amount_values = [safe_float(row.get("result_amount")) for row in decision_rows]
    avg_result_pct = average_float([v for v in result_pct_values if v is not None])
    avg_result_amount = average_float([v for v in result_amount_values if v is not None])
    no_entry_counter = Counter(
        row.get("no_entry_reason", "")
        for row in not_entered_rows
        if row.get("no_entry_reason", "")
    )
    entered_name_counter = Counter(
        row.get("name", "")
        for row in entered_rows
        if row.get("name", "")
    )
    review_note_summary = summarize_review_notes(decision_rows)

    if total_runs < 3:
        warnings.append("후보 압축 데이터가 1~2건 수준이라 주간 해석 신뢰도가 낮습니다.")
    if total_candidates == 0:
        warnings.append("집계 가능한 conservative 후보 결과가 없습니다.")
    if len(decision_paths) == 0 or len(decision_rows) == 0:
        warnings.append("실전 결과 데이터 부족: decision log가 없거나 너무 적습니다.")

    lines = [
        "# Weekly Conservative Report",
        "",
        f"- 리포트 생성일: {generated_at}",
        "",
        "## 후보 압축 결과 요약",
        f"- 총 실행 횟수: {total_runs}",
        f"- 총 후보 수: {total_candidates}",
        f"- 총 통과 후보 수: {total_passed}",
        f"- 평균 총점: {avg_score}",
        f"- 가장 자주 등장한 테마: {top_theme}",
        f"- 가장 자주 상위 3위 안에 들어간 종목: {top_name}",
        "",
        "### 집계 대상 후보 결과 파일",
    ]

    if candidate_paths:
        lines.extend(f"- {path.as_posix()}" for path in candidate_paths)
    else:
        lines.append("- 없음")

    lines.extend(["", "### 상위 빈도 테마"])
    if candidate_theme_counter:
        lines.extend(f"- {theme}: {count}회" for theme, count in candidate_theme_counter.most_common(5))
    else:
        lines.append("- 없음")

    lines.extend(["", "### 상위 빈도 종목"])
    if candidate_name_counter:
        lines.extend(f"- {name}: {count}회" for name, count in candidate_name_counter.most_common(5))
    else:
        lines.append("- 없음")

    lines.extend([
        "",
        "## 실제 의사결정/실전 결과 요약",
        f"- 실제 decision log 파일 수: {len(decision_paths)}",
        f"- 실제 진입 횟수: {len(entered_rows)}",
        f"- 미진입 횟수: {len(not_entered_rows)}",
        f"- 평균 result_pct: {avg_result_pct}",
        f"- 평균 result_amount: {avg_result_amount}",
        f"- 가장 자주 나온 no_entry_reason: {no_entry_counter.most_common(1)[0][0] if no_entry_counter else '없음'}",
        f"- 가장 자주 나온 entered=yes 종목: {entered_name_counter.most_common(1)[0][0] if entered_name_counter else '없음'}",
        "",
        "### 집계 대상 decision log 파일",
    ])

    if decision_paths:
        lines.extend(f"- {path.as_posix()}" for path in decision_paths)
    else:
        lines.append("- 없음")

    lines.extend(["", "### review_note 요약"])
    if review_note_summary:
        lines.extend(f"- {item}" for item in review_note_summary)
    else:
        lines.append("- 없음")

    lines.extend(["", "## 경고"])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 없음")

    lines.extend([
        "",
        "## 해석 포인트",
        "- 후보 압축 결과와 실제 진입 행동이 얼마나 일치하는지 본다.",
        "- 미진입 사유가 반복된다면 진입 기준이 지나치게 까다로운지 점검한다.",
        "- review_note가 반복되는 종목/상황은 다음 주 매매 계획에 반영한다.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_LOG_DIR.mkdir(parents=True, exist_ok=True)

    candidate_paths = find_conservative_files()
    decision_paths = find_decision_logs()
    candidate_rows, candidate_warnings = load_candidate_rows(candidate_paths)
    decision_rows, decision_warnings = load_decision_rows(decision_paths)
    warnings = candidate_warnings + decision_warnings
    report_text = build_report(candidate_paths, candidate_rows, decision_paths, decision_rows, warnings)
    OUTPUT_PATH.write_text(report_text, encoding="utf-8")
    print(f"[Saved] {OUTPUT_PATH}")
    print()
    print(report_text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
