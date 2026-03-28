from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OrderResult:
    symbol: str
    side: str
    quantity: int
    price: float
    fee: float
    status: str
    message: str = ""
    order_id: str = ""


class BrokerBase(ABC):
    @abstractmethod
    def buy(self, symbol: str, quantity: int, price: float) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def sell(self, symbol: str, quantity: int, price: float) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_average_price(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_cash(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> dict[str, int]:
        raise NotImplementedError
