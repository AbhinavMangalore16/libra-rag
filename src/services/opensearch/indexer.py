from typing import List
from langchain_core.documents import Document
from opensearchpy import OpenSearch, helpers
from src.services.opensearch.client import get_opensearch_client

INDEX_NAME = "agentic-rag-chunks"

def create_index_if_not_exists(client: OpenSearch):
    """
    Creates the OpenSearch index with BM25 mappings.
    (Vector mapping will be added here later once embeddings are decided).
    """
    if not client.indices.exists(index=INDEX_NAME):
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "standard"},
                    "source_file": {"type": "keyword"},
                    "page_content": {"type": "text"},
                    "chunk_type": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "space_type": "cosinesimil"
                        }
                    }
                }
            }
        }
        client.indices.create(index=INDEX_NAME, body=index_body)

def index_documents(docs: List[Document], chunk_type: str = "child"):
    """
    Bulk indexes Langchain documents into OpenSearch.
    """
    client = get_opensearch_client()
    create_index_if_not_exists(client)
    
    from src.services.embeddings.client import get_embeddings
    embeddings_client = get_embeddings()
    
    actions = []
    # Optionally, we can batch embed, but for simplicity we do it here.
    texts = [doc.page_content for doc in docs]
    
    # In production, we'd batch this to avoid API rate limits,
    # but Langchain's embed_documents already handles some batching.
    print(f"Generating embeddings for {len(texts)} {chunk_type} chunks...")
    vectors = embeddings_client.embed_documents(texts)
    
    for i, doc in enumerate(docs):
        action = {
            "_index": INDEX_NAME,
            "_source": {
                "text": doc.page_content,
                "page_content": doc.page_content,
                "source_file": doc.metadata.get("source_file", "unknown"),
                "total_pages": doc.metadata.get("total_pages", 0),
                "page_number": doc.metadata.get("page", 0),
                "chunk_type": chunk_type,
                "embedding": vectors[i]
            }
        }
        actions.append(action)
        
    # Bulk insert
    helpers.bulk(client, actions)
    print(f"Successfully indexed {len(actions)} {chunk_type} chunks into {INDEX_NAME}.")
