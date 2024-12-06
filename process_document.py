import logging
import fitz  # PyMuPDF for PDF handling
import docx  # python-docx for DOCX handling
import io


def extract_tables_from_page(page_text):
    """
    Extracts simple table-like structures from page text.

    Args:
        page_text (str): The text content of a PDF page.

    Returns:
        list: A list of table-like structures, each represented as a list of rows.
    """
    tables = []
    try:
        # Split text into lines
        lines = page_text.splitlines()

        # Look for lines with consistent column-like spacing (e.g., using tabs or multiple spaces)
        table = []
        for line in lines:
            # Detect potential table rows (e.g., lines with multiple spaces or tab delimiters)
            if "\t" in line or "  " in line:
                # Split the row into columns based on tabs or spaces
                columns = line.split("\t") if "\t" in line else line.split()
                table.append(columns)
            elif (
                table
            ):  # If we find a line not part of the table, save the current table
                tables.append(table)
                table = []  # Reset for the next table

        # Append the last table if still active
        if table:
            tables.append(table)

    except Exception as e:
        logging.warning(f"Failed to extract tables from page: {e}")

    return tables


def process_pdf(file_content):
    logging.debug("Starting PDF processing.")
    try:
        # Open the PDF from binary content using a BytesIO stream
        doc = fitz.open("pdf", io.BytesIO(file_content))
        metadata = doc.metadata  # Extract metadata
        logging.debug(f"Extracted metadata: {metadata}")

        # Initialize extracted data structure
        extracted_data = {"metadata": metadata, "text": "", "tables": []}

        # Iterate over pages in the PDF
        for page_num in range(doc.page_count):
            logging.debug(f"Processing page {page_num + 1}/{doc.page_count}")
            page = doc.load_page(page_num)

            # Extract plain text
            try:
                page_text = page.get_text("text")
                extracted_data["text"] += page_text
                logging.debug(f"Extracted text from page {page_num + 1}")
            except Exception as e:
                logging.warning(f"Failed to extract text from page {page_num + 1}: {e}")

            # Extract structured text for tables
            try:
                page_text = page.get_text("text")  # Use plain text instead of "dict"
                tables = extract_tables_from_page(page_text)  # Pass plain text to the function
                extracted_data["tables"].append(tables)
                logging.debug(f"Extracted tables from page {page_num + 1}")
            except Exception as e:
                logging.warning(f"Failed to extract tables from page {page_num + 1}: {e}")

        # Close the document
        doc.close()
        logging.debug("Completed PDF processing.")
        return extracted_data

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        return None


def process_docx(file_content):
    logging.debug("Starting DOCX processing.")
    try:
        # Load DOCX content from bytes
        from io import BytesIO

        doc = docx.Document(BytesIO(file_content))
        full_text = [para.text for para in doc.paragraphs]
        return {"text": "\n".join(full_text).strip()}
    except Exception as e:
        logging.error(f"Error processing DOCX: {e}")
        return None


def process_txt(file_content):
    logging.debug("Starting TXT processing.")
    try:
        text = file_content.decode("utf-8").strip()
        return {"text": text} if text else None
    except Exception as e:
        logging.error(f"Error processing TXT: {e}")
        return None


def process_document(file, file_extension):
    logging.debug(f"Processing document of type: {file_extension}")
    try:
        if file_extension == "pdf":
            return process_pdf(file)
        elif file_extension == "docx":
            return process_docx(file)
        elif file_extension == "txt":
            return process_txt(file)
        else:
            logging.error(f"Unsupported file type: {file_extension}")
            return None
    except Exception as e:
        logging.error(f"Error processing document: {e}")
        return None
