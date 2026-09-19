from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from src.config import get_settings


@lru_cache
def get_embeddings():
    s = get_settings()
    if not s.hf_token:
        raise RuntimeError("HF_TOKEN is not configured")
    return HuggingFaceEndpointEmbeddings(
        model=s.embedding_model,
        task="feature-extraction",
        huggingfacehub_api_token=s.hf_token,
    )


def get_vector_store():
    """
    Load the FAISS index from disk if it exists, otherwise return None.
    """
    s = get_settings()
    index_path = Path(s.faiss_index_path)

    if not index_path.exists():
        return None

    return FAISS.load_local(
        str(index_path),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def save_vector_store(store: FAISS):
    s = get_settings()
    index_path = Path(s.faiss_index_path)
    index_path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_path))


def get_retriever():
    s = get_settings()
    store = get_vector_store()
    if store is None:
        raise RuntimeError(
            "FAISS index not found. Run data_ingestion.py first."
        )
    return store.as_retriever(search_kwargs={"k": s.top_k})
