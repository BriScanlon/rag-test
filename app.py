import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException, File, UploadFile, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chunking import chunk_text
from indexing import create_faiss_index, query_index
from sentence_transformers import SentenceTransformer
from rag_request import send_to_rag_api
import numpy as np
from process_document import process_document
import uvicorn
from pymongo import MongoClient
from datetime import datetime
import boto3
from urllib.parse import quote_plus
from hdfs import InsecureClient
from urllib.parse import urlparse
import time
from bson import ObjectId
import faiss
from vectorising import embed_chunks, query_faiss, list_vectors


def convert_objectid_to_str(data):
    """Recursively convert ObjectId instances to strings."""
    if isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data


# Set up logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.info("Logging initialized.")

logging.getLogger("pymongo").setLevel(logging.WARNING)

# Load the pre-trained embedding model for query embedding
model = SentenceTransformer("all-MiniLM-L12-v2")

# Initialize FastAPI app
app = FastAPI()


# Query request model
class SearchRequest(BaseModel):
    query: str  # The search query text
    top_k: int = 5  # Number of similar results to return


# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.info("CORS Middleware loaded")

# MongoDB setup
# Encode username and password
username = quote_plus("admin")
password = quote_plus("Th3laundry123")

# Construct the connection string
mongo_client = MongoClient(f"mongodb://{username}:{password}@192.168.4.218:27017/")
db = mongo_client["file_manager"]
files_collection = db["files"]
chunks_collection = db["chunks"]
embeddings_collection = db["embeddings"]

# HDFS client setup
hdfs_client = InsecureClient("http://192.168.4.218:9870", user="hadoop")

DOCUMENTS_FOLDER = "documents/"


# Function to load or create FAISS index
def load_or_create_faiss_index(index_path, dimension):
    index_file = os.path.join(index_path, "faiss_index.index")
    if os.path.exists(index_file):
        index = faiss.read_index(index_file)
        print("FAISS index loaded successfully.")
    else:
        index = faiss.IndexFlatL2(dimension)  # Create a new index
        print("New FAISS index created.")
    logging.debug(f"FAISS index contains {index.ntotal} vectors.")

    return index, index_file


# Pydantic model for request body (only the user query)
class DocumentQueryRequest(BaseModel):
    user_query: str  # Query for searching the documents


# Function to merge duplicate nodes and update links
def merge_duplicates(nodes, links):
    node_map = {}
    node_mapping = {}
    merged_nodes = []
    new_links = []

    # Merge nodes by name
    for node in nodes:
        if node["name"] in node_map:
            existing_node = node_map[node["name"]]
            existing_node["category"] = (
                f"{existing_node['category']}, {node['category']}"
            )
            node_mapping[node["id"]] = existing_node["id"]
        else:
            node_map[node["name"]] = node
            merged_nodes.append(node)
            node_mapping[node["id"]] = node["id"]

    # Update links to point to the merged node
    for link in links:
        new_source_id = node_mapping.get(link["source_id"])
        new_target_id = node_mapping.get(link["target_id"])
        if new_source_id and new_target_id:
            new_links.append(
                {
                    "source_id": new_source_id,
                    "target_id": new_target_id,
                    "relation": link["relation"],
                }
            )

    return merged_nodes, new_links


# FastAPI POST endpoint to process documents and query
@app.post("/process_documents/")
async def process_documents(request: DocumentQueryRequest):
    logging.debug("1. Beginning process_documents function")

    user_query = request.user_query

    if not user_query:
        logging.error("User query not provided.")
        raise HTTPException(status_code=400, detail="User query must be provided.")

    # Initialize storage for document chunks and embeddings
    all_chunks = []
    all_embeddings = []

    # Iterate over all documents in the folder
    for document_name in os.listdir(DOCUMENTS_FOLDER):
        document_path = os.path.join(DOCUMENTS_FOLDER, document_name)
        logging.debug(f"Processing document: {document_name}")

        document_text = process_document(document_path)
        if document_text is None:
            logging.warning(f"Skipping document {document_name}: Not found or empty.")
            continue

        chunks = chunk_text(document_text, chunk_size=512)
        if not chunks:
            logging.warning(f"Skipping document {document_name}: No chunks created.")
            continue

        embeddings = embed_chunks(chunks)
        if embeddings.size == 0:
            logging.warning(
                f"Skipping document {document_name}: No embeddings created."
            )
            continue

        all_chunks.extend(
            [{"document_name": document_name, "chunk": chunk} for chunk in chunks]
        )
        all_embeddings.append(embeddings)

    if not all_embeddings:
        logging.error("No valid documents found or processed.")
        raise HTTPException(
            status_code=404, detail="No valid documents found or processed."
        )

    all_embeddings = np.vstack(all_embeddings)

    try:
        logging.debug("Creating FAISS index.")
        index = create_faiss_index(all_embeddings)
    except ValueError as e:
        logging.error(f"Error creating FAISS index: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    query_embedding = model.encode([user_query])
    if query_embedding.size == 0:
        logging.error("Failed to encode user query.")
        raise HTTPException(status_code=400, detail="Failed to encode query.")

    try:
        logging.debug("Querying FAISS index.")
        result_indices = query_index(index, query_embedding)
    except ValueError as e:
        logging.error(f"Error querying FAISS index: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    result_chunks = [all_chunks[idx] for idx in result_indices]

    logging.debug("Sending data to RAG API.")
    generated_answer = send_to_rag_api(result_chunks, user_query)

    if generated_answer and generated_answer.get("response"):
        cleaned_response = generated_answer["response"].strip("```")
        generated_answer["response"] = cleaned_response

    logging.debug("2. Response received from RAG API, cleaning up response.")

    merged_nodes, new_links = merge_duplicates(
        generated_answer.get("nodes", []), generated_answer.get("links", [])
    )

    logging.debug(f"Merged nodes: {len(merged_nodes)}")
    logging.debug(f"Updated links: {len(new_links)}")

    generated_answer["nodes"] = merged_nodes
    generated_answer["links"] = new_links

    logging.debug("Process completed successfully.")
    return {"generated_answer": generated_answer}


# STEP 1: process documents
# /document endpoint
@app.post("/document")
async def upload_and_process_document(file: UploadFile = File(...)):
    logging.debug(f"1. Received file: {file.filename if file else 'No file received'}")

    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    allowed_extensions = {"pdf", "docx", "txt"}
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    logging.debug(
        f"2. {file.filename} passed file type validation. Extension: {file_extension}"
    )

    # Save original file to HDFS
    try:
        logging.debug("3. Saving original file to HDFS.")
        hdfs_path_original = f"/uploads/{file.filename}"
        webhdfs_url_original = (
            f"http://192.168.4.218:9870/webhdfs/v1{hdfs_path_original}?op=OPEN"
        )

        with hdfs_client.write(hdfs_path_original, overwrite=True) as writer:
            writer.write(file.file.read())
        logging.info(
            f"4. Original file successfully saved to HDFS at {webhdfs_url_original}"
        )

        # Save file metadata to MongoDB
        original_file_metadata = {
            "filename": file.filename,
            "upload_timestamp": datetime.utcnow(),
            "hdfs_path": webhdfs_url_original,
        }
        original_file_id = files_collection.insert_one(
            original_file_metadata
        ).inserted_id
        logging.info(
            f"5. Original file metadata saved to MongoDB with ID: {original_file_id}"
        )

    except Exception as e:
        logging.error(f"Error saving original file to HDFS: {e}")
        raise HTTPException(
            status_code=500, detail="Error saving original file to HDFS"
        )

    # Reset file pointer for processing
    file.file.seek(0)

    # Process the file to extract text and save as .txt to HDFS
    try:
        logging.debug("6. Processing the file.")
        file_content = file.file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty or unreadable")

        processed_data = process_document(file_content, file_extension)
        if not processed_data or "text" not in processed_data:
            raise HTTPException(
                status_code=500, detail="Error processing file: no content extracted"
            )

        processed_text = processed_data["text"]
        processed_filename = f"{file.filename.split('.')[0]}.txt"
        hdfs_path_processed = f"/uploads/{processed_filename}"
        webhdfs_url_processed = (
            f"http://192.168.4.218:9870/webhdfs/v1{hdfs_path_processed}?op=OPEN"
        )

        with hdfs_client.write(hdfs_path_processed, overwrite=True) as writer:
            writer.write(processed_text.encode("utf-8"))
        logging.info(f"7. Processed text file saved to HDFS at {webhdfs_url_processed}")

        processed_file_metadata = {
            "filename": processed_filename,
            "upload_timestamp": datetime.utcnow(),
            "hdfs_path": webhdfs_url_processed,
        }
        processed_file_id = files_collection.insert_one(
            processed_file_metadata
        ).inserted_id
        logging.info(
            f"8. Processed file metadata saved to MongoDB with ID: {processed_file_id}"
        )

    except Exception as e:
        logging.error(f"Error processing or saving processed file to HDFS: {e}")
        raise HTTPException(
            status_code=500, detail="Error processing or saving processed file to HDFS"
        )

    # Chunk the processed text and save chunks to MongoDB
    try:
        logging.debug("9. Chunking the processed text.")
        chunk_ids = []
        chunks = chunk_text(
            processed_text, file_id=processed_file_id
        )  # Pass file_id to chunk_text

        for index, chunk in enumerate(chunks):
            chunk_metadata = {
                "file_id": processed_file_id,
                "chunk_index": index,
                "chunk_text": chunk,
                "created_at": datetime.utcnow(),
            }
            chunk_id = chunks_collection.insert_one(chunk_metadata).inserted_id
            chunk_ids.append(str(chunk_id))
            logging.info(f"Chunk {index} saved to MongoDB with ID: {chunk_id}")

        logging.info(f"10. Total {len(chunk_ids)} chunks saved to MongoDB.")

    except Exception as e:
        logging.error(f"Error during chunking or saving chunks to MongoDB: {e}")
        raise HTTPException(
            status_code=500, detail="Error during chunking or saving chunks"
        )

    # Vectorize chunks and save embeddings
    try:
        # Pass only the chunk text to the vectorization function
        chunk_texts = [
            chunk["chunk_text"]
            for chunk in chunks_collection.find({"file_id": processed_file_id})
        ]

        # Vectorize the chunks and save them to FAISS
        vector_ids = embed_chunks(chunk_texts, processed_file_id)

        # Log the successful storage of embeddings in FAISS
        logging.info(f"12. Vector embeddings saved in FAISS with indices: {vector_ids}")

    except Exception as e:
        logging.error(f"Error during vectorization or saving embeddings: {e}")
        raise HTTPException(
            status_code=500, detail="Error during vectorization or saving embeddings"
        )

    # Return response
    response = {
        "status": "success",
        "original_file": {
            "id": str(original_file_id),
            "filename": original_file_metadata["filename"],
            "hdfs_path": original_file_metadata["hdfs_path"],
            "upload_timestamp": original_file_metadata["upload_timestamp"],
        },
        "processed_file": {
            "id": str(processed_file_id),
            "filename": processed_file_metadata["filename"],
            "hdfs_path": processed_file_metadata["hdfs_path"],
            "upload_timestamp": processed_file_metadata["upload_timestamp"],
        },
        "chunks": {
            "total_chunks": len(chunk_ids),
            "chunk_ids": chunk_ids,
        },
        "vectorization": {
            "status": "completed",
            "vector_ids": vector_ids,  # Ensure vector_ids is a list of serializable values
        },
    }

    # Convert all ObjectIds to strings
    return convert_objectid_to_str(response)


# New endpoint for streaming text output
async def stream_text_output(user_query: str):
    rag_api_url = "http://127.0.0.1:11434/api/generate"

    prompt = (
        'Please identify the entity, predicate, and object triples from the following text. For each triple, categorize the entity and relationship, ensuring that each node has a unique ID (numeric). The format for the nodes should be: { "id": <unique numeric ID>, "name": "<entity_name>", "category": "<category_name>" }. The links should be formatted as: { "source_id": <source_node_id>, "target_id": <target_node_id>, "relation": "<relation_name>" }. Please only return the following JSON object with nodes and links, nothing else to ensure there is no trailing text after the JSON object. Example output format: { "nodes": [{ "id": 1, "name": "Peter Jackson", "category": "Director" }, { "id": 2, "name": "Orlando Bloom", "category": "Actor" }], "links": [{ "source_id": 1, "target_id": 2, "relation": "Directed" }] } '
        + f"{user_query}"
    )

    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": True,  # Enable streaming
        "system": "Your task is to provide a JSON object in response to the prompt",
        "top_p": 0.7,
    }

    with requests.post(rag_api_url, json=payload, stream=True) as response:
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    try:
                        json_response = json.loads(decoded_line)
                        if "response" in json_response:
                            yield json_response["response"] + "\n"
                    except json.JSONDecodeError:
                        continue
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to RAG API")


# FastAPI POST endpoint for streaming the text output
@app.post("/stream_text_output/")
async def stream_text_output_endpoint(request: DocumentQueryRequest):
    user_query = request.user_query
    if not user_query:
        raise HTTPException(status_code=400, detail="User query must be provided.")

    return StreamingResponse(stream_text_output(user_query), media_type="text/plain")


@app.post("/files/")
async def upload_file(file: UploadFile = File(...)):
    logging.info(f"Received file: {file.filename if file else 'No file received'}")

    hdfs_client = InsecureClient("http://192.168.4.218:9870", user="hadoop")

    if file is None:
        logging.error("No file received in the request.")
        raise HTTPException(status_code=400, detail="File is required")

    logging.debug(f"Received file: {file.filename}")
    """
    Uploads a .pdf or .docx file, stores it in MinIO, and indexes metadata in MongoDB.
    """
    if not file.filename.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(
            status_code=400, detail="Only .pdf and .docx files are allowed"
        )

    # Check for duplicate filenames in MongoDB
    existing_file = files_collection.find_one({"filename": file.filename})
    if existing_file:
        raise HTTPException(status_code=400, detail="File already exists")

    try:
        # Define HDFS path for the file
        hdfs_path = f"/uploads/{file.filename}"
        webhdfs_url = f"http://192.168.4.218:9870/webhdfs/v1{hdfs_path}?op=OPEN"

        # Save to HDFS
        with hdfs_client.write(hdfs_path, overwrite=True) as writer:
            writer.write(file.file.read())

        # Save metadata in MongoDB
        file_metadata = {
            "filename": file.filename,
            "upload_timestamp": datetime.utcnow(),
            "hdfs_path": webhdfs_url,  # Save the WebHDFS URL instead of just the path
        }
        files_collection.insert_one(file_metadata)

        return {"message": "File uploaded successfully", "hdfs_path": webhdfs_url}

    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading file")


@app.get("/files/")
async def list_files():
    # Fetch all files from the `files` collection
    listed_files = list(files_collection.find())

    # For each file, check if it has been chunked
    for file in listed_files:
        file_id = file["_id"]
        file["_id"] = str(file_id)  # Convert ObjectId to string for JSON serialization

        # Check if there are any chunks with the matching file_id
        chunk_exists = db["chunks"].find_one({"file_id": file_id}) is not None
        file["chunked"] = chunk_exists  # Add chunked status as a boolean

    return {"files": convert_objectid_to_str(listed_files)}


@app.get("/vectors/")
async def list_vectors_endpoint(vector_ids: list[int] = Query(None)):
    try:
        logging.debug(f"API called to list vectors with IDs: {vector_ids}")
        vectors = list_vectors(vector_ids)
        logging.debug(f"Vectors retrieved: {len(vectors)}")
        return {"total_vectors": len(vectors), "vectors": vectors}
    except ValueError as e:
        logging.error(f"ValueError in /vectors/ endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in /vectors/ endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")


@app.post("/search/")
async def search_similar_chunks(request: SearchRequest):
    """
    Search the FAISS index for similar chunks to the input query.
    """
    logging.debug(f"Search query received: {request.query}, Top-K: {request.top_k}")
    results = query_faiss(request.query, request.top_k)

    if not results:
        raise HTTPException(status_code=404, detail="No similar chunks found")

    return {"query": request.query, "top_k": request.top_k, "results": results}

class RagApiRequest(BaseModel):
    document_chunks: str  # Accept a string for document chunks
    user_query: str       # Accept a string for the user query
    
    
@app.post("/rag_api/")
async def call_rag_api(request: RagApiRequest):
    """
    Endpoint to send document chunks and a user query to the RAG API.
    """
    try:
        # Extract data from the request
        document_chunks = request.document_chunks
        user_query = request.user_query

        # Call the function and process the response
        response = send_to_rag_api(document_chunks, user_query)

        return {"status": "success", "response": response}
    except HTTPException as e:
        logging.error(f"HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while processing the request."
        )


@app.options("/{path:path}")
async def preflight_handler():
    return {}


# Add uvicorn startup code
if __name__ == "__main__":
    logging.info("Starting Uvicorn server.")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
