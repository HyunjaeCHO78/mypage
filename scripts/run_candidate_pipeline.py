#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the candidate ranking pipeline from a CSV input")
    parser.add_argument("--input", required=True, help="Candidate CSV input path")
    parser.add_argument("--profile", choices=["conservative", "aggressive"], required=True)
    parser.add_argument("--output", help="Optional output path (.json). Defaults to reports/candidates_<profile>_top3.json")
    return parser


def default_output_path(profile: str) -> Path:
    return Path("reports") / f"candidates_{profile}_top3.json"


def run_rank_script(input_path: str, profile: str, output_path: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "scripts/rank_candidates.py",
        "--profile",
        profile,
        "--input",
        input_path,
        "--format",
        "csv",
        "--output",
        str(output_path),
    ]
    return subprocess.run(command, text=True, capture_output=True, check=False)


def load_top_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Output file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def print_summary(profile: str, results: list[dict[str, Any]], output_path: Path) -> None:
    print(f"[Pipeline Summary] profile={profile}")
    print(f"saved_to={output_path}")
    print()
    print("[Top 3 Candidates]")
    if not results:
        print("- 통과 후보가 없습니다.")
        return
    for row in results[:3]:
        print(
            f"{row.get('rank')}. {row.get('name')} [{row.get('ticker')}] | "
            f"score={row.get('total_score')} | passed={row.get('passed')} | "
            f"details={row.get('major_score_details')}"
        )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    output_path = Path(args.output) if args.output else default_output_path(args.profile)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    completed = run_rank_script(str(input_path), args.profile, output_path)
    if completed.stdout:
        print(completed.stdout.strip())
        print()
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)
        return completed.returncode

    results = load_top_results(output_path)
    print_summary(args.profile, results, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
