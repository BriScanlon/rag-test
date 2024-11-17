import requests
from fastapi import HTTPException

# Function to send chunks to the RAG LLM API
def send_to_rag_api(document_chunks, user_query):
    print(
        f"Document Chunks to be sent to Ollama: {document_chunks} \nOriginal Prompt: {user_query}"
    )

    rag_api_url = "http://127.0.0.1:11434/api/generate"  # RAG LLM API endpoint

    prompt = ("Take the following text and identify the entity, predicate, and object triples. For each of these triples, categorize them into the main originating entity that the text is discussing. Define the category of the relationship between the predicate and object. If an entity is repeated, ensure it is only included once. \n\nThe output should be a JSON object structured for use in Apache ECharts for node graphs. Each entity and object should be defined as nodes, and the relationships between them should be represented as links. The categories should be defined for each relationship to allow styling with different colors.\n\nOnly output the JSON object containing the nodes and links; no other text should be included in the response.\n\nFormat the JSON as follows:\n{\n  \"nodes\": [\n    {\n      \"id\": \"entity1\",\n      \"category\": \"category1\"\n    },\n    {\n      \"id\": \"entity2\",\n      \"category\": \"category2\"\n    },\n    ...\n  ],\n  \"links\": [\n    {\n      \"source\": \"entity1\",\n      \"target\": \"entity2\",\n      \"category\": \"relationship_category\"\n    },\n    ...\n  ]\n}\n\n "f"{user_query}"
    )

    payload = {"model": "llama3.2", "prompt": prompt, "stream": False, "system": "Your task is to provide a json object in response to the prompt", "top_p": 0.7,}

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
