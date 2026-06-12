"""Агент-новостник (News Analyst) — узкий stateless-специалист.

Получает новости по (ticker, day) детерминированным инструментом и оценивает сентимент
структурированным вызовом GigaChat. Возвращает {summary, sentiment_score, signal}.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from agents.prompts import NEWS_ANALYST_PROMPT
from core.llm import get_chat
from tools.news_tools import fetch_daily_news


class NewsSentiment(BaseModel):
    """Структурированная оценка новостного фона по компании за один день."""

    summary: str = Field(description="краткое саммари новостного фона за день")
    sentiment_score: float = Field(description="сентимент от -1.0 (негатив) до +1.0 (позитив)")
    signal: str = Field(description="торговый сигнал: buy, sell или hold")


def analyze(ticker: str, day: int) -> NewsSentiment:
    """Оценить новостной фон по тикеру за день симуляции.

    Сначала детерминированно тянем новости (fetch_daily_news), затем просим GigaChat
    вернуть структурированную оценку. Пустой день обрабатываем без вызова LLM.
    """
    news = fetch_daily_news(ticker, day)
    if not news:
        return NewsSentiment(summary="Новостей нет", sentiment_score=0.0, signal="hold")

    headlines = "\n".join(
        f"- {n.get('headline', '')}. {n.get('summary', '')}".strip() for n in news
    )
    llm = get_chat().with_structured_output(NewsSentiment)
    return llm.invoke(
        f"{NEWS_ANALYST_PROMPT}\n\nКомпания: {ticker}. День: {day}.\n"
        f"Новости дня:\n{headlines}"
    )
