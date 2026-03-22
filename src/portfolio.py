from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PositionTranche:
    tranche_index: int
    quantity: int
    entry_price: float
    entry_date: str
    entry_low: float
    signal_name: str


@dataclass
class Position:
    symbol: str
    tranches: list[PositionTranche] = field(default_factory=list)
    reduction_count: int = 0
    warning_count: int = 0

    @property
    def quantity(self) -> int:
        return sum(tranche.quantity for tranche in self.tranches)

    @property
    def avg_price(self) -> float:
        total_quantity = self.quantity
        if total_quantity == 0:
            return 0.0
        total_cost = sum(tranche.quantity * tranche.entry_price for tranche in self.tranches)
        return total_cost / total_quantity

    @property
    def entry_low(self) -> float:
        if not self.tranches:
            return 0.0
        return min(tranche.entry_low for tranche in self.tranches)

    @property
    def next_tranche_index(self) -> int:
        return len(self.tranches) + 1

    def add_tranche(self, tranche: PositionTranche) -> None:
        self.tranches.append(tranche)

    def trim(self, quantity_to_reduce: int) -> list[PositionTranche]:
        remaining = quantity_to_reduce
        removed: list[PositionTranche] = []
        while remaining > 0 and self.tranches:
            tranche = self.tranches[-1]
            removable = min(remaining, tranche.quantity)
            removed.append(
                PositionTranche(
                    tranche_index=tranche.tranche_index,
                    quantity=removable,
                    entry_price=tranche.entry_price,
                    entry_date=tranche.entry_date,
                    entry_low=tranche.entry_low,
                    signal_name=tranche.signal_name,
                )
            )
            tranche.quantity -= removable
            remaining -= removable
            if tranche.quantity == 0:
                self.tranches.pop()
        return removed


@dataclass
class Portfolio:
    cash: float
    max_positions: int
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0

    def can_open_new_position(self, symbol: str) -> bool:
        return symbol in self.positions or len(self.positions) < self.max_positions

    def total_market_value(self, latest_prices: dict[str, float]) -> float:
        return sum(position.quantity * latest_prices.get(symbol, position.avg_price) for symbol, position in self.positions.items())

    def equity(self, latest_prices: dict[str, float]) -> float:
        return self.cash + self.total_market_value(latest_prices)
