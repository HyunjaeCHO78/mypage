from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

# 1차/2차 공통 경로 설정
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "universe_example.csv"
OUTPUT_PATH = BASE_DIR / "output" / "universe_stage1.csv"


def read_universe_rows(path: Path) -> list[dict[str, str]]:
    """예시 유니버스 CSV를 읽는다. 파일이 없으면 빈 목록을 반환한다."""
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return [dict(row) for row in reader]


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """필수 컬럼을 보정하고 as_of 값을 채운다."""
    today = datetime.now().strftime("%Y-%m-%d")
    normalized: list[dict[str, str]] = []

    for row in rows:
        def text(value: str | None) -> str:
            return (value or "").strip()

        normalized.append(
            {
                "code": text(row.get("code")),
                "name": text(row.get("name")),
                "current_price": text(row.get("current_price")),
                "target_price": text(row.get("target_price")),
                "as_of": text(row.get("as_of")) or today,
            }
        )

    return normalized


def write_universe_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """유니버스 스테이지 산출물을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["code", "name", "current_price", "target_price", "as_of"]

    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    # pandas 없이 표준 라이브러리만으로 실행 가능하도록 구성
    rows = read_universe_rows(DATA_PATH)
    normalized = normalize_rows(rows)
    write_universe_rows(OUTPUT_PATH, normalized)


if __name__ == "__main__":
    main()
