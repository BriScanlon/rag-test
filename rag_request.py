import requests
from fastapi import HTTPException


# Function to send chunks to the RAG LLM API
def send_to_rag_api(document_chunks, user_query):
    print(
        f"Document Chunks to be sent to Ollama: {document_chunks} \nOriginal Prompt: {user_query}"
    )

    rag_api_url = "http://127.0.0.1:11434/api/generate"  # RAG LLM API endpoint

    prompt = f"""
    Analyze the following text to create a comprehensive report that identifies key components, root causes, failure modes, and connections across the information provided. The report must include the following sections:

    1. **Executive Summary**:  
      Provide a brief, high-level summary of the findings for non-technical stakeholders, highlighting key conclusions and their relevance.

    2. **Root Cause Analysis**:  
      Identify and explain the fundamental issues or failure modes discussed in the provided information. If assumptions are made due to incomplete data, clearly outline these assumptions.

    3. **Component Analysis and Interconnections**:  
      Discuss the specific components or issues mentioned, including their relationships and potential cascading effects. Where applicable, include links between issues to provide a holistic understanding of the system or process.

    4. **Discussion**:  
      Offer a detailed technical analysis that explores the implications of the findings, connects the dots across different pieces of information, and contextualizes the issues within the broader system.

    5. **Limitations and Unanswered Questions**:  
      Clearly state any areas where the information is insufficient to provide a complete analysis. If unable to address the original query, explain why and provide suggestions for additional information that would enable a more thorough response.

    6. **Recommendations (if applicable)**:  
      If the analysis points to actionable insights or solutions, include specific recommendations. Otherwise, omit this section.

    **Formatting Requirements**:
    - Use clear, structured sections with appropriate headings.
    - Prioritize technical depth and clarity for a knowledgeable audience.
    - When making assumptions, explicitly label them as such.

    **Additional Guidelines**:
    - Ensure the response is verbose and leverages all the provided information.
    - If connections between issues are identified, emphasize them and explain their significance.
    - Do not generate additional content unrelated to the analysis or make unsupported claims.

    If unable to fulfill the query due to missing or ambiguous information, state this explicitly and outline what additional details would be required to proceed.

    **Query**: {user_query}

    **Document Chunks**:  
    {document_chunks}
    """

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
