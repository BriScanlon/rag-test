# © 2024 Brian Scanlon. All rights reserved.

def chunk_text(text, chunk_size=512):
    """Splits text into chunks of specified size."""
    words = text.split()
    if len(words) == 0:  # Check for empty document content
        return []
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
