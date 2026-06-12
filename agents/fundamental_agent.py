"""Агент-фундаменталист (Fundamental Analyst) — ReAct + RAG.

Сам решает, что искать: вызывает инструменты семантического поиска по отчётам компаний
и по макроэкономике (сквозной RAG, Domain Knowledge уровня 2), затем формирует
долгосрочный вывод. Вызывается управляющим редко (1-й день / резкие новости).
"""
from __future__ import annotations

from functools import lru_cache

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from agents.prompts import FUNDAMENTAL_ANALYST_PROMPT
from core.llm import get_chat
from tools import rag_tools


@tool
def search_company_reports(query: str) -> str:
    """Семантический поиск по фундаментальным профилям компаний США."""
    return "\n\n".join(rag_tools.search_company_reports(query))


@tool
def search_macro_economics(query: str) -> str:
    """Семантический поиск по макроэкономическому контексту (ставка ФРС, инфляция)."""
    return "\n\n".join(rag_tools.search_macro_economics(query))


@lru_cache(maxsize=1)
def _agent():
    return create_agent(
        get_chat(),
        tools=[search_company_reports, search_macro_economics],
        system_prompt=FUNDAMENTAL_ANALYST_PROMPT,
    )


def analyze(ticker: str) -> str:
    """Дать долгосрочную фундаментальную оценку компании (текстовый вывод)."""
    result = _agent().invoke(
        {"messages": [HumanMessage(f"Дай долгосрочную фундаментальную оценку компании {ticker}.")]}
    )
    return result["messages"][-1].content
