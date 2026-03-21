"""코스피200 유니버스 파일 구조를 점검/생성하는 초안 스크립트."""

from pathlib import Path
import pandas as pd

UNIVERSE_PATH = Path("universe/kospi200_universe.csv")
REQUIRED_COLUMNS = ["종목코드", "종목명", "시장", "섹터", "비고"]


def ensure_universe_file() -> pd.DataFrame:
    """유니버스 파일을 읽고 필수 컬럼 존재 여부를 검증한다."""
    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"유니버스 파일이 없습니다: {UNIVERSE_PATH}")

    df = pd.read_csv(UNIVERSE_PATH, dtype=str).fillna("")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"유니버스 컬럼 누락: {missing}")

    return df[REQUIRED_COLUMNS]


if __name__ == "__main__":
    universe_df = ensure_universe_file()
    print(f"유니버스 점검 완료: {len(universe_df)}개 종목")
