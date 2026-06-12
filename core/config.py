"""Центральная конфигурация симуляции.

Здесь собраны все «ручки» проекта: список компаний, окно симуляции, стартовые
параметры портфеля и пути к данным. Меняя значения тут, мы влияем на весь пайплайн
(сбор данных, прогон агентов, UI) без правок в логике.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Пути ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
PRICES_CSV = DATA_DIR / "prices.csv"
NEWS_JSON = DATA_DIR / "news.json"
FAISS_DIR = ROOT / "faiss_index"
DB_PATH = ROOT / "portfolio.sqlite"

# --- Рынок и тикеры (US) ---
TICKERS: list[str] = ["AAPL", "MSFT", "TSLA", "AMZN", "GOOG"]

# --- Окно симуляции ---
# Сколько последних ТОРГОВЫХ дней моделируем. Конкретные даты подставляются при
# сборе цен (берём реальный торговый календарь из yfinance).
SIMULATION_DAYS: int = 10

# --- Стартовые параметры портфеля ---
DEFAULT_INITIAL_BALANCE: float = 10_000.0
MAX_OPEN_POSITIONS: int = 1  # правило: не более 1 акции в портфеле (Constraint Compliance)

# --- Риск-профили (влияют на system_prompt Управляющего — критерий Role) ---
RISK_PROFILES = ("conservative", "aggressive")
DEFAULT_RISK_PROFILE = "conservative"
# Просадка от пика (в %), при которой Управляющий сам ужесточает свой промпт (Role → уровень 2)
DRAWDOWN_GUARD_PCT: float = 3.0

# --- Ключи API ---
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# --- Модель GigaChat ---
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-2-Max")
GIGACHAT_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", "0.1"))
GIGACHAT_TIMEOUT = float(os.getenv("GIGACHAT_TIMEOUT", "90"))  # сек на запрос (устойчивость прогона)
GIGACHAT_MAX_RETRIES = int(os.getenv("GIGACHAT_MAX_RETRIES", "3"))  # ретраи при сетевых сбоях
