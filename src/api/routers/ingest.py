from fastapi import APIRouter, UploadFile, File, HTTPException
from src.schemas.ingest import IngestResponse
from src.services.ingestion.loader import load_uploaded_pdf
from src.services.ingestion.chunker import get_parent_splitter, get_child_splitter

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a PDF document, extract text, and chunk it.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # 1. Load the PDF
        docs = await load_uploaded_pdf(file)
        
        # 2. Chunk the documents (Parent/Child split)
        parent_splitter = get_parent_splitter()
        child_splitter = get_child_splitter()
        
        parent_chunks = parent_splitter.split_documents(docs)
        child_chunks = child_splitter.split_documents(docs)
        
        # 3. Store these chunks in OpenSearch
        from src.services.opensearch.indexer import index_documents
        
        # In a real background task, we might do this asynchronously,
        # but for now we do it synchronously.
        index_documents(parent_chunks, chunk_type="parent")
        index_documents(child_chunks, chunk_type="child")
        
        # Log to Neon Postgres if available
        from src.core.config import get_settings
        settings = get_settings()
        if settings.POSTGRES_DATABASE_URL:
            from src.db.session import AsyncSessionLocal
            from src.db.models import IngestedDocument
            async with AsyncSessionLocal() as session:
                doc_record = IngestedDocument(
                    filename=file.filename,
                    user_id="default_user", # Extend API to accept user_id later
                    chunk_count=len(parent_chunks) + len(child_chunks),
                    status="completed"
                )
                session.add(doc_record)
                await session.commit()
                
        return IngestResponse(
            filename=file.filename,
            total_pages=len(docs),
            total_parent_chunks=len(parent_chunks),
            total_child_chunks=len(child_chunks),
            status="success (stored in OpenSearch)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {str(e)}")
