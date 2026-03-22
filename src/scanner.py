from __future__ import annotations

from src.indicators import add_indicators
from src.strategy import detect_pullback_signal, detect_stage1_signal, detect_stage6_signal
from src.utils import group_by_symbol, save_rows


SCAN_LABELS = ["stage6_candidate", "stage1_candidate", "pullback_candidate", "no_signal"]



def classify_symbol(history: list[dict], lookback: int = 20) -> str:
    idx = len(history) - 1
    latest = history[idx]
    if detect_stage1_signal(latest):
        return "stage1_candidate"
    if detect_stage6_signal(latest):
        return "stage6_candidate"
    if detect_pullback_signal(history, idx, lookback=lookback):
        return "pullback_candidate"
    return "no_signal"



def _fmt(value: float | None, digits: int = 4) -> float | str:
    return round(value, digits) if value is not None else ""



def run_scan(rows: list[dict], output_path: str, lookback: int = 20) -> list[dict]:
    enriched = add_indicators(rows)
    results: list[dict] = []
    for symbol, history in group_by_symbol(enriched).items():
        latest = history[-1]
        results.append(
            {
                "date": latest["date"].strftime("%Y-%m-%d"),
                "symbol": symbol,
                "signal": classify_symbol(history, lookback=lookback),
                "close": round(latest["close"], 2),
                "ma5": _fmt(latest["ma5"]),
                "ma20": _fmt(latest["ma20"]),
                "ma40": _fmt(latest["ma40"]),
                "ma5_slope": _fmt(latest["ma5_slope"]),
                "ma20_slope": _fmt(latest["ma20_slope"]),
                "ma40_slope": _fmt(latest["ma40_slope"]),
                "volume_sma20": _fmt(latest["volume_sma20"], 2),
                "volume": int(latest["volume"]),
            }
        )
    results.sort(key=lambda row: (row["signal"], row["symbol"]))
    save_rows(results, output_path)
    return results
