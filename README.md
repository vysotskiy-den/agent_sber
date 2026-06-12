# Agent Sber — Мультиагентная торговая система (МАС)

Проект: иерархическая мультиагентная система, симулирующая 10-дневную
торговлю акциями.

Автономный агент-управляющий портфелем принимает торговые решения, опираясь на
двух узких агентов-советников (Новостник и Фундаментальный аналитик), внешнюю
память («Цифровой двойник» портфеля) и RAG по отчётам/макроэкономике.

## Состав МАС
| Агент | Роль | Память | Инструменты |
|-------|------|--------|-------------|
| Portfolio Manager (оркестратор) | Управляющий портфелем | State + долгосрочные заметки | `ask_news_agent`, `ask_fundamental_agent`, `get_current_price`, `execute_trade`, `save_insight_to_memory` |
| News Analyst | Аналитик новостного фона | Stateless | `fetch_daily_news(ticker, day)` |
| Fundamental Analyst | Аналитик ценных бумаг / макро | Stateless | `search_company_reports(query)`, `search_macro_economics(query)` |

## Технологический стек
- **Пакетный менеджер:** [uv](https://docs.astral.sh/uv/) (зависимости в `pyproject.toml`, лок в `uv.lock`).
- **LLM:** GigaChat через `langchain-gigachat` (чат + эмбеддинги).
- **Оркестрация:** LangGraph / LangChain (ReAct-агенты).
- **RAG:** FAISS на GigaChat-эмбеддингах.
- **Память:** SQLite («Цифровой двойник» портфеля + заметки агента).
- **UI:** Streamlit + Plotly.
- **Данные:** yfinance (цены + фундаментал), Finnhub (новости).

## Быстрый старт

### 1. Установка окружения
```bash
uv sync          # поднимает виртуальное окружение из uv.lock
```

### 2. Ключи API
Скопируйте шаблон и впишите свои ключи:
```bash
cp .env.example .env
```
| Переменная | Назначение | Где взять |
|------------|------------|-----------|
| `GIGACHAT_CREDENTIALS` | Authorization key GigaChat | личный кабинет GigaChat API |
| `GIGACHAT_SCOPE` | Scope (по умолчанию `GIGACHAT_API_PERS`) | — |
| `FINNHUB_API_KEY` | Новости по тикерам | [finnhub.io](https://finnhub.io) (бесплатно) |

### 3. Подготовка данных (один раз)
Скачивает реальные цены, новости и фундаментал в `data/` (кэшируется локально):
```bash
uv run python -m scripts.prepare_data
```

### 4. Запуск UI
```bash
uv run streamlit run app.py
```

## Интерфейс (Streamlit)
- **Левая панель — параметры (задаются ДО старта, дальше агент автономен):**
  выбор компаний, начальный баланс, риск-профиль (Консервативный / Агрессивный),
  кнопка «Начать симуляцию».
- **Центральный экран:**
  - потоковый **лог рассуждений** агентов по дням (раскрывающиеся блоки: какие
    инструменты вызваны, что вернули, как прошла самопроверка Reflection и сделка);
  - **график стоимости портфеля** по дням;
  - **график цен** выбранных компаний с зелёными (Buy) и красными (Sell) точками сделок;
  - **итоговые метрики** (см. ниже).

## Управление через CLI
```bash
# Прогон симуляции с сохранением артефакта в data/run_result.json
uv run python -m scripts.run_simulation --balance 10000 --risk aggressive

# Пересобрать данные
uv run python -m scripts.prepare_data

# Тесты (детерминированная часть: state, db, метрики)
uv run pytest
```
Модули запускаются из корня проекта (`pythonpath` для pytest настроен в `pyproject.toml`).

## Метрики качества
**Бизнес-метрики портфеля:** ROI, Win Rate, Max Drawdown.
**Метрики МАС:** Constraint Compliance (нарушения правила «≤1 позиции», цель — 0),
Tool Accuracy (доля успешных вызовов инструментов), Coherence (согласованность сделок
с сигналом новостей).

## Правила симуляции
- Не более **одной открытой позиции** одновременно (`MAX_OPEN_POSITIONS`).
- Агент видит цену только за **текущий день** (защита от «заглядывания в будущее»).
- В рантайме используются только локально подготовленные данные — никаких живых
  запросов во время демо (воспроизводимость).

## Структура проекта
```
core/        config.py · state.py · llm.py · metrics.py
database/    db.py — SQLite «Цифровой двойник», сделки, заметки, equity-кривая
tools/       market_tools · memory_tools · news_tools · rag_tools
agents/      prompts · news_agent · fundamental_agent · portfolio_graph (+ run_simulation)
scripts/     prepare_data.py · run_simulation.py
tests/       тесты детерминированной части
app.py       Streamlit UI
data/        prices.csv · news.json · knowledge/ (генерируются prepare_data)
```

Все настройки (тикеры, окно симуляции, баланс, риск-профиль, модель GigaChat) — в
`core/config.py`.
