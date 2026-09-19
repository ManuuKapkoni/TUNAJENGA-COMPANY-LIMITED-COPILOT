from functools import lru_cache
from langchain_groq import ChatGroq
from src.config import get_settings


@lru_cache
def get_llm():
    s = get_settings()
    if not s.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured in .env")
    return ChatGroq(
        model=s.groq_model,
        temperature=0,
        api_key=s.groq_api_key,
    )