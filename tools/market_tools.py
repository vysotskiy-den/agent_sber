"""Рыночные инструменты: цены и исполнение сделок.

Чистые функции (без LLM), их оборачивает слой агентов в LangChain-инструменты.
Два ключевых решения реализованы здесь:
  * защита от «заглядывания в будущее» — цену можно узнать только за день <= текущего
    дня симуляции (критерий 5, проблема галлюцинации цен);
  * правило «не более 1 открытой позиции» — нарушающие сделки отклоняются и
    логируются как BUY_REJECTED (метрика Constraint Compliance).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from core import config
from database import db


@lru_cache(maxsize=1)
def _price_table() -> dict[tuple[str, int], float]:
    """Загружает prices.csv в словарь {(ticker, day): close}. Кэшируется."""
    df = pd.read_csv(config.PRICES_CSV)
    return {(r.ticker, int(r.day)): float(r.close) for r in df.itertuples()}


def price_at(ticker: str, day: int) -> float:
    """Цена закрытия тикера за конкретный торговый день (без проверок доступа)."""
    try:
        return _price_table()[(ticker, day)]
    except KeyError as exc:
        raise KeyError(f"Нет цены для {ticker} за день {day}") from exc


def get_current_price(ticker: str, day: int, db_path: Path | None = None) -> dict:
    """Узнать цену акции на день симуляции.

    Защита от галлюцинаций: запрашиваемый день не может быть больше текущего дня
    «двойника» — агент не видит будущее.
    """
    current_day = db.get_portfolio(db_path).day
    if day > current_day:
        return {
            "error": f"День {day} ещё не наступил (текущий день: {current_day}). "
            "Цены будущего недоступны."
        }
    return {"ticker": ticker, "day": day, "price": price_at(ticker, day)}


def execute_trade(action: str, ticker: str, db_path: Path | None = None) -> dict:
    """Совершить сделку (BUY/SELL/HOLD) по текущему дню симуляции.

    BUY  — покупает максимум целых акций на доступный кэш; запрещён при уже открытой
           позиции (правило ≤1 позиции).
    SELL — продаёт всю позицию по тикеру, фиксирует PnL.
    HOLD — ничего не делает.
    Состояние «двойника» обновляется детерминированно после сделки.
    """
    action = action.upper()
    state = db.get_portfolio(db_path)
    day = state.day

    if action == "HOLD":
        return {"status": "ok", "action": "HOLD", "cash": state.cash}

    if action == "BUY":
        if state.position is not None:
            # Нарушение правила ≤1 позиции — отклоняем и логируем (Constraint Compliance).
            db.record_trade(day, ticker, "BUY_REJECTED", 0, 0.0, state.cash, db_path=db_path)
            return {
                "status": "rejected",
                "reason": f"Уже открыта позиция по {state.position.ticker}. "
                "Правило: не более 1 акции в портфеле. Сначала продайте текущую.",
            }
        price = price_at(ticker, day)
        qty = int(state.cash // price)
        if qty < 1:
            return {"status": "rejected", "reason": "Недостаточно средств для покупки."}
        state.cash -= qty * price
        from core.state import Position
        state.position = Position(ticker=ticker, qty=qty, buy_price=price, buy_day=day)
        db.save_portfolio(state, db_path)
        db.record_trade(day, ticker, "BUY", qty, price, state.cash, db_path=db_path)
        return {"status": "ok", "action": "BUY", "ticker": ticker, "qty": qty,
                "price": price, "cash": state.cash}

    if action == "SELL":
        if state.position is None:
            return {"status": "rejected", "reason": "Нет открытой позиции для продажи."}
        if state.position.ticker != ticker:
            return {"status": "rejected",
                    "reason": f"Открыта позиция по {state.position.ticker}, не по {ticker}."}
        price = price_at(ticker, day)
        qty = state.position.qty
        proceeds = qty * price
        pnl = proceeds - state.position.cost
        state.cash += proceeds
        state.position = None
        db.save_portfolio(state, db_path)
        db.record_trade(day, ticker, "SELL", qty, price, state.cash, pnl, db_path=db_path)
        return {"status": "ok", "action": "SELL", "ticker": ticker, "qty": qty,
                "price": price, "pnl": pnl, "cash": state.cash}

    return {"status": "rejected", "reason": f"Неизвестное действие: {action}"}
