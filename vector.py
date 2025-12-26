from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
DATA_PATH = Path("data/phones.csv")
DB_LOCATION = Path("./chrome_langchain_db")
EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "phones"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Global State (lazy initialization)
# ─────────────────────────────────────────────────────────
_vector_store: Optional[Chroma] = None
_embeddings: Optional[OllamaEmbeddings] = None


def _get_embeddings() -> OllamaEmbeddings:
    """Get or create embeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return _embeddings


def _build_documents_from_csv() -> tuple[list[Document], list[str]]:
    """Read phones.csv and create Document objects."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")
    
    df = pd.read_csv(DATA_PATH)
    documents = []
    ids = []
    
    for i, row in df.iterrows():
        page_content = (
            f"{row['Name']} {row['Brand']} {row['Model']} "
            f"with {row['Battery capacity (mAh)']}mAh battery, "
            f"{row['Screen size (inches)']} inch screen, "
            f"{row['RAM (MB)']}MB RAM, "
            f"{row['Rear camera']}MP rear camera"
        )
        document = Document(
            page_content=page_content,
            metadata={
                "brand": row["Brand"],
                "model": row["Model"],
                "price": row["Price"],
                "battery": row["Battery capacity (mAh)"],
                "ram": row["RAM (MB)"],
                "storage": row["Internal storage (GB)"],
                "os": row["Operating system"]
            },
            id=str(i)
        )
        ids.append(str(i))
        documents.append(document)
    
    logger.info(f"Built {len(documents)} documents from {DATA_PATH}")
    return documents, ids


def get_vector_store(force_rebuild: bool = False) -> Chroma:
    """Get or create the vector store (lazy initialization).
    
    Args:
        force_rebuild: If True, delete existing DB and rebuild from CSV.
    """
    global _vector_store
    
    if force_rebuild and DB_LOCATION.exists():
        import shutil
        shutil.rmtree(DB_LOCATION)
        logger.info(f"Deleted existing vector store at {DB_LOCATION}")
        _vector_store = None
    
    if _vector_store is not None:
        return _vector_store
    
    embeddings = _get_embeddings()
    need_to_add = not DB_LOCATION.exists()
    
    _vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(DB_LOCATION),
        embedding_function=embeddings
    )
    
    if need_to_add:
        documents, ids = _build_documents_from_csv()
        _vector_store.add_documents(documents=documents, ids=ids)
        logger.info(f"Added {len(documents)} documents to vector store")
    else:
        logger.info(f"Loaded existing vector store from {DB_LOCATION}")
    
    return _vector_store


def rebuild_index() -> None:
    """Force rebuild the vector index from phones.csv."""
    get_vector_store(force_rebuild=True)
    logger.info("Vector index rebuilt successfully")


def retrieve_with_scores(query: str, k: int = 5):
    """Return list of (Document, score).

    Score semantics depend on the underlying vector store implementation.
    For Chroma via LangChain, `similarity_search_with_relevance_scores` returns
    relevance scores in [0, 1] when available.
    """
    store = get_vector_store()
    
    if hasattr(store, "similarity_search_with_relevance_scores"):
        return store.similarity_search_with_relevance_scores(query, k=k)
    # Fallback: some implementations expose `similarity_search_with_score`
    if hasattr(store, "similarity_search_with_score"):
        return store.similarity_search_with_score(query, k=k)
    # Last resort: no scores available
    return [(doc, None) for doc in store.similarity_search(query, k=k)]