"""Инструмент новостей: чтение подготовленных новостей за день симуляции.

Источник — `data/news.json` (собран из Finnhub скриптом prepare_data). Агент-новостник
получает сырые заголовки/саммари за конкретный (ticker, day) и сам оценивает сентимент.
"""
from __future__ import annotations

import json
from functools import lru_cache

from core import config


@lru_cache(maxsize=1)
def _news_data() -> dict:
    with open(config.NEWS_JSON, encoding="utf-8") as f:
        return json.load(f)


def fetch_daily_news(ticker: str, day: int) -> list[dict]:
    """Вернуть список новостей по тикеру за конкретный день симуляции.

    Каждая новость: {headline, summary, datetime, source}. Пустой список — значит
    в этот день по компании новостей не было (валидная ситуация).
    """
    return _news_data().get(str(day), {}).get(ticker, [])
