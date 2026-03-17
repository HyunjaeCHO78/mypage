from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
GAP_PATH = BASE_DIR / "output" / "gap_stage2.csv"
REPORT_PATH = BASE_DIR / "output" / "reports_stage1.csv"
FINAL_PATH = BASE_DIR / "output" / "kospi200_targetprice_table.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as fp:
        return [dict(row) for row in csv.DictReader(fp)]


def map_report_notes(report_rows: list[dict[str, str]]) -> dict[str, str]:
    """코드 기준 note 매핑을 만든다."""
    mapping: dict[str, str] = {}
    for row in report_rows:
        code = row.get("code", "").strip()
        if code and code not in mapping:
            mapping[code] = row.get("note", "")
    return mapping


def write_final(path: Path, gap_rows: list[dict[str, str]], note_map: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["code", "name", "current_price", "target_price", "gap_pct", "as_of", "note"]

    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()

        for row in gap_rows:
            code = row.get("code", "").strip()
            writer.writerow(
                {
                    "code": code,
                    "name": row.get("name", ""),
                    "current_price": row.get("current_price", ""),
                    "target_price": row.get("target_price", ""),
                    "gap_pct": row.get("gap_pct", ""),
                    "as_of": row.get("as_of", ""),
                    "note": note_map.get(code, ""),
                }
            )


def main() -> None:
    gap_rows = read_csv(GAP_PATH)
    report_rows = read_csv(REPORT_PATH)
    note_map = map_report_notes(report_rows)

    # gap_rows가 비어 있어도 최종 템플릿 CSV(헤더 포함)를 생성
    write_final(FINAL_PATH, gap_rows, note_map)


if __name__ == "__main__":
    main()
