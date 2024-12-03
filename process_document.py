# © 2024 Brian Scanlon. All rights reserved.

import os
import fitz  # PyMuPDF for PDF handling
import docx  # python-docx for DOCX handling


# Function to remove metadata from PDF and extract structured text
def process_pdf(file_path):
    print(f"Processing PDF: {file_path}")
    try:
        doc = fitz.open(file_path)
        metadata = doc.metadata  # Extract metadata (can be discarded)
        extracted_data = {"metadata": metadata, "text": "", "tables": []}

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)

            # Extract plain text for general content
            page_text = page.get_text("text")
            extracted_data["text"] += page_text

            # Extract structured text as dictionary
            page_dict = page.get_text("dict")
            extracted_data["tables"].append(extract_tables_from_page(page_dict))

        doc.close()
        return extracted_data  # Return both plain text and table data
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None


# Helper function to extract tables based on text positions
def extract_tables_from_page(page_dict):
    blocks = page_dict.get("blocks", [])
    table_data = []
    for block in blocks:
        if "lines" in block:
            row = []
            for line in block["lines"]:
                row_text = " ".join([span["text"] for span in line["spans"]])
                row.append(row_text)
            if row:  # Only append non-empty rows
                table_data.append(row)
    return table_data


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
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return content.strip()  # Return text content
    except FileNotFoundError:
        return None


# Function to handle different document types
def process_document(file_path):
    file_extension = file_path.split(".")[-1].lower()

    if file_extension == "pdf":
        return process_pdf(file_path)
    elif file_extension == "docx":
        return process_docx(file_path)
    elif file_extension == "txt":
        return process_txt(file_path)
    else:
        print(f"Unsupported file type: {file_extension}")
        return None
