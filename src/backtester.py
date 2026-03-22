from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.indicators import add_indicators
from src.portfolio import Portfolio, Position, PositionTranche
from src.risk import calculate_position_size
from src.strategy import detect_exit_signal, detect_pullback_signal, detect_stage1_signal, detect_stage6_signal
from src.utils import group_by_symbol, save_rows


@dataclass
class BacktestResult:
    trades: list[dict]
    equity_curve: list[dict]
    symbol_summary: list[dict]
    metrics: dict[str, float]


def _compute_max_consecutive_losses(closed_trades: list[dict]) -> int:
    max_streak = 0
    current = 0
    for trade in closed_trades:
        if trade["pnl"] < 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _compute_trade_stats(closed_trades: list[dict[str, Any]]) -> dict[str, Any]:
    wins = [trade for trade in closed_trades if trade["pnl"] > 0]
    losses = [trade for trade in closed_trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    returns = [trade.get("return_pct", 0.0) for trade in closed_trades]
    return {
        "closed_trades": len(closed_trades),
        "win_rate": round(len(wins) / len(closed_trades), 4) if closed_trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else ("inf" if gross_profit > 0 else 0.0),
        "average_return": round(sum(returns) / len(returns), 4) if returns else 0.0,
        "max_consecutive_loss": _compute_max_consecutive_losses(closed_trades),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def _build_symbol_summary(trades: list[dict]) -> list[dict]:
    summary: dict[str, dict] = {}
    for trade in trades:
        symbol = trade["symbol"]
        bucket = summary.setdefault(
            symbol,
            {
                "symbol": symbol,
                "buy_count": 0,
                "sell_count": 0,
                "realized_pnl": 0.0,
                "average_return": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "closed_trades": 0,
                "max_consecutive_loss": 0,
            },
        )
        if trade["action"] == "BUY":
            bucket["buy_count"] += 1
        elif trade["action"] == "SELL":
            bucket["sell_count"] += 1
            bucket["realized_pnl"] += trade["pnl"]

    for symbol, bucket in summary.items():
        closed = [trade for trade in trades if trade["symbol"] == symbol and trade["action"] == "SELL"]
        stats = _compute_trade_stats(closed)
        bucket["average_return"] = stats["average_return"]
        bucket["win_rate"] = stats["win_rate"]
        bucket["profit_factor"] = stats["profit_factor"]
        bucket["closed_trades"] = stats["closed_trades"]
        bucket["max_consecutive_loss"] = stats["max_consecutive_loss"]
        bucket["realized_pnl"] = round(bucket["realized_pnl"], 2)
    return sorted(summary.values(), key=lambda row: row["symbol"])


def _compute_metrics(equity_curve: list[dict], trades: list[dict], initial_equity: float) -> dict[str, float]:
    if not equity_curve:
        return {"cagr": 0.0, "mdd": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "average_return": 0.0, "max_consecutive_loss": 0}
    days = max((equity_curve[-1]["date"] - equity_curve[0]["date"]).days, 1)
    ending_equity = equity_curve[-1]["equity"]
    cagr = (ending_equity / initial_equity) ** (365 / days) - 1 if ending_equity > 0 else -1.0
    peak = equity_curve[0]["equity"]
    mdd = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        drawdown = (point["equity"] - peak) / peak
        mdd = min(mdd, drawdown)
    closed = [trade for trade in trades if trade["action"] == "SELL"]
    stats = _compute_trade_stats(closed)
    profit_factor = float("inf") if stats["profit_factor"] == "inf" else stats["profit_factor"]
    return {
        "cagr": cagr,
        "mdd": mdd,
        "win_rate": stats["win_rate"],
        "profit_factor": profit_factor,
        "average_return": stats["average_return"],
        "max_consecutive_loss": stats["max_consecutive_loss"],
    }


def _entry_signal_name(row: dict, history: list[dict], idx: int, lookback: int) -> str | None:
    if detect_stage1_signal(row):
        return "stage1"
    if detect_stage6_signal(row):
        return "stage6"
    if detect_pullback_signal(history, idx, lookback):
        return "pullback"
    return None


def _sell_quantity(position: Position, quantity: int, price: float, reason: str, date, trades: list[dict], portfolio: Portfolio, symbol: str) -> None:
    removed_tranches = position.trim(quantity)
    total_qty = sum(tranche.quantity for tranche in removed_tranches)
    if total_qty <= 0:
        return
    realized_cost = sum(tranche.entry_price * tranche.quantity for tranche in removed_tranches)
    avg_cost = realized_cost / total_qty
    pnl = (price - avg_cost) * total_qty
    return_pct = ((price - avg_cost) / avg_cost) if avg_cost > 0 else 0.0
    portfolio.cash += price * total_qty
    portfolio.realized_pnl += pnl
    trades.append(
        {
            "date": date,
            "symbol": symbol,
            "action": "SELL",
            "price": round(price, 2),
            "quantity": total_qty,
            "reason": reason,
            "pnl": round(pnl, 2),
            "return_pct": round(return_pct, 4),
        }
    )
    if position.quantity == 0:
        portfolio.positions.pop(symbol, None)


def _portfolio_metrics_rows(metrics: dict[str, float]) -> list[dict[str, float | str | int]]:
    return [
        {"metric": "cagr", "value": round(metrics["cagr"], 6)},
        {"metric": "mdd", "value": round(metrics["mdd"], 6)},
        {"metric": "win_rate", "value": round(metrics["win_rate"], 6)},
        {"metric": "profit_factor", "value": metrics["profit_factor"] if metrics["profit_factor"] != float("inf") else "inf"},
        {"metric": "average_return", "value": round(metrics["average_return"], 6)},
        {"metric": "max_consecutive_loss", "value": metrics["max_consecutive_loss"]},
    ]


def run_backtest(rows: list[dict], config: dict, trades_output: str, equity_output: str) -> BacktestResult:
    defaults = config["defaults"]
    allocation_plan = defaults["allocation_plan"]
    enriched = add_indicators(rows, config["strategy"]["ma_short"], config["strategy"]["ma_mid"], config["strategy"]["ma_long"], defaults["atr_period"])
    by_symbol = group_by_symbol(enriched)
    all_dates = sorted({row["date"] for row in enriched})
    daily_rows = {date: [row for row in enriched if row["date"] == date] for date in all_dates}
    portfolio = Portfolio(cash=defaults["initial_equity"], max_positions=defaults["max_positions"])
    trades: list[dict] = []
    equity_curve: list[dict] = []
    latest_prices: dict[str, float] = {}
    trades_path = Path(trades_output)
    symbol_summary_output = str(trades_path.with_name("backtest_symbol_summary.csv"))
    portfolio_metrics_output = str(trades_path.with_name("backtest_portfolio_metrics.csv"))

    for date in all_dates:
        for row in daily_rows[date]:
            symbol = row["symbol"]
            latest_prices[symbol] = row["close"]
            history = [item for item in by_symbol[symbol] if item["date"] <= date]
            idx = len(history) - 1
            signal_name = _entry_signal_name(row, history, idx, defaults["scanner_lookback"])
            position = portfolio.positions.get(symbol)

            if position is not None:
                reason, should_exit = detect_exit_signal(history, idx, entry_price=position.avg_price, entry_low=position.entry_low)
                if reason == "warning":
                    position.warning_count += 1
                    logging.info("[%s] warning signal on %s: position held", symbol, date.strftime("%Y-%m-%d"))
                elif should_exit and reason == "reduce":
                    reduce_qty = max(1, round(position.quantity * 0.5))
                    position.reduction_count += 1
                    logging.info("[%s] reduce signal on %s: selling %s of %s shares", symbol, date.strftime("%Y-%m-%d"), reduce_qty, position.quantity)
                    _sell_quantity(position, reduce_qty, row["close"], reason, date, trades, portfolio, symbol)
                elif should_exit:
                    logging.info("[%s] exit signal %s on %s: liquidating remaining %s shares", symbol, reason, date.strftime("%Y-%m-%d"), position.quantity)
                    _sell_quantity(position, position.quantity, row["close"], reason, date, trades, portfolio, symbol)
                    position = portfolio.positions.get(symbol)

            position = portfolio.positions.get(symbol)
            if signal_name is None:
                continue
            if not portfolio.can_open_new_position(symbol):
                continue

            is_new_position = position is None
            if is_new_position:
                stop_price = row["low"] if row.get("atr") is None else max(row["low"], row["close"] - row["atr"] * defaults["atr_multiplier"])
                sizing = calculate_position_size(portfolio.equity(latest_prices), row["close"], stop_price, defaults["risk_per_trade"], allocation_plan)
                if sizing.quantity <= 0:
                    continue
                target_position = Position(symbol=symbol)
                target_position.set_tranche_plan(sizing.tranche_quantities)
            else:
                target_position = position

            tranche_index = target_position.next_tranche_index
            if tranche_index > len(allocation_plan):
                continue
            tranche_qty = target_position.planned_quantity_for(tranche_index)
            cost = row["close"] * tranche_qty
            if tranche_qty <= 0 or cost > portfolio.cash:
                continue

            if is_new_position:
                portfolio.positions[symbol] = target_position
            portfolio.cash -= cost
            target_position.add_tranche(
                PositionTranche(
                    tranche_index=tranche_index,
                    quantity=tranche_qty,
                    entry_price=row["close"],
                    entry_date=date.strftime("%Y-%m-%d"),
                    entry_low=row["low"],
                    signal_name=signal_name,
                )
            )
            trades.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "action": "BUY",
                    "price": round(row["close"], 2),
                    "quantity": tranche_qty,
                    "reason": f"entry_{signal_name}_tranche_{tranche_index}",
                    "pnl": 0.0,
                    "return_pct": 0.0,
                }
            )
        equity_curve.append({"date": date, "equity": round(portfolio.equity(latest_prices), 2), "cash": round(portfolio.cash, 2)})

    metrics = _compute_metrics(equity_curve, trades, defaults["initial_equity"])
    symbol_summary = _build_symbol_summary(trades)
    save_rows(trades, trades_output, fieldnames=["date", "symbol", "action", "price", "quantity", "reason", "pnl", "return_pct"])
    save_rows(equity_curve, equity_output, fieldnames=["date", "equity", "cash"])
    save_rows(symbol_summary, symbol_summary_output, fieldnames=["symbol", "buy_count", "sell_count", "realized_pnl", "average_return", "win_rate", "profit_factor", "closed_trades", "max_consecutive_loss"])
    save_rows(_portfolio_metrics_rows(metrics), portfolio_metrics_output, fieldnames=["metric", "value"])
    return BacktestResult(trades=trades, equity_curve=equity_curve, symbol_summary=symbol_summary, metrics=metrics)
