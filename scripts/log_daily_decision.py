#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TEMPLATE_PATH = Path("templates/daily_decision_log_template.csv")
LOGS_DIR = Path("logs/daily_decisions")
DEFAULT_LOG_PATH = LOGS_DIR / f"{TODAY}_decision_log.csv"
FIELDNAMES = [
    "date",
    "ticker",
    "name",
    "selected_rank",
    "entered",
    "entry_reason",
    "no_entry_reason",
    "result_pct",
    "result_amount",
    "review_note",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or append a daily decision log")
    parser.add_argument("--date", default=TODAY, help="Log date in YYYY-MM-DD format")
    parser.add_argument("--init-only", action="store_true", help="Create the daily log file from template/header and exit")
    parser.add_argument("--ticker")
    parser.add_argument("--name")
    parser.add_argument("--selected-rank")
    parser.add_argument("--entered", choices=["yes", "no"])
    parser.add_argument("--entry-reason", default="")
    parser.add_argument("--no-entry-reason", default="")
    parser.add_argument("--result-pct", default="0")
    parser.add_argument("--result-amount", default="0")
    parser.add_argument("--review-note", default="")
    return parser


def log_path_for(date_str: str) -> Path:
    return LOGS_DIR / f"{date_str}_decision_log.csv"


def ensure_log_exists(path: Path) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if TEMPLATE_PATH.exists():
        shutil.copy2(TEMPLATE_PATH, path)
        return
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writeheader()


def append_row(path: Path, row: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=FIELDNAMES)
        writer.writerow(row)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    path = log_path_for(args.date)
    ensure_log_exists(path)

    if args.init_only:
        print(f"[Decision Log Ready] {path}")
        return 0

    required_for_append = [args.ticker, args.name, args.selected_rank, args.entered]
    if any(value is None for value in required_for_append):
        print(f"[Decision Log Ready] {path}")
        print("행 추가를 하려면 최소한 --ticker --name --selected-rank --entered 를 함께 넣어야 합니다.")
        return 0

    row = {
        "date": args.date,
        "ticker": args.ticker or "",
        "name": args.name or "",
        "selected_rank": args.selected_rank or "",
        "entered": args.entered or "",
        "entry_reason": args.entry_reason,
        "no_entry_reason": args.no_entry_reason,
        "result_pct": args.result_pct,
        "result_amount": args.result_amount,
        "review_note": args.review_note,
    }
    append_row(path, row)
    print(f"[Decision Logged] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
