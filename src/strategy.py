from __future__ import annotations


REQUIRED_KEYS = ["ma5", "ma20", "ma40", "ma5_slope", "ma20_slope", "ma40_slope", "volume_sma20"]



def _valid_row(row: dict) -> bool:
    return all(row.get(key) is not None for key in REQUIRED_KEYS)



def detect_stage6_signal(row: dict) -> bool:
    if not _valid_row(row):
        return False
    return (
        row["ma5"] > row["ma40"] > row["ma20"]
        and row["ma5_slope"] > 0
        and row["close"] > row["ma5"]
        and row["volume"] > row["volume_sma20"]
    )



def detect_stage1_signal(row: dict) -> bool:
    if not _valid_row(row):
        return False
    return (
        row["ma5"] > row["ma20"] > row["ma40"]
        and row["ma5_slope"] > 0
        and row["ma20_slope"] > 0
        and row["ma40_slope"] >= 0
        and row["close"] > row["ma5"]
    )



def detect_pullback_signal(history: list[dict], idx: int, lookback: int = 20) -> bool:
    if idx <= 0:
        return False
    current = history[idx]
    previous = history[idx - 1]
    if any(current.get(key) is None for key in ["ma5", "ma20", "ma40", "ma20_slope", "ma40_slope"]):
        return False

    recent = history[max(0, idx - lookback):idx]
    had_stage1 = any(
        row.get("ma5") is not None and row.get("ma20") is not None and row.get("ma40") is not None and
        row.get("ma20_slope") is not None and row.get("ma40_slope") is not None and
        row["ma5"] > row["ma20"] > row["ma40"] and row["ma20_slope"] > 0 and row["ma40_slope"] >= 0
        for row in recent
    )

    touched_pullback_zone = (
        previous.get("ma5") is not None and previous["low"] <= previous["ma5"] <= previous["high"]
    ) or (
        previous.get("ma20") is not None and previous["low"] <= previous["ma20"] <= previous["high"]
    ) or (
        previous.get("ma5") is not None and previous["close"] <= previous["ma5"]
    ) or (
        previous.get("ma20") is not None and previous["close"] <= previous["ma20"]
    )

    reclaim_ma5 = previous.get("ma5") is not None and current.get("ma5") is not None and current["close"] > current["ma5"] and previous["close"] <= previous["ma5"]

    return had_stage1 and touched_pullback_zone and reclaim_ma5 and current["ma20_slope"] > 0 and current["ma40_slope"] >= 0



def detect_exit_signal(history: list[dict], idx: int, entry_price: float | None = None, entry_low: float | None = None) -> tuple[str, bool]:
    row = history[idx]
    recent = history[max(0, idx - 1): idx + 1]
    below_ma5_2days = len(recent) == 2 and all(item.get("ma5") is not None and item["close"] < item["ma5"] for item in recent)
    below_ma20_2days = len(recent) == 2 and all(item.get("ma20") is not None and item["close"] < item["ma20"] for item in recent)

    if entry_low is not None and row["low"] < entry_low:
        return "initial_stop_entry_low", True
    if entry_price is not None and row.get("atr") is not None and row["close"] < entry_price - (row["atr"] * 2):
        return "initial_stop_atr", True
    if below_ma20_2days or (row.get("ma20_slope") is not None and row["ma20_slope"] < 0):
        return "final_exit", True
    if row.get("ma5") is not None and row.get("ma20") is not None and row.get("ma20_slope") is not None and row["ma5"] < row["ma20"] and row["ma20_slope"] <= 0:
        return "reduce", True
    if below_ma5_2days:
        return "warning", False
    return "hold", False
