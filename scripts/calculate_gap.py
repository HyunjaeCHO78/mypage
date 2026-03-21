"""현재가 대비 목표가 괴리율/업사이드 계산 스크립트."""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def calculate_gap_percent(current_price: float | int | None, target_price: float | int | None) -> float:
    """목표가괴리율(%) 계산.

    규칙:
    - (최신목표가 - 현재가) / 현재가 * 100
    - 현재가 또는 목표가가 비어 있거나 현재가가 0이면 NaN 반환
    """
    if current_price is None or target_price is None:
        return np.nan
    if pd.isna(current_price) or pd.isna(target_price):
        return np.nan

    current = float(current_price)
    target = float(target_price)
    if current == 0:
        return np.nan

    return (target - current) / current * 100


def calculate_upside_percent(current_price: float | int | None, target_price: float | int | None) -> float:
    """업사이드(%) 계산.

    현재는 괴리율과 동일 수식 사용.
    향후 운영 정책 변경 가능성을 고려해 함수 분리.
    """
    return calculate_gap_percent(current_price, target_price)


def apply_gap_calculation(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame에 괴리율/업사이드 계산을 적용한다."""
    working = df.copy()
    current_series = pd.to_numeric(working.get("현재가"), errors="coerce")
    target_series = pd.to_numeric(working.get("최신목표가"), errors="coerce")

    working["목표가괴리율(%)"] = [
        calculate_gap_percent(c, t) for c, t in zip(current_series, target_series)
    ]
    working["업사이드(%)"] = [
        calculate_upside_percent(c, t) for c, t in zip(current_series, target_series)
    ]
    return working


def main() -> None:
    parser = argparse.ArgumentParser(description="목표가 괴리율 계산")
    parser.add_argument("--input", required=True, help="입력 CSV 경로")
    parser.add_argument("--output", required=True, help="출력 CSV 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path, dtype=str)
    result = apply_gap_calculation(df)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"계산 완료: {output_path}")


if __name__ == "__main__":
    main()
