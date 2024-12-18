import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chunking import chunk_text
from vectorising import embed_chunks
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


# Set up logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Load the pre-trained embedding model for query embedding
model = SentenceTransformer("all-MiniLM-L12-v2")

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

# MongoDB setup
# Encode username and password
username = quote_plus("admin")
password = quote_plus("Th3laundry123")

# Construct the connection string
mongo_client = MongoClient(f"mongodb://{username}:{password}@192.168.4.218:27017/")
db = mongo_client["file_manager"]
files_collection = db["files"]

DOCUMENTS_FOLDER = "documents/"


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
@app.post("/document")
async def upload_and_process_document(file: UploadFile = File(...)):
    logging.debug(f"1. Received file: {file.filename if file else 'No file received'}")

    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    # Validate the file type
    allowed_extensions = {"pdf", "docx", "txt"}
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    logging.debug(f"2. {file} passed file type validation. {file_extension}")

    # Save original file to HDFS
    try:
        logging.debug("3. Saving original file to HDFS.")
        hdfs_client = InsecureClient("http://192.168.4.218:9870", user="hadoop")
        hdfs_path_original = f"/uploads/{file.filename}"
        webhdfs_url_original = (
            f"http://192.168.4.218:9870/webhdfs/v1{hdfs_path_original}?op=OPEN"
        )

        # Write to HDFS
        with hdfs_client.write(hdfs_path_original, overwrite=True) as writer:
            writer.write(file.file.read())
        logging.info(
            f"4. Original file successfully saved to HDFS at {webhdfs_url_original}"
        )

        # Save original file metadata in MongoDB
        original_file_metadata = {
            "filename": file.filename,
            "upload_timestamp": datetime.utcnow(),
            "hdfs_path": webhdfs_url_original,
        }
        files_collection.insert_one(original_file_metadata)
        logging.info(f"5. Saved to mongodb")

    except Exception as e:
        logging.error(f"Error saving original file to HDFS: {e}")
        raise HTTPException(
            status_code=500, detail="Error saving original file to HDFS"
        )

    # Reset file pointer for processing
    file.file.seek(0)

    # Process the file and save as .txt to HDFS
    try:
        logging.debug("6. Processing the file.")
        # Read the file content
        file_content = file.file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty or unreadable")

        try:
            # Convert content to a string for processing
            processed_data = process_document(file_content, file_extension)
        except Exception as e:
            logging.error(f"Error during file processing: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing the file")

        if not processed_data or "text" not in processed_data:
            raise Exception("Processing failed or returned no content.")

        # Save processed text as .txt file to HDFS
        processed_filename = f"{file.filename.split('.')[0]}.txt"
        hdfs_path_processed = f"/uploads/{processed_filename}"
        webhdfs_url_processed = (
            f"http://192.168.4.218:9870/webhdfs/v1{hdfs_path_processed}?op=OPEN"
        )

        with hdfs_client.write(hdfs_path_processed, overwrite=True) as writer:
            writer.write(processed_data["text"].encode("utf-8"))
        logging.info(
            f"7. Processed file successfully saved to HDFS at {webhdfs_url_processed}"
        )

        # Save processed file metadata in MongoDB
        processed_file_metadata = {
            "filename": processed_filename,
            "upload_timestamp": datetime.utcnow(),
            "hdfs_path": webhdfs_url_processed,
        }
        result = files_collection.insert_one(processed_file_metadata)

        # Check for the presence of "text" in the processed_data
        if not processed_data or "text" not in processed_data:
            raise Exception("Processing failed or returned no content.")

        # Extract text for further processing
        text_content = processed_data["text"]  # Access the "text" key directly
        if not isinstance(text_content, str):
            raise Exception("Processed text content is not a string.")

        # Chunk the text and save metadata
        chunk_ids = chunk_text(text_content, result.inserted_id)

        print(f"Chunk IDs: {chunk_ids}")

    except Exception as e:
        logging.error(f"Error processing or saving processed file to HDFS: {e}")
        raise HTTPException(
            status_code=500, detail="Error processing or saving processed file to HDFS"
        )

    return {
        "status": "success",
        "original_file": {
            "filename": original_file_metadata["filename"],
            "hdfs_path": original_file_metadata["hdfs_path"],
            "upload_timestamp": original_file_metadata["upload_timestamp"],
        },
        "processed_file": {
            "filename": processed_file_metadata["filename"],
            "hdfs_path": processed_file_metadata["hdfs_path"],
            "upload_timestamp": processed_file_metadata["upload_timestamp"],
        },
        "chunks": {
            "chunk_ids": [
                str(chunk_id) for chunk_id in chunk_ids
            ],  # Convert ObjectId to string
        },
    }


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

    return {"files": listed_files}


# Add uvicorn startup code
if __name__ == "__main__":
    logging.info("Starting Uvicorn server.")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
