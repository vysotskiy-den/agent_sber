"""Инструменты долгосрочной памяти агента (Agentic Memory).

Тонкая обёртка над «двойником» (`database/db.py`): агент сам решает, когда сохранить
вывод (`save_insight_to_memory`) и когда его прочитать (`read_memory`). Это и есть
критерий Memory уровня 2 — внешняя долгосрочная память с самостоятельным решением.
"""
from __future__ import annotations

from pathlib import Path

from database import db


def save_insight_to_memory(
    text: str, ticker: str | None = None, db_path: Path | None = None
) -> dict:
    """Сохранить текстовый вывод в долгосрочную память, чтобы вернуться к нему позже."""
    day = db.get_portfolio(db_path).day
    db.add_insight(day, text, ticker, db_path)
    return {"status": "ok", "saved": text, "ticker": ticker, "day": day}


def read_memory(ticker: str | None = None, db_path: Path | None = None) -> list[dict]:
    """Прочитать ранее сохранённые заметки (все или по тикеру + общие)."""
    return db.get_insights(ticker, db_path)
