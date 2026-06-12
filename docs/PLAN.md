# Состояние реализации

## Реализовано

**Данные и конфигурация**
- `core/config.py` — центральная конфигурация (тикеры, окно симуляции, портфель, ключи, модель).
- `scripts/prepare_data.py` — сбор реальных данных (yfinance + Finnhub) в `data/`.
- Собраны `prices.csv`, `news.json`, корпус `knowledge/` (фундаментал + макро).

**Ядро МАС**
- `core/state.py` — `Position` / `PortfolioState`.
- `database/db.py` — SQLite: «Цифровой двойник», сделки, заметки, equity-кривая.
- `core/llm.py` — фабрика GigaChat (чат + эмбеддинги) с таймаутом и ретраями.
- Инструменты: `tools/market_tools.py` (цены с защитой от будущего + сделки),
  `tools/memory_tools.py`, `tools/news_tools.py`, `tools/rag_tools.py` (FAISS-RAG).
- Промпты трёх ролей — `agents/prompts.py`.
- Агенты: News Analyst (structured output), Fundamental Analyst (ReAct + RAG),
  Portfolio Manager (оркестратор) — `agents/`.

**Симуляция и метрики**
- `run_simulation` — автономный цикл по дням с guard роли и фиксацией equity.
- `core/metrics.py` — ROI, Win Rate, Max Drawdown, Constraint Compliance, Tool Accuracy, Coherence.
- `scripts/run_simulation.py` — CLI-прогон с сохранением артефакта `data/run_result.json`.

**Интерфейс**
- `app.py` — Streamlit: параметры, потоковый лог рассуждений, графики портфеля и сделок, метрики.

**Тесты**
- `tests/` — детерминированная часть (state, db, метрики). Недетерминированный LLM-слой
  проверяется прогоном симуляции (см. тест-стратегию в `CLAUDE.md`).

## Возможные улучшения
- Кэш сентимента новостника по `(ticker, day)` — ускоряет повторные прогоны.
- LLM-судья для Coherence вместо парсинга лога регулярными выражениями.
- Шорт-позиции и дробные акции (снять ограничения «только лонг / целые акции»).
- Расширение вселенной тикеров и окна (всё конфигурируется в `core/config.py`).
- Сравнение нескольких прогонов / профилей в UI.
- Асинхронный сбор данных в `prepare_data` при большой вселенной тикеров.
