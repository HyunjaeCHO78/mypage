from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.backtester import run_backtest
from src.broker_mock import MockBroker
from src.indicators import add_indicators
from src.scanner import run_scan
from src.strategy import detect_exit_signal, detect_pullback_signal, detect_stage1_signal, detect_stage6_signal
from src.utils import ensure_directories, format_pct, group_by_symbol, load_config, load_ohlcv_csv, save_rows



def setup_logging(log_dir: str) -> None:
    ensure_directories([log_dir])
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(Path(log_dir) / "run.log", encoding="utf-8"), logging.StreamHandler()],
    )



def print_table(rows: list[dict]) -> None:
    if not rows:
        print("No rows")
        return
    headers = list(rows[0].keys())
    widths = {header: max(len(header), *(len(str(row.get(header, ""))) for row in rows)) for header in headers}
    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))



def run_mock_trade(rows: list[dict], config: dict, output_path: str) -> list[dict]:
    defaults = config["defaults"]
    broker_cfg = config["broker"]
    broker = MockBroker(starting_cash=broker_cfg["starting_cash"], slippage_bps=broker_cfg["slippage_bps"], fee_bps=broker_cfg["fee_bps"])
    enriched = add_indicators(rows, atr_period=defaults["atr_period"])
    grouped = group_by_symbol(enriched)
    orders: list[dict] = []
    entry_meta: dict[str, dict] = {}

    for symbol, history in grouped.items():
        for idx, row in enumerate(history):
            owned = broker.get_positions().get(symbol, 0)
            if owned == 0:
                should_buy = detect_stage1_signal(row) or detect_stage6_signal(row) or detect_pullback_signal(history, idx, defaults["scanner_lookback"])
                if should_buy:
                    result = broker.buy(symbol, 1, row["close"])
                    if result.status == "filled":
                        entry_meta[symbol] = {"entry_low": row["low"], "entry_price": broker.get_average_price(symbol)}
                    orders.append({"date": row["date"], "symbol": symbol, "side": "BUY", "price": round(result.price, 2), "quantity": 1, "status": result.status, "order_id": result.order_id, "fee": round(result.fee, 2), "cash_after": round(broker.get_cash(), 2)})
            else:
                meta = entry_meta.get(symbol, {})
                reason, should_exit = detect_exit_signal(history, idx, entry_price=meta.get("entry_price"), entry_low=meta.get("entry_low"))
                if reason == "warning":
                    orders.append({"date": row["date"], "symbol": symbol, "side": "HOLD:warning", "price": round(row["close"], 2), "quantity": owned, "status": "logged", "order_id": "", "fee": 0.0, "cash_after": round(broker.get_cash(), 2)})
                elif should_exit:
                    sell_quantity = max(1, owned // 2) if reason == "reduce" and owned > 1 else owned
                    result = broker.sell(symbol, sell_quantity, row["close"])
                    orders.append({"date": row["date"], "symbol": symbol, "side": f"SELL:{reason}", "price": round(result.price, 2), "quantity": sell_quantity, "status": result.status, "order_id": result.order_id, "fee": round(result.fee, 2), "cash_after": round(broker.get_cash(), 2)})
    save_rows(orders, output_path, fieldnames=["date", "symbol", "side", "price", "quantity", "status", "order_id", "fee", "cash_after"])
    return orders



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gojiro moving average auto trading system")
    parser.add_argument("--mode", required=True, choices=["backtest", "scan", "mock-trade"])
    parser.add_argument("--data", required=True)
    parser.add_argument("--config", default="config.yaml")
    return parser



def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    ensure_directories([config["defaults"]["report_dir"], config["defaults"]["log_dir"], config["defaults"]["data_dir"]])
    setup_logging(config["defaults"]["log_dir"])
    try:
        rows = load_ohlcv_csv(args.data)
        if args.mode == "scan":
            output = str(Path(config["defaults"]["report_dir"]) / "scan_results.csv")
            results = run_scan(rows, output, config["defaults"]["scanner_lookback"])
            logging.info("Scan complete: %s", output)
            print_table(results)
        elif args.mode == "backtest":
            result = run_backtest(rows, config, str(Path(config["defaults"]["report_dir"]) / "backtest_trades.csv"), str(Path(config["defaults"]["report_dir"]) / "backtest_equity.csv"))
            summary = [{
                "CAGR": format_pct(result.metrics["cagr"]),
                "MDD": format_pct(result.metrics["mdd"]),
                "Win Rate": format_pct(result.metrics["win_rate"]),
                "Profit Factor": round(result.metrics["profit_factor"], 2) if result.metrics["profit_factor"] != float('inf') else 'inf',
                "Average Return": format_pct(result.metrics["average_return"]),
                "Max Consecutive Loss": result.metrics["max_consecutive_loss"],
            }]
            logging.info("Backtest complete")
            print_table(summary)
            if result.symbol_summary:
                print("\n[Symbol Summary]")
                print_table(result.symbol_summary)
        else:
            orders = run_mock_trade(rows, config, str(Path(config["defaults"]["report_dir"]) / "mock_trade_orders.csv"))
            logging.info("Mock trade complete")
            print_table(orders)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Execution failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
