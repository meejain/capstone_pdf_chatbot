"""Step 9: LLM access through any OpenAI-compatible server (LM Studio by default, Ollama or OpenAI work too)."""
import requests
from langchain_openai import ChatOpenAI

import config


def get_llm(model: str = None, base_url: str = None, temperature: float = None, max_tokens: int = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or config.LLM_MODEL,
        base_url=base_url or config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        temperature=config.LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=max_tokens or config.LLM_MAX_TOKENS,
        timeout=300,
    )


def list_models(base_url: str = None) -> list[str]:
    """Health check: returns the model ids served by the endpoint ([] if the server is unreachable)."""
    try:
        r = requests.get(f"{(base_url or config.LLM_BASE_URL).rstrip('/')}/models", timeout=3,
                         headers={"Authorization": f"Bearer {config.LLM_API_KEY}"})
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]
    except (requests.RequestException, ValueError, KeyError):
        return []


def complete(messages: list[dict], **kw) -> str:
    return get_llm(**kw).invoke(messages).content.strip()


def stream(messages: list[dict], **kw):
    for chunk in get_llm(**kw).stream(messages):
        if chunk.content:
            yield chunk.content
