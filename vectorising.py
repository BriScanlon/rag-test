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

# Persistent FAISS Index Settings
FAISS_INDEX_PATH = "faiss_index"
FAISS_COUNTER_FILE = os.path.join(FAISS_INDEX_PATH, "faiss_id_counter.txt")

# Ensure the directory exists for persistent storage
if not os.path.exists(FAISS_INDEX_PATH):
    os.makedirs(FAISS_INDEX_PATH)


def load_faiss_id_counter():
    """Load FAISS ID counter from a file, or initialize it if not found."""
    if os.path.exists(FAISS_COUNTER_FILE):
        with open(FAISS_COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    return 0  # Default to 0 if the file doesn't exist


def save_faiss_id_counter(counter):
    """Persist the FAISS ID counter to a file."""
    with open(FAISS_COUNTER_FILE, "w") as f:
        f.write(str(counter))


def load_or_create_faiss_index(dimension, index_path):
    """Load or create a FAISS index with persistent storage."""
    index_file = os.path.join(index_path, "faiss_index.index")
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
        index = faiss.IndexIDMap(index)  # Wrap it with IDMap for ID support
        print("FAISS index loaded successfully.")
    else:
        base_index = faiss.IndexFlatL2(dimension)  # L2 distance index
        index = faiss.IndexIDMap(base_index)  # Wrap with IDMap for ID support
        print("New FAISS index created.")
    return index, index_file


# Load FAISS index and ID counter
embedding_dim = 384  # Dimension for MiniLM-L6-v2
faiss_index, faiss_index_file = load_or_create_faiss_index(
    embedding_dim, FAISS_INDEX_PATH
)
faiss_id_counter = load_faiss_id_counter()


def embed_chunks_and_save_to_faiss(chunks, file_id):
    """Embeds text chunks, saves them to FAISS and MongoDB."""
    global faiss_id_counter  # Ensure counter persists across function calls
    if not chunks:
        return []

    embeddings = []
    chunk_metadata = []
    faiss_ids = []  # Track IDs for FAISS

    # Batch process with progress feedback
    for i in tqdm(range(0, len(chunks), 16), desc="Embedding chunks"):
        batch = chunks[i : i + 16]
        batch_embeddings = model.encode(batch)
        embeddings.extend(batch_embeddings)

        # Save chunk metadata to MongoDB
        for j, embedding in enumerate(batch_embeddings):
            faiss_ids.append(faiss_id_counter)  # Assign unique FAISS ID
            faiss_id_counter += 1  # Increment counter for next ID

            # Ensure file_id is already an ObjectId
            if not isinstance(file_id, ObjectId):
                file_id = ObjectId(file_id)

            metadata = {
                "file_id": file_id,
                "chunk_index": i + j,
                "faiss_id": faiss_ids[-1],  # Use the current FAISS ID
                "chunk_text": batch[j],  # Save the chunk text for reference
                "embedding": embedding.tolist(),  # Convert numpy array to list
            }
            result = embeddings_collection.insert_one(metadata)
            chunk_metadata.append(result.inserted_id)

    # Add embeddings to FAISS index with IDs
    embeddings_np = np.array(embeddings, dtype="float32")
    faiss_ids_np = np.array(faiss_ids, dtype="int64")  # FAISS requires int64 IDs
    faiss_index.add_with_ids(embeddings_np, faiss_ids_np)

    # Save FAISS index and counter to disk
    faiss.write_index(faiss_index, faiss_index_file)
    save_faiss_id_counter(faiss_id_counter)

    return chunk_metadata
