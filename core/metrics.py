"""Метрики качества (критерий 3).

Делятся на две группы:
  * Бизнес-метрики портфеля — детерминированы, считаются из «двойника» (БД): ROI,
    Win Rate, Max Drawdown, Constraint Compliance.
  * Метрики МАС — оцениваются по логу прогона: Tool Accuracy, Coherence Score.
"""
from __future__ import annotations

import re
from pathlib import Path

from database import db


# --- Бизнес-метрики (детерминированы, из БД) ---

def roi(db_path: Path | None = None) -> float:
    """Доходность портфеля за весь период, % ((итог - старт) / старт)."""
    curve = db.get_equity_curve(db_path)
    portfolio = db.get_portfolio(db_path)
    if not curve:
        return 0.0
    return (curve[-1]["total"] - portfolio.initial_balance) / portfolio.initial_balance * 100


def win_rate(db_path: Path | None = None) -> float | None:
    """Доля прибыльных закрытых сделок (SELL с pnl) среди всех закрытых, %."""
    closed = [t for t in db.get_trades(db_path) if t["action"] == "SELL"]
    if not closed:
        return None
    wins = sum(1 for t in closed if (t["pnl"] or 0) > 0)
    return wins / len(closed) * 100


def max_drawdown(db_path: Path | None = None) -> float:
    """Максимальная просадка стоимости портфеля от пика, %."""
    totals = [c["total"] for c in db.get_equity_curve(db_path)]
    if not totals:
        return 0.0
    peak = totals[0]
    mdd = 0.0
    for total in totals:
        peak = max(peak, total)
        mdd = max(mdd, (peak - total) / peak * 100)
    return mdd


def constraint_violations(db_path: Path | None = None) -> int:
    """Число нарушений правила «≤1 позиция» (отклонённые покупки). Цель — 0."""
    return sum(1 for t in db.get_trades(db_path) if t["action"] == "BUY_REJECTED")


# --- Метрики МАС (по логу прогона) ---

def tool_accuracy(days_log: list[dict]) -> float | None:
    """Доля успешных вызовов инструментов (без ошибок исполнения), %.

    Отклонённые сделки по правилам (ОТКЛОНЕНО) — это валидный ответ инструмента, а не
    сбой; сбоем считаем технические ошибки дня (⚠️).
    """
    calls = errors = 0
    for rec in days_log:
        for line in rec["log"]:
            if line.startswith("🔧"):
                calls += 1
            if line.startswith("⚠️"):
                errors += 1
    attempts = calls + errors
    if attempts == 0:
        return None
    return calls / attempts * 100


def coherence_score(days_log: list[dict]) -> float | None:
    """Согласованность сделок с сигналом новостей, %.

    Для каждого дня, где была сделка BUY/SELL, сверяем её с последним виденным
    сигналом новостника: BUY должен следовать за signal=buy, SELL — за sell.
    """
    aligned = total = 0
    sig_re = re.compile(r"signal=(\w+)")
    trade_re = re.compile(r"execute_trade\(\{'action': '(\w+)'")
    for rec in days_log:
        last_signal = None
        for line in rec["log"]:
            m = sig_re.search(line)
            if m:
                last_signal = m.group(1).lower()
            t = trade_re.search(line)
            if t:
                action = t.group(1).upper()
                if action in ("BUY", "SELL"):
                    total += 1
                    if (action == "BUY" and last_signal == "buy") or (
                        action == "SELL" and last_signal == "sell"
                    ):
                        aligned += 1
    if total == 0:
        return None
    return aligned / total * 100


def summary(days_log: list[dict], db_path: Path | None = None) -> dict:
    """Сводка всех метрик для отчёта/UI."""
    return {
        "ROI_%": round(roi(db_path), 2),
        "Win_Rate_%": win_rate(db_path),
        "Max_Drawdown_%": round(max_drawdown(db_path), 2),
        "Constraint_Violations": constraint_violations(db_path),
        "Tool_Accuracy_%": tool_accuracy(days_log),
        "Coherence_%": coherence_score(days_log),
    }
