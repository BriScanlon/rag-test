# © 2024 Brian Scanlon. All rights reserved.

import requests
from fastapi import HTTPException

# Function to send chunks to the RAG LLM API
def send_to_rag_api(document_chunks, user_query):
    print(f"Document Chunks to be sent to Ollama: {document_chunks} \nOriginal Prompt: {user_query}")
    
    rag_api_url = "http://127.0.0.1:11434/api/generate"  # RAG LLM API endpoint
    
    prompt = (
        '''Take the chunks provided below and create a single paragraph summarising the information given
        '''
        f"{user_query} This is the text to use: {document_chunks}"
    )
    
    payload = {
        "model": "llama2:13b",
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(rag_api_url, json=payload)
    print(f"Response from LLM: {response.json()}")
    
    if response.status_code == 200:
        return response.json()  # Return the generated answer
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to RAG API")
