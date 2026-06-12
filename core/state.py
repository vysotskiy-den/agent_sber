"""Модель состояния портфеля («Цифровой двойник»).

Чистые структуры данных без побочных эффектов: их сериализует `database/db.py`,
читают инструменты и считают метрики. LangGraph-состояние графа (с messages/логами)
появится отдельно на слое агентов — здесь только бизнес-состояние портфеля.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    """Открытая позиция. По правилу симуляции она в портфеле максимум одна."""

    ticker: str
    qty: int
    buy_price: float
    buy_day: int

    @property
    def cost(self) -> float:
        return self.qty * self.buy_price


@dataclass
class PortfolioState:
    """Снимок «Цифрового двойника» портфеля на текущий день симуляции."""

    initial_balance: float
    cash: float
    day: int
    risk_profile: str
    position: Position | None = None
    # Динамическая добавка к system_prompt Управляющего (критерий Role, уровень 2).
    prompt_addon: str = ""

    def market_value(self, current_price: float | None) -> float:
        """Стоимость открытой позиции по текущей цене (0, если позиции нет)."""
        if self.position is None or current_price is None:
            return 0.0
        return self.position.qty * current_price

    def total_value(self, current_price: float | None) -> float:
        """Полная стоимость портфеля = кэш + рыночная стоимость позиции."""
        return self.cash + self.market_value(current_price)
