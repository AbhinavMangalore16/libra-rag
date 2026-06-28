from fastapi import APIRouter, HTTPException
from src.schemas.search import SearchRequest, SearchResponse
from src.services.opensearch.retriever import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Executes a hybrid search combining Semantic Vector (Jina AI) and Keyword (BM25) approaches.
    Returns fused results using Reciprocal Rank Fusion (RRF).
    """
    try:
        results = hybrid_search(
            query=request.query,
            k=request.k,
            chunk_type=request.chunk_type
        )
        
        return SearchResponse(
            query=request.query,
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
