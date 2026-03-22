from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass
class PositionSizingResult:
    quantity: int
    risk_amount: float
    tranche_quantities: list[int]



def calculate_position_size(
    equity: float,
    entry_price: float,
    stop_price: float,
    risk_per_trade: float,
    allocation_plan: list[float],
) -> PositionSizingResult:
    if entry_price <= 0 or stop_price <= 0:
        return PositionSizingResult(quantity=0, risk_amount=0.0, tranche_quantities=[0, 0, 0])

    per_share_risk = max(entry_price - stop_price, 0)
    if per_share_risk == 0:
        return PositionSizingResult(quantity=0, risk_amount=0.0, tranche_quantities=[0, 0, 0])

    risk_amount = equity * risk_per_trade
    total_quantity = floor(risk_amount / per_share_risk)
    tranche_quantities = [floor(total_quantity * allocation) for allocation in allocation_plan]
    assigned = sum(tranche_quantities)
    if assigned < total_quantity:
        tranche_quantities[-1] += total_quantity - assigned
    return PositionSizingResult(quantity=total_quantity, risk_amount=risk_amount, tranche_quantities=tranche_quantities)
