#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
장 마감 데이터를 수집해서 input/market_close.json 파일을 생성하는 스크립트.

요약:
- yfinance로 주요 지표/ETF의 최근 종가를 조회
- 최근 2개 종가를 바탕으로 전일 대비 변동률(%) 계산
- 값이 없으면 null(None)로 저장
- 결과를 UTF-8(JSON)으로 저장하고 생성 경로를 출력
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import yfinance as yf


# 수집 대상 티커 정의
TICKERS = {
    "us10y_futures": "ZN=F",                 # 미국 10년물 국채선물
    "wti_futures": "CL=F",                   # WTI 선물
    "sp500": "^GSPC",                        # S&P500
    "nasdaq": "^IXIC",                       # 나스닥 종합
    "kodex_us10y": "308620.KS",              # KODEX 미국10년국채선물
    "kodex_wti_inverse": "271050.KS",        # KODEX WTI원유선물인버스(H)
}


def safe_float(value) -> Optional[float]:
    """pandas/numpy 타입을 JSON 직렬화 가능한 float 또는 None으로 변환."""
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def fetch_close_and_change_pct(ticker: str) -> Tuple[Optional[float], Optional[float]]:
    """
    단일 티커에 대해 최근 종가와 전일 대비 변동률(%)을 계산한다.

    반환값:
    - close: 최근 종가
    - change_pct: ((최근종가 - 전일종가) / 전일종가) * 100

    데이터가 부족하거나 예외가 발생하면 (None, None)을 반환한다.
    """
    try:
        # period=7d로 받아 두고, 종가가 2개 이상 존재하는지 확인
        hist = yf.Ticker(ticker).history(period="7d", interval="1d", auto_adjust=False)
        if hist.empty or "Close" not in hist.columns:
            return None, None

        close_series = hist["Close"].dropna()
        if len(close_series) == 0:
            return None, None

        latest_close = safe_float(close_series.iloc[-1])

        # 전일 데이터가 없는 경우 변동률은 계산 불가
        if len(close_series) < 2:
            return latest_close, None

        prev_close = safe_float(close_series.iloc[-2])
        if latest_close is None or prev_close in (None, 0):
            return latest_close, None

        change_pct = ((latest_close - prev_close) / prev_close) * 100.0
        return latest_close, round(change_pct, 4)

    except Exception:
        # 개별 티커 오류가 전체 실행을 막지 않도록 안전하게 처리
        return None, None


def build_output_payload() -> dict:
    """요구된 JSON 스키마에 맞춰 결과 딕셔너리를 생성한다."""
    us10y_close, us10y_chg = fetch_close_and_change_pct(TICKERS["us10y_futures"])
    wti_close, wti_chg = fetch_close_and_change_pct(TICKERS["wti_futures"])
    sp_close, sp_chg = fetch_close_and_change_pct(TICKERS["sp500"])
    ndq_close, ndq_chg = fetch_close_and_change_pct(TICKERS["nasdaq"])
    kodex_bond_close, kodex_bond_chg = fetch_close_and_change_pct(TICKERS["kodex_us10y"])
    kodex_wti_inv_close, kodex_wti_inv_chg = fetch_close_and_change_pct(TICKERS["kodex_wti_inverse"])

    # 날짜는 시스템 로컬 날짜(YYYY-MM-DD) 기준
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

    return {
        "date": today_str,
        "us10y_futures_close": us10y_close,
        "us10y_futures_change_pct": us10y_chg,
        "wti_futures_close": wti_close,
        "wti_futures_change_pct": wti_chg,
        "sp500_close": sp_close,
        "sp500_change_pct": sp_chg,
        "nasdaq_close": ndq_close,
        "nasdaq_change_pct": ndq_chg,
        "kodex_us10y_close": kodex_bond_close,
        "kodex_us10y_change_pct": kodex_bond_chg,
        "kodex_wti_inverse_close": kodex_wti_inv_close,
        "kodex_wti_inverse_change_pct": kodex_wti_inv_chg,
        # 아래 4개는 운용자가 이후 입력/보정할 수 있도록 기본값 제공
        "cash_ratio_current": None,
        "position_kodex_us10y": None,
        "position_kodex_wti_inverse": None,
        "notes": None,
    }


def main() -> None:
    """실행 진입점: JSON 생성 후 저장 경로 출력."""
    # 스크립트 위치 기준으로 상대 경로를 안정적으로 계산
    base_dir = Path(__file__).resolve().parent
    input_dir = base_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    output_file = input_dir / "market_close.json"

    try:
        payload = build_output_payload()

        # UTF-8 + ensure_ascii=False로 한글 깨짐 방지
        output_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"생성 완료: {output_file}")
    except Exception as exc:
        print(f"오류 발생: market_close.json 생성 실패 - {exc}")


if __name__ == "__main__":
    main()
