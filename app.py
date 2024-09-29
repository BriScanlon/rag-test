import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load the pre-trained embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to load the document
def load_document(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to split text into smaller chunks
def chunk_text(text, chunk_size=512):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# Function to embed text chunks using the model
def embed_chunks(chunks):
    return model.encode(chunks)

# Function to create and query FAISS index
def create_faiss_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    return index

def query_index(index, query, top_k=3):
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), top_k)
    return indices[0]

# Main workflow
if __name__ == "__main__":
    # Prompt user to add document
    doc_name = input("Enter the document name (located in the 'documents/' folder, with extension): ")
    doc_path = os.path.join('documents', doc_name)
    
    if not os.path.exists(doc_path):
        print(f"Error: {doc_name} not found in the 'documents/' folder.")
    else:
        # Load and process the document
        text = load_document(doc_path)
        chunks = chunk_text(text, chunk_size=512)  # Split text into chunks
        embeddings = embed_chunks(chunks)          # Embed each chunk

        # Create FAISS index for similarity search
        index = create_faiss_index(embeddings)
        
        # Prompt for a query to retrieve similar chunks
        user_query = input("Enter a query to search the document: ")
        result_indices = query_index(index, user_query)

        # Output the top matching chunks
        print("\nTop matching chunks:")
        for idx in result_indices:
            print(f"\nChunk {idx+1}:\n{chunks[idx]}")
