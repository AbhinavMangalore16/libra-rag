from typing import List, Dict
from src.services.opensearch.client import get_opensearch_client
from src.services.opensearch.indexer import INDEX_NAME
from src.services.embeddings.client import get_embeddings

def reciprocal_rank_fusion(vector_results, bm25_results, k=60):
    """
    Fuses results from vector and bm25 searches using Reciprocal Rank Fusion (RRF).
    """
    fused_scores = {}
    docs = {}
    
    # Process vector results
    for rank, hit in enumerate(vector_results):
        doc_id = hit["_id"]
        docs[doc_id] = hit
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (rank + k))
        
    # Process BM25 results
    for rank, hit in enumerate(bm25_results):
        doc_id = hit["_id"]
        docs[doc_id] = hit
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (rank + k))
        
    # Sort by fused score descending
    sorted_fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    return [docs[doc_id] for doc_id, _ in sorted_fused]

def hybrid_search(query: str, k: int = 5, chunk_type: str = "parent") -> List[Dict]:
    """
    Executes a hybrid search query using both BM25 (keyword) and k-NN (semantic vector).
    Combines the top results using Reciprocal Rank Fusion (RRF).
    """
    client = get_opensearch_client()
    embeddings_client = get_embeddings()
    
    # 1. Convert user query to 1024-dim Jina embedding
    query_vector = embeddings_client.embed_query(query)
    
    fetch_size = k * 2 # Fetch more candidates for RRF fusion
    
    # 2. Vector Search (Semantic)
    vector_query = {
        "size": fetch_size,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": fetch_size
                }
            }
        },
        "_source": ["text", "source_file", "page_number"]
    }
    
    # 3. BM25 Search (Keyword)
    bm25_query = {
        "size": fetch_size,
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "text": query
                        }
                    }
                ],
                "filter": [
                    {
                        "term": {
                            "chunk_type": chunk_type
                        }
                    }
                ]
            }
        },
        "_source": ["text", "source_file", "page_number"]
    }
    
    try:
        vector_resp = client.search(index=INDEX_NAME, body=vector_query)
        vector_hits = vector_resp["hits"]["hits"]
    except Exception as e:
        print(f"Vector search failed: {e}")
        vector_hits = []
        
    try:
        bm25_resp = client.search(index=INDEX_NAME, body=bm25_query)
        bm25_hits = bm25_resp["hits"]["hits"]
    except Exception as e:
        print(f"BM25 search failed: {e}")
        bm25_hits = []
    
    # 4. Fuse the results
    fused_hits = reciprocal_rank_fusion(vector_hits, bm25_hits)
    
    # 5. Format results for the API response
    results = []
    for hit in fused_hits[:k]:
        source = hit["_source"]
        results.append({
            "text": source.get("text", ""),
            "source_file": source.get("source_file", "unknown"),
            "page_number": source.get("page_number", 0),
            "score": hit.get("_score", 0.0)
        })
        
    return results
