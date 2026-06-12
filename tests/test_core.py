"""Тесты детерминированного ядра: «двойник» (db) и рыночные инструменты.

LLM-слой здесь не трогаем (см. тест-стратегию в CLAUDE.md). Используем временную БД и
реальный prices.csv (он детерминирован и закэширован).
"""
from __future__ import annotations

import pytest

from database import db
from tools import market_tools as mt
from tools import memory_tools as mem
from tools.market_tools import price_at


@pytest.fixture
def sim_db(tmp_path):
    """Свежий «двойник» во временной БД: баланс $10k, консервативный профиль."""
    path = tmp_path / "test.sqlite"
    db.reset_simulation(10_000.0, "conservative", db_path=path)
    return path


def test_reset_creates_portfolio(sim_db):
    p = db.get_portfolio(sim_db)
    assert p.cash == 10_000.0
    assert p.day == 1
    assert p.position is None
    assert p.risk_profile == "conservative"


def test_buy_opens_position_and_spends_cash(sim_db):
    price = price_at("AAPL", 1)
    res = mt.execute_trade("BUY", "AAPL", db_path=sim_db)
    assert res["status"] == "ok"
    expected_qty = int(10_000.0 // price)
    p = db.get_portfolio(sim_db)
    assert p.position is not None
    assert p.position.ticker == "AAPL"
    assert p.position.qty == expected_qty
    assert p.cash == pytest.approx(10_000.0 - expected_qty * price)


def test_second_buy_rejected_by_one_position_rule(sim_db):
    mt.execute_trade("BUY", "AAPL", db_path=sim_db)
    res = mt.execute_trade("BUY", "MSFT", db_path=sim_db)
    assert res["status"] == "rejected"
    # Нарушение должно попасть в журнал как BUY_REJECTED (Constraint Compliance)
    rejected = [t for t in db.get_trades(sim_db) if t["action"] == "BUY_REJECTED"]
    assert len(rejected) == 1


def test_sell_realizes_pnl_and_frees_position(sim_db):
    mt.execute_trade("BUY", "AAPL", db_path=sim_db)
    # Переходим на день 5, где другая цена
    p = db.get_portfolio(sim_db)
    p.day = 5
    db.save_portfolio(p, sim_db)

    qty = db.get_portfolio(sim_db).position.qty
    buy_price = price_at("AAPL", 1)
    sell_price = price_at("AAPL", 5)
    res = mt.execute_trade("SELL", "AAPL", db_path=sim_db)

    assert res["status"] == "ok"
    assert res["pnl"] == pytest.approx(qty * (sell_price - buy_price))
    assert db.get_portfolio(sim_db).position is None


def test_sell_without_position_rejected(sim_db):
    res = mt.execute_trade("SELL", "AAPL", db_path=sim_db)
    assert res["status"] == "rejected"


def test_price_future_guard(sim_db):
    # Текущий день = 1, запрос дня 5 должен быть отклонён
    res = mt.get_current_price("AAPL", 5, db_path=sim_db)
    assert "error" in res
    ok = mt.get_current_price("AAPL", 1, db_path=sim_db)
    assert ok["price"] == price_at("AAPL", 1)


def test_insights_save_and_read(sim_db):
    mem.save_insight_to_memory("TSLA: маржа падает", ticker="TSLA", db_path=sim_db)
    mem.save_insight_to_memory("Общий вывод про рынок", db_path=sim_db)
    tsla = mem.read_memory("TSLA", db_path=sim_db)
    # По TSLA видим и тикерную заметку, и общую (ticker IS NULL)
    assert len(tsla) == 2
    aapl = mem.read_memory("AAPL", db_path=sim_db)
    assert len(aapl) == 1  # только общая


def test_equity_curve(sim_db):
    db.snapshot_equity(1, 10_000.0, 0.0, sim_db)
    db.snapshot_equity(2, 5_000.0, 5_500.0, sim_db)
    curve = db.get_equity_curve(sim_db)
    assert [c["total"] for c in curve] == [10_000.0, 10_500.0]
