"""«Цифровой двойник» портфеля и долгосрочная память агента (SQLite).

Это внешняя по отношению к LLM долгосрочная память (критерий Memory, уровень 2):
агент сам решает, когда писать заметки (`add_insight`), а состояние портфеля
обновляется детерминированно после каждой сделки.

Таблицы:
  * portfolio      — единственная строка, текущий снимок «двойника»
  * trades         — журнал сделок (для бизнес-метрик: ROI, Win Rate)
  * insights       — заметки агента (Agentic Memory)
  * equity_curve   — стоимость портфеля по дням (для ROI и Max Drawdown)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from core import config
from core.state import PortfolioState, Position


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Создаёт схему, если её ещё нет."""
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                initial_balance REAL NOT NULL,
                cash            REAL NOT NULL,
                day             INTEGER NOT NULL,
                risk_profile    TEXT NOT NULL,
                pos_ticker      TEXT,
                pos_qty         INTEGER,
                pos_buy_price   REAL,
                pos_buy_day     INTEGER,
                prompt_addon    TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS trades (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                day        INTEGER NOT NULL,
                ticker     TEXT NOT NULL,
                action     TEXT NOT NULL,
                qty        INTEGER NOT NULL,
                price      REAL NOT NULL,
                cash_after REAL NOT NULL,
                pnl        REAL
            );
            CREATE TABLE IF NOT EXISTS insights (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                day        INTEGER NOT NULL,
                ticker     TEXT,
                text       TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS equity_curve (
                day   INTEGER PRIMARY KEY,
                cash  REAL NOT NULL,
                position_value REAL NOT NULL,
                total REAL NOT NULL
            );
            """
        )


def reset_simulation(
    initial_balance: float,
    risk_profile: str,
    db_path: Path | None = None,
) -> None:
    """Сбрасывает все таблицы и создаёт свежий «двойник» для нового прогона."""
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.executescript(
            "DELETE FROM portfolio; DELETE FROM trades; "
            "DELETE FROM insights; DELETE FROM equity_curve;"
        )
        conn.execute(
            "INSERT INTO portfolio (id, initial_balance, cash, day, risk_profile) "
            "VALUES (1, ?, ?, 1, ?)",
            (initial_balance, initial_balance, risk_profile),
        )


def get_portfolio(db_path: Path | None = None) -> PortfolioState:
    """Возвращает текущий снимок «двойника» как PortfolioState."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM portfolio WHERE id = 1").fetchone()
    if row is None:
        raise RuntimeError("Портфель не инициализирован — вызовите reset_simulation()")
    position = None
    if row["pos_ticker"] is not None:
        position = Position(
            ticker=row["pos_ticker"],
            qty=row["pos_qty"],
            buy_price=row["pos_buy_price"],
            buy_day=row["pos_buy_day"],
        )
    return PortfolioState(
        initial_balance=row["initial_balance"],
        cash=row["cash"],
        day=row["day"],
        risk_profile=row["risk_profile"],
        position=position,
        prompt_addon=row["prompt_addon"],
    )


def save_portfolio(state: PortfolioState, db_path: Path | None = None) -> None:
    """Записывает снимок «двойника» обратно в БД."""
    pos = state.position
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE portfolio SET
                initial_balance = ?, cash = ?, day = ?, risk_profile = ?,
                pos_ticker = ?, pos_qty = ?, pos_buy_price = ?, pos_buy_day = ?,
                prompt_addon = ?
            WHERE id = 1
            """,
            (
                state.initial_balance, state.cash, state.day, state.risk_profile,
                pos.ticker if pos else None,
                pos.qty if pos else None,
                pos.buy_price if pos else None,
                pos.buy_day if pos else None,
                state.prompt_addon,
            ),
        )


def record_trade(
    day: int, ticker: str, action: str, qty: int, price: float,
    cash_after: float, pnl: float | None = None, db_path: Path | None = None,
) -> None:
    """Добавляет запись в журнал сделок (для бизнес-метрик)."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO trades (day, ticker, action, qty, price, cash_after, pnl) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (day, ticker, action, qty, price, cash_after, pnl),
        )


def get_trades(db_path: Path | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def add_insight(
    day: int, text: str, ticker: str | None = None, db_path: Path | None = None
) -> None:
    """Сохраняет заметку агента в долгосрочную память (Agentic Memory)."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO insights (day, ticker, text) VALUES (?, ?, ?)",
            (day, ticker, text),
        )


def get_insights(
    ticker: str | None = None, db_path: Path | None = None
) -> list[dict]:
    """Читает заметки агента; при указании тикера — только по нему (+ общие)."""
    with _connect(db_path) as conn:
        if ticker is None:
            rows = conn.execute("SELECT * FROM insights ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM insights WHERE ticker = ? OR ticker IS NULL ORDER BY id",
                (ticker,),
            ).fetchall()
    return [dict(r) for r in rows]


def snapshot_equity(
    day: int, cash: float, position_value: float, db_path: Path | None = None
) -> None:
    """Фиксирует стоимость портфеля на конец дня (для ROI и Max Drawdown)."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO equity_curve (day, cash, position_value, total) "
            "VALUES (?, ?, ?, ?)",
            (day, cash, position_value, cash + position_value),
        )


def get_equity_curve(db_path: Path | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM equity_curve ORDER BY day").fetchall()
    return [dict(r) for r in rows]
