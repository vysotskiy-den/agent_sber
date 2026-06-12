"""Тесты детерминированных бизнес-метрик (из БД) и парсеров лога МАС."""
from __future__ import annotations

import pytest

from core import metrics
from database import db


@pytest.fixture
def sim_db(tmp_path):
    path = tmp_path / "m.sqlite"
    db.reset_simulation(10_000.0, "conservative", db_path=path)
    return path


def test_roi(sim_db):
    db.snapshot_equity(1, 10_000.0, 0.0, sim_db)
    db.snapshot_equity(2, 11_000.0, 0.0, sim_db)
    assert metrics.roi(sim_db) == pytest.approx(10.0)


def test_win_rate(sim_db):
    db.record_trade(2, "AAPL", "SELL", 1, 110, 110, pnl=10, db_path=sim_db)
    db.record_trade(4, "MSFT", "SELL", 1, 90, 200, pnl=-10, db_path=sim_db)
    db.record_trade(6, "TSLA", "SELL", 1, 120, 320, pnl=5, db_path=sim_db)
    assert metrics.win_rate(sim_db) == pytest.approx(2 / 3 * 100)


def test_win_rate_none_when_no_closed_trades(sim_db):
    assert metrics.win_rate(sim_db) is None


def test_max_drawdown(sim_db):
    for day, total in enumerate([10_000, 12_000, 9_000, 11_000], start=1):
        db.snapshot_equity(day, total, 0.0, sim_db)
    # Пик 12000 -> впадина 9000 => просадка 25%
    assert metrics.max_drawdown(sim_db) == pytest.approx(25.0)


def test_constraint_violations(sim_db):
    db.record_trade(1, "AAPL", "BUY", 10, 100, 0, db_path=sim_db)
    db.record_trade(2, "MSFT", "BUY_REJECTED", 0, 0, 0, db_path=sim_db)
    assert metrics.constraint_violations(sim_db) == 1


def test_tool_accuracy_and_coherence_from_log():
    days_log = [
        {"day": 1, "log": [
            "🔧 ask_news_agent({'ticker': 'AAPL'})",
            "↩️ sentiment=+0.70, signal=buy. ...",
            "🔧 execute_trade({'action': 'BUY', 'ticker': 'AAPL'})",
            "↩️ OK",
        ]},
        {"day": 2, "log": [
            "🔧 ask_news_agent({'ticker': 'AAPL'})",
            "↩️ sentiment=-0.90, signal=sell. ...",
            "🔧 execute_trade({'action': 'BUY', 'ticker': 'AAPL'})",  # рассогласовано
            "↩️ OK",
        ]},
        {"day": 3, "log": ["⚠️ Ошибка дня (пропуск, HOLD): timed out"]},
    ]
    # 4 успешных вызова инструментов, 1 ошибка дня -> 80%
    assert metrics.tool_accuracy(days_log) == pytest.approx(80.0)
    # 2 сделки, 1 согласована с сигналом -> 50%
    assert metrics.coherence_score(days_log) == pytest.approx(50.0)
