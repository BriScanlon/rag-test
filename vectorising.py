# vectorization.py
# © 2024 Brian Scanlon. All rights reserved.

from sentence_transformers import SentenceTransformer
import numpy as np

# Load the pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """Embeds text chunks using the pre-trained model."""
    if not chunks:
        return np.array([])  # Return empty array if no chunks
    return model.encode(chunks)
