# Проектные решения

Зафиксированные технические решения по реализации.

1. **LLM — GigaChat** через `langchain-gigachat` (поддерживает function-calling). Чат и
   эмбеддинги создаются в `core/llm.py`; `verify_ssl_certs=False` (сертификаты НУЦ Минцифры).
2. **Оркестрация — LangGraph / LangChain** (`create_agent`): граф с циклом и внешней памятью.
3. **Рынок — US.** Тикеры по умолчанию: AAPL, MSFT, TSLA, AMZN, GOOG (расширяемо через
   `core/config.py`). Окно — недавние торговые дни, где есть новости. yfinance без суффиксов.
4. **Цены и фундаментал — yfinance**; **новости — Finnhub** (`company-news`, фильтр по тикеру
   и датам). Telegram-каналы и PDF-отчёты не используются.
5. **RAG фундаментального агента** строится из `yfinance.Ticker().info` (фундаментал компаний)
   и локальной макро-базы (ставка ФРС, инфляция) — сквозной RAG по двум срезам знаний.
6. **Пакетный менеджер — uv** (`pyproject.toml` + `uv.lock`).

## Ключи (в `.env`, шаблон — `.env.example`)
- `GIGACHAT_CREDENTIALS` — Authorization key GigaChat; `GIGACHAT_SCOPE` (по умолчанию `GIGACHAT_API_PERS`).
- `FINNHUB_API_KEY` — бесплатный ключ с finnhub.io (нужен для `scripts/prepare_data.py`).
- Макро-данные — статический локальный текст, отдельного API не требуют.
