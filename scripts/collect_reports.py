"""리포트/컨센서스 수집 파이프라인의 1차 초안.

현재 단계에서는 외부 수집을 수행하지 않고,
유니버스 기반으로 최종 출력 테이블의 빈 틀을 생성한다.
"""

from datetime import datetime
from pathlib import Path
import pandas as pd

UNIVERSE_PATH = Path("universe/kospi200_universe.csv")
OUTPUT_PATH = Path("output/kospi200_targetprice_table.csv")

FINAL_COLUMNS = [
    "종목코드",
    "종목명",
    "시장",
    "섹터",
    "현재가",
    "최신목표가",
    "1개월평균목표가",
    "3개월평균목표가",
    "최고목표가",
    "최저목표가",
    "최신투자의견",
    "리포트수",
    "최신리포트날짜",
    "최근주요증권사",
    "목표가괴리율(%)",
    "업사이드(%)",
    "밸류메모",
    "데이터출처",
    "최종업데이트일시",
]


def build_empty_table_from_universe(universe_df: pd.DataFrame) -> pd.DataFrame:
    """유니버스를 기반으로 최종 테이블의 기본 골격을 생성한다."""
    table = pd.DataFrame(columns=FINAL_COLUMNS)
    table[["종목코드", "종목명", "시장", "섹터"]] = universe_df[["종목코드", "종목명", "시장", "섹터"]]
    table["최종업데이트일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return table


def main() -> None:
    universe_df = pd.read_csv(UNIVERSE_PATH, dtype=str).fillna("")
    result_df = build_empty_table_from_universe(universe_df)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"출력 완료: {OUTPUT_PATH} ({len(result_df)}행)")


if __name__ == "__main__":
    main()
