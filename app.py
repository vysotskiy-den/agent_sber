"""Streamlit UI: запуск и визуализация 10-дневной торговой симуляции МАС.

Слева — параметры (компании, баланс, риск-профиль) и кнопка старта. В центре — графики
стоимости портфеля и цен с точками входа/выхода, потоковый лог рассуждений агентов и
итоговые метрики. Перед запуском пользователь задаёт настройки, дальше агент работает
автономно (критерий Autonomy) — пользователь только наблюдает.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config, metrics
from database import db

st.set_page_config(page_title="Agent Sber — Торговая МАС", layout="wide")
st.title("💼 Мультиагентная торговая система")
st.caption("Portfolio Manager + News Analyst + Fundamental Analyst · GigaChat · 10 дней симуляции")


# --- Левая панель: параметры (критерий Autonomy — задаём ДО старта) ---
with st.sidebar:
    st.header("Параметры симуляции")
    tickers = st.multiselect("Компании", config.TICKERS, default=config.TICKERS)
    balance = st.number_input("Начальный баланс, $", 1000, 1_000_000,
                              int(config.DEFAULT_INITIAL_BALANCE), step=1000)
    risk = st.radio("Риск-профиль", config.RISK_PROFILES,
                    format_func=lambda r: {"conservative": "Консервативный",
                                           "aggressive": "Агрессивный"}[r])
    start = st.button("🚀 Начать симуляцию", type="primary", use_container_width=True)


def _prices_df() -> pd.DataFrame:
    return pd.read_csv(config.PRICES_CSV)


def _equity_chart() -> go.Figure:
    """График стоимости портфеля по дням."""
    curve = db.get_equity_curve()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[c["day"] for c in curve], y=[c["total"] for c in curve],
        mode="lines+markers", name="Стоимость портфеля", line=dict(width=3),
    ))
    fig.add_hline(y=balance, line_dash="dash", line_color="gray",
                  annotation_text="Старт")
    fig.update_layout(title="Стоимость портфеля", xaxis_title="День",
                      yaxis_title="$", height=350)
    return fig


def _price_trades_chart(selected: list[str]) -> go.Figure:
    """Цены выбранных компаний с зелёными (Buy) и красными (Sell) точками."""
    prices = _prices_df()
    fig = go.Figure()
    for t in selected:
        sub = prices[prices.ticker == t]
        fig.add_trace(go.Scatter(x=sub.day, y=sub.close, mode="lines", name=t))

    trades = db.get_trades()
    for action, color, symbol, label in [
        ("BUY", "green", "triangle-up", "Buy"),
        ("SELL", "red", "triangle-down", "Sell"),
    ]:
        pts = [t for t in trades if t["action"] == action]
        if pts:
            fig.add_trace(go.Scatter(
                x=[t["day"] for t in pts], y=[t["price"] for t in pts],
                mode="markers", name=label,
                marker=dict(color=color, size=14, symbol=symbol),
            ))
    fig.update_layout(title="Цены и сделки", xaxis_title="День",
                      yaxis_title="$", height=350)
    return fig


def _show_results(days_log: list[dict], selected: list[str]) -> None:
    m = metrics.summary(days_log)
    c1, c2, c3 = st.columns(3)
    c1.metric("ROI", f"{m['ROI_%']}%")
    c2.metric("Win Rate", "—" if m["Win_Rate_%"] is None else f"{m['Win_Rate_%']:.0f}%")
    c3.metric("Max Drawdown", f"{m['Max_Drawdown_%']}%")
    c4, c5, c6 = st.columns(3)
    c4.metric("Нарушений правила ≤1 позиции", m["Constraint_Violations"])
    c5.metric("Tool Accuracy", "—" if m["Tool_Accuracy_%"] is None else f"{m['Tool_Accuracy_%']:.0f}%")
    c6.metric("Coherence", "—" if m["Coherence_%"] is None else f"{m['Coherence_%']:.0f}%")

    st.plotly_chart(_equity_chart(), use_container_width=True)
    st.plotly_chart(_price_trades_chart(selected), use_container_width=True)


# --- Запуск симуляции ---
if start:
    if not tickers:
        st.warning("Выберите хотя бы одну компанию.")
        st.stop()

    config.TICKERS = tickers  # агент работает по выбранному набору
    from agents import portfolio_graph as pg  # импорт здесь: тянет LLM-слой

    st.subheader("Лог рассуждений агентов")
    days_log: list[dict] = []
    progress = st.progress(0.0, text="Идёт симуляция…")

    for rec in pg.run_simulation(initial_balance=float(balance), risk_profile=risk):
        days_log.append(rec)
        s = rec["state"]
        pos = (f"{s.position.ticker} × {s.position.qty}" if s.position else "нет позиции")
        with st.expander(f"День {rec['day']} · кэш ${s.cash:.0f} · позиция: {pos}",
                         expanded=(rec["day"] == 1)):
            for line in rec["log"]:
                st.write(line)
        progress.progress(rec["day"] / config.SIMULATION_DAYS,
                          text=f"День {rec['day']} из {config.SIMULATION_DAYS}")

    progress.empty()
    st.success("Симуляция завершена")
    st.subheader("Итоги")
    _show_results(days_log, tickers)
else:
    st.info("Задайте параметры слева и нажмите «Начать симуляцию».")
