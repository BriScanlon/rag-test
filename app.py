import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException
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

# Set up logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# Folder containing the documents
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
            existing_node["category"] = f"{existing_node['category']}, {node['category']}"
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
            new_links.append({
                "source_id": new_source_id,
                "target_id": new_target_id,
                "relation": link["relation"]
            })

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
            logging.warning(f"Skipping document {document_name}: No embeddings created.")
            continue

        all_chunks.extend([{"document_name": document_name, "chunk": chunk} for chunk in chunks])
        all_embeddings.append(embeddings)

    if not all_embeddings:
        logging.error("No valid documents found or processed.")
        raise HTTPException(status_code=404, detail="No valid documents found or processed.")

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
    
    merged_nodes, new_links = merge_duplicates(generated_answer.get("nodes", []), generated_answer.get("links", []))

    logging.debug(f"Merged nodes: {len(merged_nodes)}")
    logging.debug(f"Updated links: {len(new_links)}")

    generated_answer["nodes"] = merged_nodes
    generated_answer["links"] = new_links

    logging.debug("Process completed successfully.")
    return {"generated_answer": generated_answer}


# New endpoint for streaming text output
async def stream_text_output(user_query: str):
    rag_api_url = "http://127.0.0.1:11434/api/generate"

    prompt = "Please identify the entity, predicate, and object triples from the following text. For each triple, categorize the entity and relationship, ensuring that each node has a unique ID (numeric). The format for the nodes should be: { \"id\": <unique numeric ID>, \"name\": \"<entity_name>\", \"category\": \"<category_name>\" }. The links should be formatted as: { \"source_id\": <source_node_id>, \"target_id\": <target_node_id>, \"relation\": \"<relation_name>\" }. Please only return the following JSON object with nodes and links, nothing else to ensure there is no trailing text after the JSON object. Example output format: { \"nodes\": [{ \"id\": 1, \"name\": \"Peter Jackson\", \"category\": \"Director\" }, { \"id\": 2, \"name\": \"Orlando Bloom\", \"category\": \"Actor\" }], \"links\": [{ \"source_id\": 1, \"target_id\": 2, \"relation\": \"Directed\" }] } " + f"{user_query}"

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
                    decoded_line = line.decode('utf-8')
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


# Add uvicorn startup code
if __name__ == "__main__":
    logging.info("Starting Uvicorn server.")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
