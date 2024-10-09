# indexing.py

import faiss
import numpy as np

def create_faiss_index(embeddings):
    """Creates a FAISS index for embeddings."""
    if embeddings.shape[0] == 0:  # Check if embeddings are empty
        raise ValueError("No embeddings found to create FAISS index.")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    return index

def query_index(index, query_embedding, top_k=6):
    """Queries the FAISS index to find top_k similar embeddings."""
    if query_embedding.size == 0:  # Check if query embedding is empty
        raise ValueError("Failed to encode query.")
    
    distances, indices = index.search(np.array(query_embedding), top_k)
    if len(indices[0]) == 0:  # Handle no results case
        raise ValueError("No matching results found.")
    return indices[0]
