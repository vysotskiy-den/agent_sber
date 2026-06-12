# Архитектура и ИТ-ландшафт

## Паттерн
Иерархическая МАС: один **агент-оркестратор** (Portfolio Manager) и два **узких
агента-советника** (News Analyst, Fundamental Analyst). Оркестратор и фундаменталист —
ReAct-агенты на `create_agent`; новостник — структурированный вызов GigaChat (без цикла).

## Поток одного дня (цикл по дням симуляции)
1. **Начало дня:** оркестратору инжектится состояние портфеля (день, кэш, позиция, тикеры).
2. **Guard роли:** если просадка от пика ≥ `DRAWDOWN_GUARD_PCT`, system_prompt управляющего
   дополняется установкой осторожности (`_apply_drawdown_guard`).
3. **Сбор информации:** оркестратор вызывает `ask_news_agent` по нескольким тикерам;
   новостник возвращает `{summary, sentiment_score, signal}`. При необходимости —
   `ask_fundamental_agent` (RAG по фундаменталу + макро).
4. **Reasoning (ReAct):** сопоставляет сигналы и заметки из памяти, формирует план.
5. **Reflection:** проверяет план на правила (хватает денег, ≤1 позиция) и корректирует.
6. **Action:** `execute_trade(action, ticker)`; состояние «двойника» обновляется детерминированно.
7. **Конец дня:** фиксируется стоимость портфеля (`snapshot_equity`) для метрик.

## Память
- **Жёсткий State («Цифровой двойник»):** баланс, открытая позиция, цена и день покупки,
  риск-профиль, динамическая добавка к промпту. Хранится в SQLite, обновляется после сделок.
- **Заметки агента (долгосрочная):** `save_insight_to_memory(text)` — агент сам решает,
  что сохранить, и читает на следующих днях через `read_memory`.

## Данные
Собираются из реальных источников на этапе подготовки (`scripts/prepare_data.py`),
кэшируются локально; в рантайме агент обращается только к локальным файлам через инструменты
(детерминизм и воспроизводимость):
- `data/prices.csv` — цены из **yfinance** (ticker, day, close)
- `data/news.json` — новости из **Finnhub** (`company-news`), разложенные по дням и тикерам
- `data/knowledge/` — корпус для RAG фундаментального агента:
  - фундаментал компаний из `yfinance.Ticker().info` (P/E, маржа, выручка) → текст
  - макро (ставка ФРС, инфляция) → локальный текст
  - индексируется в FAISS на GigaChat-эмбеддингах (`faiss_index/`, пересобирается из корпуса)

Рынок — US; тикеры заданы в `core/config.py` (по умолчанию AAPL, MSFT, TSLA, AMZN, GOOG).

## Защита от заглядывания в будущее
`get_current_price` отдаёт цену только за день ≤ текущего дня симуляции — агент не может
получить будущие котировки.

## Структура репозитория
```
core/        config.py · state.py · llm.py · metrics.py
database/    db.py — SQLite «Цифровой двойник», сделки, заметки, equity-кривая
tools/       market_tools · memory_tools · news_tools · rag_tools
agents/      prompts · news_agent · fundamental_agent · portfolio_graph (+ run_simulation)
scripts/     prepare_data.py · run_simulation.py
tests/       тесты детерминированной части
app.py       Streamlit UI
data/        prices.csv · news.json · knowledge/
```

## Технологический стек
- Оркестрация: **LangGraph / LangChain** (`create_agent`, граф с циклом и памятью)
- LLM: **GigaChat** через `langchain-gigachat` (чат + эмбеддинги), фабрика в `core/llm.py`
- UI: Streamlit + Plotly
- RAG: FAISS + GigaChat-эмбеддинги
- Память: SQLite («Цифровой двойник» + заметки)
- Данные: yfinance (цены + фундаментал) · Finnhub (новости) · локальная макро-база
- Пакетный менеджер: uv (`pyproject.toml` + `uv.lock`)
