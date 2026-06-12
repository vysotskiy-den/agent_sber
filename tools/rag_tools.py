"""RAG-инструменты фундаментального агента (FAISS на GigaChat-эмбеддингах).

Реализует Domain Knowledge уровня 2 («сквозной RAG»): два среза знаний —
предметная область (фундаментал компаний) и смежная (макроэкономика). Индекс строится
один раз из `data/knowledge/` и кэшируется в `faiss_index/`.

  * search_company_reports(query) — поиск по фундаментальным профилям компаний
  * search_macro_economics(query) — поиск по макроэкономическому контексту
"""
from __future__ import annotations

from functools import lru_cache

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from core import config
from core.llm import get_embeddings


def _load_documents() -> list[Document]:
    """Читает knowledge-файлы в Documents с метаданными kind/ticker."""
    docs: list[Document] = []
    for path in sorted(config.KNOWLEDGE_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if path.stem.startswith("fundamental_"):
            ticker = path.stem.removeprefix("fundamental_")
            docs.append(Document(text, metadata={"kind": "fundamental", "ticker": ticker}))
        elif path.stem.startswith("macro"):
            docs.append(Document(text, metadata={"kind": "macro", "ticker": None}))
    return docs


def build_index() -> None:
    """Строит FAISS-индекс из knowledge-файлов и сохраняет на диск."""
    docs = _load_documents()
    store = FAISS.from_documents(docs, get_embeddings())
    store.save_local(str(config.FAISS_DIR))


@lru_cache(maxsize=1)
def _store() -> FAISS:
    """Загружает кэшированный индекс (строит при первом обращении, если его нет)."""
    if not (config.FAISS_DIR / "index.faiss").exists():
        build_index()
    return FAISS.load_local(
        str(config.FAISS_DIR), get_embeddings(), allow_dangerous_deserialization=True
    )


def search_company_reports(query: str, k: int = 2) -> list[str]:
    """Семантический поиск по фундаментальным профилям компаний (предметная область)."""
    hits = _store().similarity_search(query, k=k, filter={"kind": "fundamental"})
    return [d.page_content for d in hits]


def search_macro_economics(query: str, k: int = 1) -> list[str]:
    """Семантический поиск по макроэкономическому контексту (смежная область)."""
    hits = _store().similarity_search(query, k=k, filter={"kind": "macro"})
    return [d.page_content for d in hits]
