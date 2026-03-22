from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable


REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume", "symbol"]



def ensure_directories(paths: list[str]) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)



def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")



def load_config(path: str) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    current_section: Dict[str, Any] | None = None
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" ") and line.endswith(":"):
                section_name = line[:-1]
                current_section = {}
                config[section_name] = current_section
                continue
            if ":" in line and current_section is not None:
                key, value = line.strip().split(":", 1)
                current_section[key.strip()] = _parse_scalar(value)
    return config



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
