# © 2024 Brian Scanlon. All rights reserved.
from datetime import datetime
from urllib.parse import quote_plus
from pymongo import MongoClient
import logging

# MongoDB setup
# Encode username and password
username = quote_plus("admin")
password = quote_plus("Th3laundry123")

# Construct the connection string
mongo_client = MongoClient(f"mongodb://{username}:{password}@192.168.4.218:27017/")
db = mongo_client["file_manager"]
chunks_collection = db["chunks"]

def chunk_text(text, file_id, chunk_size=512, metadata=None):
    """
    Splits text into chunks of specified size and saves each chunk with metadata to MongoDB.

    Args:
        text (str): The original text to be chunked.
        file_id (ObjectId): The ID of the original file in the `files` collection.
        chunk_size (int): The size of each chunk in words (default: 512).
        metadata (dict): Additional metadata (e.g., page_number, section_title).

    Returns:
        list: A list of inserted MongoDB document IDs for the chunks.
    """
    if not text or len(text.strip()) == 0:
        logging.warning("The provided text is empty. No chunks to process.")
        return []

    words = text.split()
    total_words = len(words)
    inserted_chunk_ids = []

    for i in range(0, total_words, chunk_size):
        chunk_text = ' '.join(words[i:i+chunk_size])
        start_word_index = i
        end_word_index = min(i + chunk_size, total_words)

        # Prepare the chunk document
        chunk_document = {
            "file_id": file_id,                      # Link to the original file
            "chunk_index": i // chunk_size,          # Sequential chunk index
            "chunk_text": chunk_text,                # The actual chunk text
            "start_word_index": start_word_index,    # Start word position
            "end_word_index": end_word_index,        # End word position
            "created_at": datetime.utcnow(),         # Timestamp for creation
            "metadata": metadata or {}              # Additional metadata
        }

        # Save the chunk document to MongoDB
        result = chunks_collection.insert_one(chunk_document)
        inserted_chunk_ids.append(result.inserted_id)

        logging.info(f"Chunk {chunk_document['chunk_index']} saved to MongoDB.")

    logging.info(f"Total {len(inserted_chunk_ids)} chunks saved.")
    return inserted_chunk_ids
