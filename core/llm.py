"""Фабрика клиентов GigaChat (чат + эмбеддинги).

Единая точка создания LLM-клиентов: креды и параметры берутся из `core/config.py`,
чтобы не дублировать их по модулям. `verify_ssl_certs=False` — GigaChat использует
сертификаты НУЦ Минцифры; для учебного прототипа отключаем проверку (см. OPEN_QUESTIONS).
"""
from __future__ import annotations

import urllib3

from langchain_gigachat import GigaChat, GigaChatEmbeddings

from core import config

# GigaChat по самоподписанному CA — глушим шумные предупреждения urllib3.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_chat(temperature: float | None = None) -> GigaChat:
    """Чат-модель GigaChat для рассуждений агентов."""
    return GigaChat(
        credentials=config.GIGACHAT_CREDENTIALS,
        scope=config.GIGACHAT_SCOPE,
        model=config.GIGACHAT_MODEL,
        temperature=config.GIGACHAT_TEMPERATURE if temperature is None else temperature,
        timeout=config.GIGACHAT_TIMEOUT,
        max_retries=config.GIGACHAT_MAX_RETRIES,
        verify_ssl_certs=False,
        profanity_check=False,
    )


def get_embeddings() -> GigaChatEmbeddings:
    """Эмбеддинги GigaChat (1024-dim) для FAISS-RAG фундаментального агента."""
    return GigaChatEmbeddings(
        credentials=config.GIGACHAT_CREDENTIALS,
        scope=config.GIGACHAT_SCOPE,
        verify_ssl_certs=False,
    )
