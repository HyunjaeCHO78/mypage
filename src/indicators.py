from __future__ import annotations

from collections import deque

from src.utils import group_by_symbol



def _rolling_mean(values: deque[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)



def add_indicators(rows: list[dict], ma_short: int = 5, ma_mid: int = 20, ma_long: int = 40, atr_period: int = 14) -> list[dict]:
    enriched: list[dict] = []
    for symbol, history in group_by_symbol(rows).items():
        close5: deque[float] = deque(maxlen=ma_short)
        close20: deque[float] = deque(maxlen=ma_mid)
        close40: deque[float] = deque(maxlen=ma_long)
        vol20: deque[float] = deque(maxlen=20)
        tr_values: deque[float] = deque(maxlen=atr_period)
        prev_close: float | None = None
        prev_ma5: float | None = None
        prev_ma20: float | None = None
        prev_ma40: float | None = None

        for row in history:
            record = dict(row)
            close5.append(row["close"])
            close20.append(row["close"])
            close40.append(row["close"])
            vol20.append(row["volume"])

            ma5 = _rolling_mean(close5) if len(close5) == ma_short else None
            ma20 = _rolling_mean(close20) if len(close20) == ma_mid else None
            ma40 = _rolling_mean(close40) if len(close40) == ma_long else None
            vol_sma20 = _rolling_mean(vol20) if len(vol20) == 20 else None

            if prev_close is None:
                tr = row["high"] - row["low"]
            else:
                tr = max(row["high"] - row["low"], abs(row["high"] - prev_close), abs(row["low"] - prev_close))
            tr_values.append(tr)
            atr = _rolling_mean(tr_values) if len(tr_values) == atr_period else None

            record["ma5"] = ma5
            record["ma20"] = ma20
            record["ma40"] = ma40
            record["volume_sma20"] = vol_sma20
            record["ma5_slope"] = (ma5 - prev_ma5) if ma5 is not None and prev_ma5 is not None else None
            record["ma20_slope"] = (ma20 - prev_ma20) if ma20 is not None and prev_ma20 is not None else None
            record["ma40_slope"] = (ma40 - prev_ma40) if ma40 is not None and prev_ma40 is not None else None
            record["atr"] = atr
            enriched.append(record)

            prev_close = row["close"]
            prev_ma5 = ma5 if ma5 is not None else prev_ma5
            prev_ma20 = ma20 if ma20 is not None else prev_ma20
            prev_ma40 = ma40 if ma40 is not None else prev_ma40
    enriched.sort(key=lambda row: (row["date"], row["symbol"]))
    return enriched
