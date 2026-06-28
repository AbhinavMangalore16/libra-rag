from opensearchpy import OpenSearch
from src.core.config import get_settings

settings = get_settings()

def get_opensearch_client() -> OpenSearch:
    """
    Returns an initialized OpenSearch client connecting to the Docker container.
    """
    client = OpenSearch(
        hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
        http_compress=True, # enables gzip compression for request bodies
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )
    return client
