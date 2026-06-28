from langchain_community.embeddings import JinaEmbeddings
from src.core.config import get_settings

settings = get_settings()

def get_embeddings() -> JinaEmbeddings:
    """
    Returns an initialized Jina AI Embeddings client.
    Using jina-embeddings-v3 which outputs 1024-dimensional vectors.
    """
    return JinaEmbeddings(
        jina_api_key=settings.JINA_API_KEY,
        model_name="jina-embeddings-v3"
    )
