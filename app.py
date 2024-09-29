from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Initialize FastAPI app
app = FastAPI()

# Load model and tokenizer locally (distilgpt2 in this case)
model_name = "mistralai/Mistral-7B-Instruct-v0.1"  # Replace with the actual model name (e.g., Mistral model)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Option 1: Set pad_token to eos_token
tokenizer.pad_token = tokenizer.eos_token

# Pydantic model for request validation
class InputData(BaseModel):
    text: str

# Function to generate model response
def generate_response(input_text: str):
    # Tokenize input text with attention mask and padding enabled
    inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
    
    # Generate response with attention mask
    outputs = model.generate(
        inputs.input_ids, 
        attention_mask=inputs.attention_mask,  # Add attention_mask here
        max_length=50
    )
    
    # Decode the generated tokens
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# API endpoint to send data to the model
@app.post("/send-to-model")
def send_to_model(data: InputData):
    model_response = generate_response(data.text)
    return {"response": model_response}
