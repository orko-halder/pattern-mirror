"""
Pattern Mirror — Files API integration.

Uploads user-provided context documents to the Anthropic Files API.
Returns a file_id to reference in the analysis pipeline.
Files are ephemeral — call delete_file() after analysis completes.

Demonstrates: client.beta.files.upload(), file IDs, document blocks in messages.
"""

import io
import os
from dataclasses import dataclass
from anthropic import Anthropic
from prompts import CONTEXT_FILE_INSTRUCTION


# Supported MIME types for context documents
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".txt": "text/plain",
    ".md":  "text/plain",
    ".pdf": "application/pdf",
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@dataclass
class UploadedFile:
    file_id: str      # Anthropic file ID — use in document blocks
    filename: str
    size_bytes: int


def upload_context_file(client: Anthropic, file_bytes: bytes, filename: str) -> UploadedFile:
    """Upload a context document to the Anthropic Files API.

    Returns an UploadedFile with the file_id to pass to analyse_structured().
    Raises ValueError for unsupported types or oversized files.

    The caller is responsible for calling delete_file() once the file_id
    has been used — files are not automatically deleted.
    """
    ext = os.path.splitext(filename)[1].lower()
    mime_type = SUPPORTED_EXTENSIONS.get(ext)
    if not mime_type:
        supported = ", ".join(SUPPORTED_EXTENSIONS.keys())
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {supported}.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        size_kb = len(file_bytes) // 1024
        raise ValueError(f"File too large ({size_kb} KB). Maximum is 5 MB.")

    response = client.beta.files.upload(
        file=(filename, io.BytesIO(file_bytes), mime_type),
    )

    return UploadedFile(
        file_id=response.id,
        filename=filename,
        size_bytes=len(file_bytes),
    )


def delete_file(client: Anthropic, file_id: str) -> None:
    """Delete a file from the Anthropic Files API.

    Call this after analysis completes (or fails) to avoid accumulating
    files in the Anthropic workspace. Swallows errors so pipeline cleanup
    is never interrupted by a delete failure.
    """
    try:
        client.beta.files.delete(file_id)
        print(f"🗑️  Deleted context file {file_id}")
    except Exception as e:
        print(f"⚠️  Failed to delete file {file_id}: {e}")


def build_document_block(file_id: str) -> dict:
    """Build the document content block that references an uploaded file.

    Used by analyse_structured() to prepend the context document to the
    user message. Claude sees the document content before the reflection answers.
    """
    return {
        "type": "document",
        "source": {
            "type": "file",
            "file_id": file_id,
        },
        "title": "Additional context provided by the user",
        "context": CONTEXT_FILE_INSTRUCTION,
    }
