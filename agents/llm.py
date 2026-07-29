from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from backend.core.config import settings

_primary_base = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.groq_api_key,
    temperature=0,
    max_tokens=1200
)

_fallback_base = ChatMistralAI(
    model="mistral-large-latest",
    api_key=settings.mistral_api_key,
    temperature=0,
    max_tokens=1200
)

primary_llm = _primary_base.with_retry(
    stop_after_attempt=4,
    wait_exponential_jitter=True
)

fallback_llm = _fallback_base.with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True
)

def get_llm(prefer_mistral: bool = False):
    return fallback_llm if prefer_mistral else primary_llm

def get_base_llm(prefer_mistral: bool = False):
    return _fallback_base if prefer_mistral else _primary_base

async def get_llm_with_fallback():
    """Try Groq first, fall back to Mistral if rate limited."""
    return primary_llm
