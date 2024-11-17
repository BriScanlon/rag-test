import requests
from fastapi import HTTPException


# Function to send chunks to the RAG LLM API
def send_to_rag_api(document_chunks, user_query):
    print(
        f"Document Chunks to be sent to Ollama: {document_chunks} \nOriginal Prompt: {user_query}"
    )

    rag_api_url = "http://127.0.0.1:11434/api/generate"  # RAG LLM API endpoint

    prompt = "Please identify the entity, predicate, and object triples from the following text. For each triple, categorize the entity and relationship, ensuring that each node has a unique ID (numeric). The format for the nodes should be: { \"id\": <unique numeric ID>, \"name\": \"<entity_name>\", \"category\": \"<category_name>\" }. The links should be formatted as: { \"source_id\": <source_node_id>, \"target_id\": <target_node_id>, \"relation\": \"<relation_name>\" }. Please only return the following JSON object with nodes and links, nothing else to ensure there is no trailing text after the JSON object. Example output format: { \"nodes\": [{ \"id\": 1, \"name\": \"Peter Jackson\", \"category\": \"Director\" }, { \"id\": 2, \"name\": \"Orlando Bloom\", \"category\": \"Actor\" }], \"links\": [{ \"source_id\": 1, \"target_id\": 2, \"relation\": \"Directed\" }] } " + f"{user_query}"

    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False,
        "system": "Your task is to provide a json object in response to the prompt",
        "top_p": 0.7,
    }

    response = requests.post(rag_api_url, json=payload)
    print(f"Response from LLM: {response.json()}")

    if response.status_code == 200:
        result = response.json()
        # Clean ticks from the response
        if result.get("response"):
            result["response"] = result["response"].strip("```")
        return result  # Return the generated answer without backticks
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to RAG API")
