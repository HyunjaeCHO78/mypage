"""다중 소스 병합 초안 스크립트."""

import pandas as pd


def merge_sources(base_df: pd.DataFrame, source_dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """기본 테이블과 소스별 DataFrame을 순차 병합한다(초안)."""
    merged = base_df.copy()
    for df in source_dfs:
        if "종목코드" not in df.columns:
            continue
        merged = merged.merge(df, on="종목코드", how="left", suffixes=("", "_src"))
    return merged


if __name__ == "__main__":
    print("merge_consensus.py 초안: 병합 전략 세부화 필요")
