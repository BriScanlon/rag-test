# © 2024 Brian Scanlon. All rights reserved.

import requests
from fastapi import HTTPException


# Function to send chunks to the RAG LLM API
def send_to_rag_api(document_chunks, user_query):
    print(
        f"Document Chunks to be sent to Ollama: {document_chunks} \nOriginal Prompt: {user_query}"
    )

    rag_api_url = "http://127.0.0.1:11434/api/generate"  # RAG LLM API endpoint

    prompt = (
        """
       You will be provided with a natural language prompt. Your task is to perform the following steps:

1. **Identify Entities**: Extract key objects or actors mentioned in the prompt.
2. **Identify Attributes**: For each entity, identify and list its relevant attributes and their values.
3. **Identify Relationships**: Define relationships between entities, specifying the type of relationship, the source entity, and the target entity.

The output must be structured in a well-formed JSON object using the following format:

```json
{
  "entities": [
    {
      "entity": "<entity_name>",
      "attributes": [
        {
          "attribute_name": "<attribute_name>",
          "value": "<value>"
        }
      ]
    }
  ],
  "relationships": [
    {
      "source_entity": "<source_entity>",
      "target_entity": "<target_entity>",
      "relationship_type": "<relationship_type>"
    }
  ]
}
Example Input:
"A dog chased a cat across the yard."

Example Output:
json
Copy code
{
  "entities": [
    {
      "entity": "dog",
      "attributes": []
    },
    {
      "entity": "cat",
      "attributes": []
    },
    {
      "entity": "yard",
      "attributes": []
    }
  ],
  "relationships": [
    {
      "source_entity": "dog",
      "target_entity": "cat",
      "relationship_type": "chased"
    },
    {
      "source_entity": "chase",
      "target_entity": "yard",
      "relationship_type": "location"
    }
  ]
}
Ensure that:

The JSON object is valid and well-formed.
All relevant entities, attributes, and relationships are extracted.
The output format is consistent for every prompt.
        """
        f"{user_query} This is the text to use: {document_chunks}"
    )

    payload = {"model": "llama2:7b", "prompt": prompt, "stream": False}

    response = requests.post(rag_api_url, json=payload)
    print(f"Response from LLM: {response.json()}")

    if response.status_code == 200:
        return response.json()  # Return the generated answer
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to RAG API")
