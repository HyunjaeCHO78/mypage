from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = BASE_DIR / "output" / "universe_stage1.csv"
OUTPUT_PATH = BASE_DIR / "output" / "reports_stage1.csv"


def read_universe_codes(path: Path) -> list[str]:
    """유니버스 파일에서 종목 코드를 읽는다."""
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return [row.get("code", "").strip() for row in reader if row.get("code", "").strip()]


def write_report_stub(path: Path, codes: list[str]) -> None:
    """1차/2차 검증용 리포트 스텁 CSV를 작성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["code", "report_date", "source", "note"]
    today = datetime.now().strftime("%Y-%m-%d")

    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()

        # 실제 수집 대신 예시 스텁만 기록
        for code in codes:
            writer.writerow(
                {
                    "code": code,
                    "report_date": today,
                    "source": "example",
                    "note": "예시 데이터 기반 스텁",
                }
            )


def main() -> None:
    codes = read_universe_codes(UNIVERSE_PATH)
    write_report_stub(OUTPUT_PATH, codes)


if __name__ == "__main__":
    main()
