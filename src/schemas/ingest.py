from pydantic import BaseModel

class IngestResponse(BaseModel):
    filename: str
    total_pages: int
    total_parent_chunks: int
    total_child_chunks: int
    status: str
