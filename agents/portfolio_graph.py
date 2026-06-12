"""Управляющий портфелем (Portfolio Manager) и цикл 10-дневной симуляции.

Оркестратор — ReAct-агент, который делегирует задачи узким агентам (Action: вызов
других агентов), читает/пишет внешнюю память (Memory), меняет план по ходу (Reasoning),
проверяет себя перед сделкой (Reflection) и работает автономно весь цикл (Autonomy).
Роль управляющего динамически ужесточается при просадке (Role уровень 2).
"""
from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from agents import fundamental_agent, news_agent
from agents.prompts import portfolio_manager_prompt
from core import config
from core.llm import get_chat
from database import db
from tools import market_tools, memory_tools


# --- Инструменты управляющего (берут текущий день симуляции из «двойника») ---

@tool
def ask_news_agent(ticker: str) -> str:
    """Запросить у новостника сентимент по компании за текущий день."""
    day = db.get_portfolio().day
    s = news_agent.analyze(ticker, day)
    return f"sentiment={s.sentiment_score:+.2f}, signal={s.signal}. {s.summary}"


@tool
def ask_fundamental_agent(ticker: str) -> str:
    """Запросить у фундаменталиста долгосрочную оценку компании (RAG)."""
    return fundamental_agent.analyze(ticker)


@tool
def get_current_price(ticker: str) -> str:
    """Узнать цену акции на текущий день симуляции."""
    res = market_tools.get_current_price(ticker, db.get_portfolio().day)
    return res.get("error") or f"{ticker}: ${res['price']:.2f} (день {res['day']})"


@tool
def read_memory(ticker: str) -> str:
    """Прочитать свои прежние заметки по компании (и общие)."""
    notes = memory_tools.read_memory(ticker)
    if not notes:
        return "Заметок нет."
    return "\n".join(f"[день {n['day']}] {n['text']}" for n in notes)


@tool
def save_insight_to_memory(text: str, ticker: str = "") -> str:
    """Сохранить важный долгосрочный вывод в память, чтобы вернуться к нему позже."""
    memory_tools.save_insight_to_memory(text, ticker or None)
    return "Сохранено."


@tool
def execute_trade(action: str, ticker: str) -> str:
    """Совершить сделку: action ∈ {BUY, SELL, HOLD}."""
    res = market_tools.execute_trade(action, ticker)
    if res["status"] == "rejected":
        return f"ОТКЛОНЕНО: {res['reason']}"
    return f"OK: {res}"


PM_TOOLS = [
    ask_news_agent, ask_fundamental_agent, get_current_price,
    read_memory, save_insight_to_memory, execute_trade,
]


def _build_agent(risk_profile: str, prompt_addon: str):
    return create_agent(
        get_chat(),
        tools=PM_TOOLS,
        system_prompt=portfolio_manager_prompt(risk_profile, prompt_addon),
    )


def _state_message(state) -> str:
    pos = (
        f"{state.position.ticker} × {state.position.qty} @ ${state.position.buy_price:.2f}"
        if state.position else "нет открытой позиции"
    )
    return (
        f"ДЕНЬ {state.day} из {config.SIMULATION_DAYS}.\n"
        f"Кэш: ${state.cash:.2f}. Открытая позиция: {pos}.\n"
        f"Доступные компании: {', '.join(config.TICKERS)}.\n"
        f"Прими торговое решение на сегодня по своему алгоритму (включая Reflection)."
    )


def _extract_log(messages) -> list[str]:
    """Достаёт читаемую цепочку рассуждений и действий из сообщений агента."""
    log: list[str] = []
    for m in messages:
        kind = type(m).__name__
        if kind == "AIMessage":
            if m.content:
                log.append(f"🧠 {m.content}")
            for tc in getattr(m, "tool_calls", []) or []:
                log.append(f"🔧 {tc['name']}({tc['args']})")
        elif kind == "ToolMessage":
            log.append(f"↩️ {m.content}")
    return log


def _apply_drawdown_guard(state) -> None:
    """Role уровень 2: при просадке от пика управляющий сам ужесточает свой промпт.

    «Просадка» = падение текущей стоимости портфеля относительно достигнутого пика
    (стандартная трактовка drawdown), а не относительно стартового баланса.
    """
    total = state.total_value(_safe_price(state))
    totals = [c["total"] for c in db.get_equity_curve()] + [total]
    peak = max(state.initial_balance, *totals)
    drawdown_pct = (peak - total) / peak * 100
    if drawdown_pct >= config.DRAWDOWN_GUARD_PCT and not state.prompt_addon:
        state.prompt_addon = (
            f"Портфель в просадке {drawdown_pct:.1f}% от пика. Действуй максимально "
            "осторожно, приоритет — сохранение капитала, избегай рискованных покупок."
        )
        db.save_portfolio(state)


def _safe_price(state):
    if state.position is None:
        return None
    try:
        return market_tools.price_at(state.position.ticker, state.day)
    except KeyError:
        return state.position.buy_price


def run_simulation(
    initial_balance: float = config.DEFAULT_INITIAL_BALANCE,
    risk_profile: str = config.DEFAULT_RISK_PROFILE,
):
    """Прогоняет автономную 10-дневную симуляцию. Возвращает лог по дням.

    Генератор: на каждый день отдаёт {day, log, state} — удобно для стриминга в UI.
    """
    db.reset_simulation(initial_balance, risk_profile)
    for day in range(1, config.SIMULATION_DAYS + 1):
        state = db.get_portfolio()
        state.day = day
        db.save_portfolio(state)
        _apply_drawdown_guard(state)
        state = db.get_portfolio()

        agent = _build_agent(state.risk_profile, state.prompt_addon)
        try:
            result = agent.invoke({"messages": [HumanMessage(_state_message(state))]})
            log = _extract_log(result["messages"])
        except Exception as exc:  # устойчивость демо: день не должен ронять прогон
            log = [f"⚠️ Ошибка дня (пропуск, HOLD): {exc}"]

        # Конец дня: фиксируем стоимость портфеля для метрик.
        end = db.get_portfolio()
        price = _safe_price(end)
        db.snapshot_equity(day, end.cash, end.market_value(price))

        yield {"day": day, "log": log, "state": db.get_portfolio()}
