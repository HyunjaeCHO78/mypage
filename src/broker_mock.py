from __future__ import annotations

from src.broker_base import BrokerBase, OrderResult


class MockBroker(BrokerBase):
    def __init__(self, starting_cash: float, slippage_bps: float = 0.0, fee_bps: float = 0.0) -> None:
        self.cash = starting_cash
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.positions: dict[str, int] = {}
        self.position_costs: dict[str, float] = {}
        self.order_seq = 0
        self.orders: dict[str, OrderResult] = {}

    def _next_order_id(self) -> str:
        self.order_seq += 1
        return f"MOCK-{self.order_seq:06d}"

    def _apply_execution_price(self, price: float, side: str) -> float:
        adjustment = price * (self.slippage_bps / 10000)
        return price + adjustment if side == "buy" else price - adjustment

    def _fee(self, gross_amount: float) -> float:
        return gross_amount * (self.fee_bps / 10000)

    def buy(self, symbol: str, quantity: int, price: float) -> OrderResult:
        order_id = self._next_order_id()
        exec_price = self._apply_execution_price(price, "buy")
        gross = exec_price * quantity
        fee = self._fee(gross)
        total = gross + fee
        if quantity <= 0:
            result = OrderResult(symbol, "buy", quantity, exec_price, fee, "rejected", "quantity must be positive", order_id)
        elif total > self.cash:
            result = OrderResult(symbol, "buy", quantity, exec_price, fee, "rejected", "insufficient cash", order_id)
        else:
            current_quantity = self.positions.get(symbol, 0)
            self.cash -= total
            self.positions[symbol] = current_quantity + quantity
            self.position_costs[symbol] = self.position_costs.get(symbol, 0.0) + gross + fee
            result = OrderResult(symbol, "buy", quantity, exec_price, fee, "filled", order_id=order_id)
        self.orders[order_id] = result
        return result

    def sell(self, symbol: str, quantity: int, price: float) -> OrderResult:
        order_id = self._next_order_id()
        current_quantity = self.positions.get(symbol, 0)
        exec_price = self._apply_execution_price(price, "sell")
        gross = exec_price * quantity
        fee = self._fee(gross)
        if quantity <= 0:
            result = OrderResult(symbol, "sell", quantity, exec_price, fee, "rejected", "quantity must be positive", order_id)
        elif quantity > current_quantity:
            result = OrderResult(symbol, "sell", quantity, exec_price, fee, "rejected", "insufficient holdings", order_id)
        else:
            average_price = self.get_average_price(symbol)
            self.cash += gross - fee
            remaining = current_quantity - quantity
            if remaining == 0:
                self.positions.pop(symbol, None)
                self.position_costs.pop(symbol, None)
            else:
                self.positions[symbol] = remaining
                self.position_costs[symbol] = average_price * remaining
            result = OrderResult(symbol, "sell", quantity, exec_price, fee, "filled", order_id=order_id)
        self.orders[order_id] = result
        return result

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order is None or order.status == "filled":
            return False
        order.status = "cancelled"
        return True

    def get_order_status(self, order_id: str) -> str:
        order = self.orders.get(order_id)
        return order.status if order is not None else "unknown"

    def get_average_price(self, symbol: str) -> float:
        quantity = self.positions.get(symbol, 0)
        if quantity <= 0:
            return 0.0
        return self.position_costs.get(symbol, 0.0) / quantity

    def get_cash(self) -> float:
        return self.cash

    def get_positions(self) -> dict[str, int]:
        return dict(self.positions)
