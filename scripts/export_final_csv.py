"""최종 CSV 정렬/출력 초안 스크립트."""

from pathlib import Path
import pandas as pd

INPUT_PATH = Path("output/kospi200_targetprice_table.csv")
OUTPUT_PATH = Path("output/kospi200_targetprice_table.csv")

ORDERED_COLUMNS = [
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


def export_ordered_csv(df: pd.DataFrame, output_path: Path) -> None:
    """컬럼 순서를 표준 스키마에 맞춰 저장한다."""
    for col in ORDERED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[ORDERED_COLUMNS]
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    frame = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    export_ordered_csv(frame, OUTPUT_PATH)
    print(f"최종 CSV 내보내기 완료: {OUTPUT_PATH}")
