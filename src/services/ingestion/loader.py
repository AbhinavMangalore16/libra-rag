import os
import aiofiles
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader
from fastapi import UploadFile

import tempfile

async def load_uploaded_pdf(file: UploadFile) -> List[Document]:
    """
    Saves an uploaded PDF to a temporary file, loads it using PyMuPDFLoader,
    and returns the Langchain Documents.
    """
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    # Save the file asynchronously
    async with aiofiles.open(temp_file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        
    try:
        # PyMuPDFLoader is synchronous, but fast
        loader = PyMuPDFLoader(temp_file_path)
        docs = loader.load()
        
        # Enrich metadata
        for doc in docs:
            doc.metadata["source_file"] = file.filename
            doc.metadata["total_pages"] = len(docs)
            
        return docs
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
