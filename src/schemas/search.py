from pydantic import BaseModel
from typing import List

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    chunk_type: str = "parent"

class SearchResult(BaseModel):
    text: str
    source_file: str
    page_number: int
    score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
