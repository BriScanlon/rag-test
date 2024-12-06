import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from bson import ObjectId
import logging

# Configure Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "vectorising.log"),
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Constants
MODEL_NAME = "all-MiniLM-L12-v2"
MONGO_URI = "mongodb://admin:Th3laundry123@192.168.4.218:27017/"
FAISS_INDEX_PATH = "faiss_index"
FAISS_COUNTER_FILE = os.path.join(FAISS_INDEX_PATH, "faiss_id_counter.txt")
FAISS_INDEX_FILE = os.path.join(FAISS_INDEX_PATH, "faiss_index.index")
NUM_CLUSTERS = 128
EMBEDDING_DIM = 384

# Ensure FAISS index directory exists
os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client["file_manager"]
embeddings_collection = db["embeddings"]

# Load SentenceTransformer Model
model = SentenceTransformer(MODEL_NAME)


# Utility Functions
def load_faiss_id_counter():
    """Load FAISS ID counter from file, or initialize it."""
    if os.path.exists(FAISS_COUNTER_FILE):
        with open(FAISS_COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    return 0


def save_faiss_id_counter(counter):
    """Save the FAISS ID counter to a file."""
    with open(FAISS_COUNTER_FILE, "w") as f:
        f.write(str(counter))


def create_new_faiss_index():
    """Create a new FAISS IndexIVFFlat."""
    quantizer = faiss.IndexFlatL2(EMBEDDING_DIM)
    index = faiss.IndexIVFFlat(quantizer, EMBEDDING_DIM, NUM_CLUSTERS, faiss.METRIC_L2)
    index = faiss.IndexIDMap(index)
    logging.info("Created a new FAISS index.")
    return index


def initialize_faiss_index():
    """Initialize and train the FAISS index."""
    global faiss_index

    if os.path.exists(FAISS_INDEX_FILE):
        faiss_index = faiss.read_index(FAISS_INDEX_FILE)
        logging.info(f"Loaded existing FAISS index with {faiss_index.ntotal} vectors.")
    else:
        logging.info("No FAISS index found. Creating and training a new index.")
        faiss_index = create_new_faiss_index()
        # Generate synthetic data for training
        synthetic_data = np.random.rand(NUM_CLUSTERS * 40, EMBEDDING_DIM).astype(
            "float32"
        )
        faiss_index.train(synthetic_data)
        faiss.write_index(faiss_index, FAISS_INDEX_FILE)
        # Log FAISS index details
        logging.debug(f"FAISS index loaded with {faiss_index.ntotal} vectors.")
        logging.info("New FAISS index trained and saved.")

    logging.debug(f"FAISS index type: {type(faiss_index)}")
    logging.debug(f"Base FAISS index type: {type(faiss_index.index)}")


# Load FAISS index on import
initialize_faiss_index()


# Functions for Embedding, Listing, and Searching
def embed_chunks(chunks, file_id):
    """Embed text chunks and save embeddings to FAISS."""
    global faiss_index
    faiss_id_counter = load_faiss_id_counter()

    if not chunks:
        logging.warning("No chunks provided for embedding.")
        return []

    embeddings = model.encode(chunks)
    logging.debug(
        f"Generated embeddings with shape: {embeddings.shape}, dtype: {embeddings.dtype}"
    )
    faiss_ids = []

    for i, embedding in enumerate(embeddings):
        faiss_id = faiss_id_counter
        faiss_ids.append(faiss_id)
        embeddings_collection.insert_one(
            {
                "file_id": file_id,
                "faiss_id": faiss_id,
                "chunk_index": i,
                "chunk_text": chunks[i],
                "embedding": embedding.tolist(),
            }
        )
        faiss_id_counter += 1

    # Add to FAISS index
    try:
        faiss_index.add_with_ids(
            np.array(embeddings, dtype="float32"), np.array(faiss_ids, dtype="int64")
        )
        faiss.write_index(faiss_index, FAISS_INDEX_FILE)
        save_faiss_id_counter(faiss_id_counter)
        logging.debug(
            f"Added embeddings to FAISS. Total vectors now: {faiss_index.ntotal}"
        )
        logging.info(f"Added {len(embeddings)} embeddings to FAISS index.")
    except Exception as e:
        logging.error(f"Error adding embeddings to FAISS: {e}")
        raise ValueError("Failed to add embeddings to FAISS index.")

    return faiss_ids


def list_vectors(vector_ids=None):
    """
    Retrieve vectors from FAISS or MongoDB if FAISS does not support reconstruction.
    """
    try:
        total_vectors = faiss_index.ntotal
        logging.debug(f"FAISS index total vectors: {total_vectors}")

        if vector_ids is not None:
            # Validate vector IDs
            if max(vector_ids) >= total_vectors:
                raise ValueError(
                    f"Invalid vector IDs. Maximum valid ID is {total_vectors - 1}."
                )

            # Attempt to reconstruct vectors from FAISS if supported
            vectors = []
            for vector_id in vector_ids:
                try:
                    reconstructed_vector = faiss_index.reconstruct(vector_id)
                    vectors.append(reconstructed_vector.tolist())
                except RuntimeError as e:
                    logging.warning(f"FAISS reconstruct not supported: {e}")
                    break  # Fallback to MongoDB if FAISS fails

            # If FAISS reconstruction is not supported, fallback to MongoDB
            if len(vectors) < len(vector_ids):
                mongo_vectors = list(
                    embeddings_collection.find(
                        {"faiss_id": {"$in": vector_ids}},
                        {"_id": 0, "embedding": 1},
                    )
                )
                vectors = [v["embedding"] for v in mongo_vectors]

            return {"total_vectors": len(vectors), "vectors": vectors}

        # If no specific IDs are provided, retrieve all vectors
        vectors = []
        for i in range(total_vectors):
            try:
                reconstructed_vector = faiss_index.reconstruct(i)
                vectors.append(reconstructed_vector.tolist())
            except RuntimeError as e:
                logging.warning(f"FAISS reconstruct not supported: {e}")
                # Fallback to MongoDB for all vectors
                mongo_vectors = list(
                    embeddings_collection.find({}, {"_id": 0, "embedding": 1})
                )
                vectors = [v["embedding"] for v in mongo_vectors]
                break

        return {"total_vectors": len(vectors), "vectors": vectors}

    except Exception as e:
        logging.error(f"Error in list_vectors: {str(e)}")
        raise HTTPException(status_code=500, detail="Error listing vectors")


def query_faiss(query, top_k):
    """
    Query FAISS for the top_k most similar embeddings to the given query.
    """
    try:
        query_vector = model.encode([query])
        distances, indices = faiss_index.search(query_vector, top_k)
        logging.debug(f"Query result indices: {indices}, distances: {distances}")

        # Collect metadata for each result
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            # Fetch metadata from MongoDB
            chunk_data = embeddings_collection.find_one({"faiss_id": idx})
            if chunk_data:
                results.append(
                    {
                        "faiss_id": idx,
                        "distance": float(distance),
                        "chunk_text": chunk_data.get("chunk_text", ""),
                        "file_id": str(chunk_data.get("file_id", "")),
                        "chunk_index": chunk_data.get("chunk_index", -1),
                    }
                )
        return results

    except Exception as e:
        logging.error(f"Error querying FAISS: {str(e)}")
        raise HTTPException(status_code=500, detail="Error querying FAISS")


# Expose for Import
__all__ = ["embed_chunks", "query_faiss", "list_vectors", "faiss_index"]
