import os
import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Load the pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize FastAPI app
app = FastAPI()

# Folder containing the documents
DOCUMENTS_FOLDER = 'documents/'

# Pydantic model for request body
class DocumentQueryRequest(BaseModel):
    document_name: str  # Name of the document to search in
    user_query: str  # Query for searching the document

# Function to load the document
def load_document(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return None

# Function to split text into smaller chunks
def chunk_text(text, chunk_size=512):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# Function to embed text chunks using the model
def embed_chunks(chunks):
    return model.encode(chunks)

# Function to create and query FAISS index
def create_faiss_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    return index

def query_index(index, query, top_k=4):
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), top_k)
    return indices[0]

# FastAPI POST endpoint to process document and query
@app.post("/process_document/")
async def process_document(request: DocumentQueryRequest):
    # Get document name and user query from the request body
    document_name = request.document_name
    user_query = request.user_query

    if not document_name or not user_query:
        raise HTTPException(status_code=400, detail="Both document name and user query must be provided.")
    
    # Construct document path
    document_path = os.path.join(DOCUMENTS_FOLDER, document_name)
    
    # Load the document
    document_text = load_document(document_path)
    if document_text is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found.")
    
    # Split document into chunks
    chunks = chunk_text(document_text, chunk_size=512)

    # Embed each chunk
    embeddings = embed_chunks(chunks)

    # Create FAISS index for similarity search
    index = create_faiss_index(embeddings)

    # Query the index
    result_indices = query_index(index, user_query)

    # Retrieve the top matching chunks
    result_chunks = [{"document_name": document_name, "chunk": chunks[idx]} for idx in result_indices]

    return {"top_matching_chunks": result_chunks}

