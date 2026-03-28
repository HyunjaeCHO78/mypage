#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_PATH = Path("templates/candidate_input_template.csv")
PROFILE = "conservative"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DAILY_DIR = Path("reports/daily")
ARCHIVE_DIR = Path("inputs/archive")
OUTPUT_JSON = DAILY_DIR / f"{TODAY}_{PROFILE}_top3.json"
SUMMARY_TXT = DAILY_DIR / f"{TODAY}_{PROFILE}_summary.txt"
ARCHIVE_CSV = ARCHIVE_DIR / f"{TODAY}_candidates.csv"


def ensure_directories() -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def archive_input() -> None:
    shutil.copy2(INPUT_PATH, ARCHIVE_CSV)


def run_pipeline() -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "scripts/run_candidate_pipeline.py",
        "--input",
        str(INPUT_PATH),
        "--profile",
        PROFILE,
        "--output",
        str(OUTPUT_JSON),
    ]
    return subprocess.run(command, text=True, capture_output=True, check=False)


def load_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(results: list[dict[str, Any]]) -> str:
    lines = [
        "[Daily Conservative Summary]",
        f"date={TODAY}",
        f"input={INPUT_PATH}",
        f"archived_input={ARCHIVE_CSV}",
        f"output={OUTPUT_JSON}",
        "",
        "[Top 3 Candidates]",
    ]
    if not results:
        lines.append("- 통과 후보가 없습니다.")
        return "\n".join(lines)

    for row in results[:3]:
        lines.append(
            f"{row.get('rank')}. {row.get('name')} [{row.get('ticker')}] | "
            f"score={row.get('total_score')} | details={row.get('major_score_details')}"
        )
    return "\n".join(lines)


def save_summary(text: str) -> None:
    SUMMARY_TXT.write_text(text + "\n", encoding="utf-8")


def print_final_candidates(results: list[dict[str, Any]]) -> None:
    print("[Final Candidates | Conservative]")
    if not results:
        print("- 통과 후보가 없습니다.")
        return
    for row in results[:3]:
        print(
            f"{row.get('rank')}. {row.get('name')} [{row.get('ticker')}] | "
            f"score={row.get('total_score')} | details={row.get('major_score_details')}"
        )


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"입력 템플릿을 찾을 수 없습니다: {INPUT_PATH}", file=sys.stderr)
        return 1

    ensure_directories()
    try:
        archive_input()
    except Exception as exc:
        print(f"입력 템플릿 보관에 실패했습니다: {exc}", file=sys.stderr)
        return 1

    completed = run_pipeline()
    if completed.stdout:
        print(completed.stdout.strip())
        print()
    if completed.returncode != 0:
        print("보수형 일일 실행에 실패했습니다.", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)
        else:
            print("원인: 파이프라인 실행 중 오류가 발생했습니다.", file=sys.stderr)
        return completed.returncode

    try:
        results = load_results(OUTPUT_JSON)
    except Exception as exc:
        print(f"결과 파일을 읽지 못했습니다: {exc}", file=sys.stderr)
        return 1

    summary_text = build_summary(results)
    save_summary(summary_text)
    print_final_candidates(results)
    print()
    print(f"[Saved JSON] {OUTPUT_JSON}")
    print(f"[Saved Summary] {SUMMARY_TXT}")
    print(f"[Archived Input] {ARCHIVE_CSV}")
    print("[Next Step] python3 scripts/log_daily_decision.py --init-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
