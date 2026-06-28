from langchain_openai import ChatOpenAI
from src.core.config import get_settings

settings = get_settings()

def get_llm() -> ChatOpenAI:
    """
    Returns a configured LangChain Chat Model.
    Although this uses ChatOpenAI under the hood, it is configured
    to point to the AICredits aggregator and run Llama models
    by overriding the base_url and api_key.
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        temperature=0.0
    )
