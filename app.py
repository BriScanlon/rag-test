# app.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chunking import chunk_text
from vectorising import embed_chunks
from indexing import create_faiss_index, query_index
from sentence_transformers import SentenceTransformer
from rag_request import send_to_rag_api
import numpy as np
from process_document import process_document
import uvicorn

# Load the pre-trained embedding model for query embedding
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize FastAPI app
app = FastAPI()

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Folder containing the documents
DOCUMENTS_FOLDER = "documents/"


# Pydantic model for request body (only the user query)
class DocumentQueryRequest(BaseModel):
    user_query: str  # Query for searching the documents


# FastAPI POST endpoint to process all documents and query
@app.post("/process_documents/")
async def process_documents(request: DocumentQueryRequest):
    print("1. Beginning process documents function")
    user_query = request.user_query

    if not user_query:
        raise HTTPException(status_code=400, detail="User query must be provided.")

    # Initialize storage for document chunks and embeddings
    all_chunks = []
    all_embeddings = []

    # Iterate over all documents in the folder
    for document_name in os.listdir(DOCUMENTS_FOLDER):
        document_path = os.path.join(DOCUMENTS_FOLDER, document_name)

        # Load each document
        document_text = process_document(document_path)
        if document_text is None:
            continue  # Skip documents that are empty or not found

        # Split document into chunks
        chunks = chunk_text(document_text, chunk_size=512)
        if not chunks:
            continue  # Skip if no chunks created

        # Embed each chunk
        embeddings = embed_chunks(chunks)
        if embeddings.size == 0:
            continue  # Skip if no embeddings created

        # Add to the global list of chunks and embeddings
        all_chunks.extend(
            [{"document_name": document_name, "chunk": chunk} for chunk in chunks]
        )
        all_embeddings.append(embeddings)

    # Ensure there are embeddings from at least one document
    if not all_embeddings:
        raise HTTPException(
            status_code=404, detail="No valid documents found or processed."
        )

    # Stack all embeddings
    all_embeddings = np.vstack(all_embeddings)

    # Create FAISS index for similarity search
    try:
        index = create_faiss_index(all_embeddings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Query embedding for the user query
    query_embedding = model.encode([user_query])
    if query_embedding.size == 0:
        raise HTTPException(status_code=400, detail="Failed to encode query.")

    # Query the index
    try:
        result_indices = query_index(index, query_embedding)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Retrieve the top matching chunks
    result_chunks = [all_chunks[idx] for idx in result_indices]

    # Send the document chunks and user query to the RAG LLM API
    generated_answer = send_to_rag_api(result_chunks, user_query)

    return {"generated_answer": generated_answer}


# Add uvicorn startup code
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
