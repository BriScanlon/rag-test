# © 2024 Brian Scanlon. All rights reserved.

import os
import fitz  # PyMuPDF for PDF handling
import docx  # python-docx for DOCX handling

# Function to remove metadata from PDF and extract text
def process_pdf(file_path):
    print(f"Processing PDF: {file_path}")
    try:
        doc = fitz.open(file_path)
        metadata = doc.metadata  # Extract metadata (can be discarded)
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
        return text.strip()  # Return extracted text without metadata
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None

# Function to extract text from DOCX and strip metadata
def process_docx(file_path):
    print(f"Processing DOCX: {file_path}")
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text).strip()  # Return extracted text
    except Exception as e:
        print(f"Error processing DOCX: {e}")
        return None

# Function to extract text from TXT
def process_txt(file_path):
    print(f"Processing TXT: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content.strip()  # Return text content
    except FileNotFoundError:
        return None

# Function to handle different document types
def process_document(file_path):
    file_extension = file_path.split('.')[-1].lower()
    
    if file_extension == "pdf":
        return process_pdf(file_path)
    elif file_extension == "docx":
        return process_docx(file_path)
    elif file_extension == "txt":
        return process_txt(file_path)
    else:
        print(f"Unsupported file type: {file_extension}")
        return None
