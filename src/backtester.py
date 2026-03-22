from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

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
                "avg_return": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "closed_trades": 0,
            },
        )
        if trade["action"] == "BUY":
            bucket["buy_count"] += 1
        elif trade["action"] == "SELL":
            bucket["sell_count"] += 1
            bucket["realized_pnl"] += trade["pnl"]
            bucket["closed_trades"] += 1

    for symbol, bucket in summary.items():
        closed = [trade for trade in trades if trade["symbol"] == symbol and trade["action"] == "SELL"]
        wins = [trade for trade in closed if trade["pnl"] > 0]
        losses = [trade for trade in closed if trade["pnl"] < 0]
        returns = [trade.get("return_pct", 0.0) for trade in closed]
        bucket["avg_return"] = round(sum(returns) / len(returns), 4) if returns else 0.0
        bucket["win_rate"] = round(len(wins) / len(closed), 4) if closed else 0.0
        gross_profit = sum(trade["pnl"] for trade in wins)
        gross_loss = abs(sum(trade["pnl"] for trade in losses))
        bucket["profit_factor"] = round(gross_profit / gross_loss, 4) if gross_loss > 0 else ("inf" if gross_profit > 0 else 0.0)
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
    wins = [trade for trade in closed if trade["pnl"] > 0]
    losses = [trade for trade in closed if trade["pnl"] < 0]
    win_rate = len(wins) / len(closed) if closed else 0.0
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    average_return = sum(trade.get("return_pct", 0.0) for trade in closed) / len(closed) if closed else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    return {
        "cagr": cagr,
        "mdd": mdd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_return": average_return,
        "max_consecutive_loss": _compute_max_consecutive_losses(closed),
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



def run_backtest(rows: list[dict], config: dict, trades_output: str, equity_output: str) -> BacktestResult:
    defaults = config["defaults"]
    enriched = add_indicators(rows, config["strategy"]["ma_short"], config["strategy"]["ma_mid"], config["strategy"]["ma_long"], defaults["atr_period"])
    by_symbol = group_by_symbol(enriched)
    all_dates = sorted({row["date"] for row in enriched})
    daily_rows = {date: [row for row in enriched if row["date"] == date] for date in all_dates}
    portfolio = Portfolio(cash=defaults["initial_equity"], max_positions=defaults["max_positions"])
    trades: list[dict] = []
    equity_curve: list[dict] = []
    latest_prices: dict[str, float] = {}
    symbol_summary_output = str(Path(trades_output).with_name("backtest_symbol_summary.csv"))

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
                elif should_exit and reason == "reduce" and position.quantity > 1:
                    reduce_qty = max(1, position.quantity // 2)
                    position.reduction_count += 1
                    _sell_quantity(position, reduce_qty, row["close"], reason, date, trades, portfolio, symbol)
                elif should_exit:
                    _sell_quantity(position, position.quantity, row["close"], reason, date, trades, portfolio, symbol)
                    position = portfolio.positions.get(symbol)

            position = portfolio.positions.get(symbol)
            if signal_name is None:
                continue
            if not portfolio.can_open_new_position(symbol):
                continue

            stop_price = row["low"] if row.get("atr") is None else max(row["low"], row["close"] - row["atr"] * defaults["atr_multiplier"])
            sizing = calculate_position_size(portfolio.equity(latest_prices), row["close"], stop_price, defaults["risk_per_trade"], defaults["allocation_plan"])
            target_position = position if position is not None else Position(symbol=symbol)
            tranche_index = target_position.next_tranche_index
            if tranche_index > len(defaults["allocation_plan"]):
                continue
            tranche_qty = sizing.tranche_quantities[tranche_index - 1]
            cost = row["close"] * tranche_qty
            if tranche_qty <= 0 or cost > portfolio.cash:
                continue
            if position is None:
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
    save_rows(symbol_summary, symbol_summary_output, fieldnames=["symbol", "buy_count", "sell_count", "realized_pnl", "avg_return", "win_rate", "profit_factor", "closed_trades"])
    return BacktestResult(trades=trades, equity_curve=equity_curve, symbol_summary=symbol_summary, metrics=metrics)
