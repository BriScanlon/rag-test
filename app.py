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


# Pydantic model for request body
class DocumentQueryRequest(BaseModel):
    document_name: str  # Name of the document to search in
    user_query: str  # Query for searching the document


# Function to load the document
def load_document(file_path):
    print(f"1. Attempting to load document with file path: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            if not content.strip():  # Check for empty or whitespace content
                return None
            return content
    except FileNotFoundError:
        return None


# FastAPI POST endpoint to process document and query
@app.post("/process_document/")
async def process_document(request: DocumentQueryRequest):
    print("1. Beginning process document function")
    # Get document name and user query from the request body
    document_name = request.document_name
    user_query = request.user_query

    if not document_name or not user_query:
        raise HTTPException(
            status_code=400,
            detail="Both document name and user query must be provided.",
        )

    # Construct document path
    document_path = os.path.join(DOCUMENTS_FOLDER, document_name)

    # Load the document
    document_text = load_document(document_path)
    if document_text is None:
        raise HTTPException(
            status_code=404, detail=f"Document '{document_name}' not found or empty."
        )

    # Split document into chunks
    chunks = chunk_text(document_text, chunk_size=512)
    if not chunks:
        raise HTTPException(
            status_code=400, detail="No valid chunks created from the document."
        )

    # Embed each chunk
    embeddings = embed_chunks(chunks)
    if embeddings.size == 0:
        raise HTTPException(
            status_code=400,
            detail="No valid embeddings created from the document chunks.",
        )

    # Create FAISS index for similarity search
    try:
        index = create_faiss_index(embeddings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Query embedding for user query
    query_embedding = model.encode([user_query])
    if query_embedding.size == 0:
        raise HTTPException(status_code=400, detail="Failed to encode query.")

    # Query the index
    try:
        result_indices = query_index(index, query_embedding)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Retrieve the top matching chunks
    result_chunks = [
        {"document_name": document_name, "chunk": chunks[idx]} for idx in result_indices
    ]

    # Send the document chunks and user query to the RAG LLM API
    generated_answer = send_to_rag_api(result_chunks, user_query)


    return {"generated_answer": generated_answer}
