import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from pymongo import MongoClient
from bson import ObjectId

# Load the pre-trained embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Setup
client = MongoClient("mongodb://admin:Th3laundry123@192.168.4.218:27017/")
db = client["file_manager"]
files_collection = db["files"]
embeddings_collection = db["embeddings"]

# FAISS Index Path (Persistent Storage)
FAISS_INDEX_PATH = "faiss_index"

# Ensure the directory exists for persistent storage
if not os.path.exists(FAISS_INDEX_PATH):
    os.makedirs(FAISS_INDEX_PATH)


def load_or_create_faiss_index(dimension, index_path):
    """Load or create a FAISS index with persistent storage."""
    index_file = os.path.join(index_path, "faiss_index.index")
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
        print("FAISS index loaded successfully.")
    else:
        index = faiss.IndexFlatL2(dimension)  # L2 distance index
        print("New FAISS index created.")
    return index, index_file


# Load or create FAISS index
embedding_dim = 384  # Dimension for MiniLM-L6-v2
faiss_index, faiss_index_file = load_or_create_faiss_index(
    embedding_dim, FAISS_INDEX_PATH
)


def embed_chunks_and_save_to_faiss(chunks, file_id):
    """Embeds text chunks, saves them to FAISS and MongoDB."""
    if not chunks:
        return []

    embeddings = []
    chunk_metadata = []

    # Batch process with progress feedback
    for i in tqdm(range(0, len(chunks), 16), desc="Embedding chunks"):
        batch = chunks[i : i + 16]
        batch_embeddings = model.encode(batch)
        embeddings.extend(batch_embeddings)

        # Save chunk metadata to MongoDB
        for j, embedding in enumerate(batch_embeddings):
            # Ensure file_id is already an ObjectId
            if not isinstance(file_id, ObjectId):
                file_id = ObjectId(file_id)

            metadata = {
                "file_id": file_id,
                "chunk_index": i + j,
                "embedding": embedding.tolist(),  # Convert numpy array to list
            }
            result = embeddings_collection.insert_one(metadata)
            chunk_metadata.append(result.inserted_id)

    # Add embeddings to FAISS index
    embeddings_np = np.array(embeddings, dtype="float32")
    faiss_index.add(embeddings_np)

    # Save FAISS index to disk
    faiss.write_index(faiss_index, faiss_index_file)

    return chunk_metadata
