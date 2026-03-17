from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = BASE_DIR / "output" / "universe_stage1.csv"
OUTPUT_PATH = BASE_DIR / "output" / "gap_stage2.csv"


def parse_float(value: str) -> float | None:
    """문자열 숫자를 안전하게 float으로 변환한다."""
    value = (value or "").replace(",", "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def calculate_gap_pct(current_price: str, target_price: str) -> str:
    """목표가/현재가가 모두 있을 때만 괴리율을 계산한다."""
    current = parse_float(current_price)
    target = parse_float(target_price)

    # 값이 없거나 0이면 빈 값 처리
    if current in (None, 0.0) or target is None:
        return ""

    gap_pct = ((target - current) / current) * 100
    return f"{gap_pct:.2f}"


def read_universe(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return [dict(row) for row in reader]


def write_gap(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["code", "name", "current_price", "target_price", "gap_pct", "as_of"]

    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    universe_rows = read_universe(UNIVERSE_PATH)
    result: list[dict[str, str]] = []

    for row in universe_rows:
        result.append(
            {
                "code": row.get("code", ""),
                "name": row.get("name", ""),
                "current_price": row.get("current_price", ""),
                "target_price": row.get("target_price", ""),
                "gap_pct": calculate_gap_pct(row.get("current_price", ""), row.get("target_price", "")),
                "as_of": row.get("as_of", ""),
            }
        )

    # 입력이 없어도 헤더만 있는 CSV를 생성해 후속 단계가 실패하지 않도록 함
    write_gap(OUTPUT_PATH, result)


if __name__ == "__main__":
    main()
