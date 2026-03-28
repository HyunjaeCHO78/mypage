#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

SCORING_FIELDS = [
    "material_clarity",
    "trading_value",
    "foreign_flow",
    "institutional_flow",
    "program_flow",
    "chart_position",
    "early_stage",
    "next_day_expectation",
    "market_alignment",
    "understanding",
]

DISPLAY_FIELD_LABELS = {
    "material_clarity": "재료",
    "trading_value": "거래대금",
    "foreign_flow": "외국인",
    "institutional_flow": "기관",
    "program_flow": "프로그램",
    "chart_position": "차트",
    "early_stage": "초입성",
    "next_day_expectation": "기대감",
    "market_alignment": "시황일치",
    "understanding": "이해도",
}

ALIASES = {
    "catalyst_clarity": "material_clarity",
    "turnover": "trading_value",
    "chart_setup": "chart_position",
    "next_day_potential": "next_day_expectation",
    "understandability": "understanding",
}

MOCK_CANDIDATES = [
    {
        "ticker": "111111",
        "name": "AlphaBio",
        "theme": "바이오",
        "material_clarity": 2,
        "trading_value": 2,
        "foreign_flow": 1,
        "institutional_flow": 0,
        "program_flow": 1,
        "chart_position": 2,
        "early_stage": 1,
        "next_day_expectation": 2,
        "market_alignment": 2,
        "understanding": 2,
    },
    {
        "ticker": "222222",
        "name": "NeoChip",
        "theme": "반도체",
        "material_clarity": 1,
        "trading_value": 2,
        "foreign_flow": 2,
        "institutional_flow": 2,
        "program_flow": 1,
        "chart_position": 1,
        "early_stage": 1,
        "next_day_expectation": 1,
        "market_alignment": 2,
        "understanding": 1,
    },
    {
        "ticker": "333333",
        "name": "QuantumSoft",
        "theme": "AI 소프트웨어",
        "material_clarity": 1,
        "trading_value": 1,
        "foreign_flow": 0,
        "institutional_flow": 0,
        "program_flow": 1,
        "chart_position": 2,
        "early_stage": 2,
        "next_day_expectation": 2,
        "market_alignment": 1,
        "understanding": 2,
    },
    {
        "ticker": "444444",
        "name": "SolarNext",
        "theme": "태양광",
        "material_clarity": 2,
        "trading_value": 1,
        "foreign_flow": 1,
        "institutional_flow": 1,
        "program_flow": 1,
        "chart_position": 1,
        "early_stage": 2,
        "next_day_expectation": 2,
        "market_alignment": 1,
        "understanding": 1,
    },
    {
        "ticker": "555555",
        "name": "ValueSteel",
        "theme": "철강",
        "material_clarity": 0,
        "trading_value": 1,
        "foreign_flow": 1,
        "institutional_flow": 1,
        "program_flow": 0,
        "chart_position": 1,
        "early_stage": 0,
        "next_day_expectation": 0,
        "market_alignment": 1,
        "understanding": 2,
    },
]


def load_profile(profile_name: str) -> dict[str, Any]:
    path = Path("profiles") / f"{profile_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_numeric(value: Any) -> tuple[Any, str | None]:
    if value in (None, ""):
        return 0, None
    if isinstance(value, (int, float)):
        return value, None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return 0, f"숫자형 변환 실패: {value!r}"
    return (int(number) if number.is_integer() else number), None


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    for old_key, new_key in ALIASES.items():
        if old_key in normalized and new_key not in normalized:
            normalized[new_key] = normalized[old_key]
    return normalized


def load_candidates(input_path: str | None, data_format: str | None) -> list[dict[str, Any]]:
    if input_path is None:
        return [normalize_candidate(item) for item in MOCK_CANDIDATES]

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    detected_format = data_format or path.suffix.lower().lstrip(".")
    if detected_format == "json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list of candidate objects")
        return [normalize_candidate(item) for item in data]

    if detected_format == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            return [normalize_candidate(dict(row)) for row in reader]

    raise ValueError("Supported formats: json, csv")


def validate_required_fields(candidate: dict[str, Any], required_fields: list[str]) -> list[str]:
    warnings = []
    for field in required_fields:
        if field not in candidate or candidate[field] in (None, ""):
            warnings.append(f"필수 필드 누락: {field}")
    return warnings


def score_candidate(candidate: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    candidate = normalize_candidate(candidate)
    warnings = validate_required_fields(candidate, profile["required_fields"])
    details = []
    total_score = 0.0

    for field in SCORING_FIELDS:
        raw_value = candidate.get(field, 0)
        numeric_value, warning = parse_numeric(raw_value)
        field_warnings = []
        if warning:
            field_warnings.append(f"{field}: {warning}")
        if isinstance(numeric_value, (int, float)) and (numeric_value < 0 or numeric_value > 2):
            field_warnings.append(f"{field}: 값 범위 경고 ({numeric_value})")
        safe_value = max(0.0, min(float(numeric_value), 2.0)) if isinstance(numeric_value, (int, float)) else 0.0
        weight = float(profile["weights"].get(field, 1.0))
        weighted_score = round(safe_value * weight, 2)
        total_score += weighted_score
        details.append({
            "field": field,
            "label": DISPLAY_FIELD_LABELS.get(field, field),
            "raw_score": raw_value,
            "normalized_score": round(safe_value, 2),
            "weight": weight,
            "weighted_score": weighted_score,
            "warnings": field_warnings,
        })
        warnings.extend(field_warnings)

    passed = not any(text.startswith("필수 필드 누락") for text in warnings) and round(total_score, 2) >= float(profile["minimum_total_score"])
    return {
        "ticker": str(candidate.get("ticker", "")),
        "name": str(candidate.get("name", "")),
        "theme": str(candidate.get("theme", "")),
        "profile_name": profile["profile_name"],
        "total_score": round(total_score, 2),
        "passed": passed,
        "warnings": warnings,
        "details": details,
        "raw": candidate,
    }


def sort_key(result: dict[str, Any], tie_break_rules: list[str]) -> tuple[Any, ...]:
    values: list[Any] = [-float(result["total_score"])]
    raw = result["raw"]
    for field in tie_break_rules:
        if field == "name":
            values.append(str(raw.get("name", "")))
        else:
            numeric_value, _ = parse_numeric(raw.get(field, 0))
            values.append(-float(numeric_value) if isinstance(numeric_value, (int, float)) else 0.0)
    values.append(str(raw.get("ticker", "")))
    return tuple(values)


def rank_candidates(candidates: list[dict[str, Any]], profile: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results = [score_candidate(candidate, profile) for candidate in candidates]
    passed = [item for item in results if item["passed"]]
    top_results = sorted(passed, key=lambda item: sort_key(item, profile["tie_break_rules"]))[: int(profile["top_n"])]
    for index, result in enumerate(top_results, start=1):
        result["rank"] = index
    for result in results:
        result.setdefault("rank", None)
    return results, top_results


def summarize_details(details: list[dict[str, Any]], top_k: int = 4) -> str:
    sorted_details = sorted(details, key=lambda item: item["weighted_score"], reverse=True)[:top_k]
    return ", ".join(f"{item['label']}={item['weighted_score']}" for item in sorted_details)


def print_results(profile: dict[str, Any], results: list[dict[str, Any]], top_results: list[dict[str, Any]], used_mock: bool) -> None:
    print(f"[Profile] {profile['profile_name']}")
    print(f"Minimum total score: {profile['minimum_total_score']}")
    print(f"Top N: {profile['top_n']}")
    print(f"Source: {'mock data' if used_mock else 'input file'}")
    print()
    print("[All Candidates]")
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        warning_text = f" warnings={len(result['warnings'])}" if result["warnings"] else ""
        print(f"- {result['name']} ({result['ticker']}): {result['total_score']} | {status}{warning_text}")
    print()
    print("[Top Candidates]")
    if not top_results:
        print("- No candidates passed the filter.")
        return
    for result in top_results:
        print(
            f"{result['rank']}. {result['name']} [{result['ticker']}] | total={result['total_score']} | "
            f"profile={result['profile_name']} | details={summarize_details(result['details'])}"
        )
    print()
    print("[Warnings]")
    warnings_found = False
    for result in results:
        if result["warnings"]:
            warnings_found = True
            print(f"- {result['name']} ({result['ticker']}):")
            for warning in result["warnings"]:
                print(f"  * {warning}")
    if not warnings_found:
        print("- none")


def serialize_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        rows.append({
            "rank": result.get("rank"),
            "profile_name": result["profile_name"],
            "ticker": result["ticker"],
            "name": result["name"],
            "theme": result["theme"],
            "total_score": result["total_score"],
            "passed": result["passed"],
            "major_score_details": summarize_details(result["details"]),
            "warnings": " | ".join(result["warnings"]),
        })
    return rows


def save_results(path_str: str, results: list[dict[str, Any]]) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = serialize_results(results)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    if path.suffix.lower() == ".csv":
        fieldnames = [
            "rank", "profile_name", "ticker", "name", "theme",
            "total_score", "passed", "major_score_details", "warnings"
        ]
        with path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return
    raise ValueError("Output file must end with .json or .csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank stock candidates using a profile-based scoring engine")
    parser.add_argument("--profile", choices=["conservative", "aggressive"], default="conservative")
    parser.add_argument("--input", help="Optional candidate input file")
    parser.add_argument("--format", choices=["json", "csv"], help="Input format override")
    parser.add_argument("--output", help="Optional output path (.json or .csv)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    profile = load_profile(args.profile)
    used_mock = args.input is None
    candidates = load_candidates(args.input, args.format)
    results, top_results = rank_candidates(candidates, profile)
    print_results(profile, results, top_results, used_mock=used_mock)
    if args.output:
        save_results(args.output, top_results)
        print()
        print(f"[Saved] {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
