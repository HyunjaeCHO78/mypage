from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume", "symbol"]
REQUIRED_CONFIG_SECTIONS = ["defaults", "broker", "strategy"]



def ensure_directories(paths: list[str]) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)



def load_config(path: str) -> dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping object.")

    missing_sections = [section for section in REQUIRED_CONFIG_SECTIONS if section not in loaded]
    if missing_sections:
        raise ValueError(f"Missing required config sections: {missing_sections}")

    return loaded



def load_ohlcv_csv(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV header is missing")

        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        rows: list[dict[str, Any]] = []
        for raw in reader:
            try:
                rows.append(
                    {
                        "date": datetime.strptime(raw["date"], "%Y-%m-%d"),
                        "open": float(raw["open"]),
                        "high": float(raw["high"]),
                        "low": float(raw["low"]),
                        "close": float(raw["close"]),
                        "volume": float(raw["volume"]),
                        "symbol": raw["symbol"],
                    }
                )
            except (TypeError, ValueError):
                continue

    rows.sort(key=lambda row: (row["symbol"], row["date"]))
    return rows



def save_rows(rows: Iterable[dict[str, Any]], path: str, fieldnames: list[str] | None = None) -> None:
    rows = list(rows)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = fieldnames or (list(rows[0].keys()) if rows else [])
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        if header:
            writer.writeheader()
        for row in rows:
            normalized = {key: (value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else value) for key, value in row.items()}
            writer.writerow(normalized)



def format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"



def group_by_symbol(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["symbol"], []).append(row)
    return grouped
