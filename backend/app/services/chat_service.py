from pathlib import Path
from typing import Optional

from app.ingestion.pdf_loader import load_pdf
from app.ingestion.chunking import split_documents
from app.ingestion.gemini_embedding import embeddings
from app.database.db import get_connection
import hashlib
from app.retrieval.vector_search import similarity_search
from app.llm.gemini import llm
from app.prompts.system_prompts import DOCUMENT_ASSISTANT_SYSTEM_PROMPT
import logging
from fastapi import UploadFile
import shutil
import uuid

logger = logging.getLogger(__name__)


def index_pdf_file(pdf_path: str, file_name: str = "") -> None:
    """Index a specific PDF file path (used for uploaded PDFs)."""
    pdf_file = Path(pdf_path)
    if not pdf_file.exists() or not pdf_file.is_file():
        logger.warning("index_pdf_file: file does not exist: %s", pdf_file)
        return

    all_docs = []
    try:
        all_docs.extend(load_pdf(str(pdf_file)))
    except Exception:
        logger.exception("Failed to load PDF: %s", pdf_file)
        return

    if not all_docs:
        return

    citation_file_name = Path(file_name).name if file_name else pdf_file.name
    for doc in all_docs:
        doc.metadata["file_name"] = citation_file_name

    chunks = split_documents(1000, 100, all_docs)
    for i, doc in enumerate(chunks, start=1):
        print(f"Chunk {i} size: {len(doc.page_content)} characters")
        print(f"Content: {doc.page_content}")
    texts = [d.page_content for d in chunks]

    try:
        vectors = embeddings.embed_documents(texts)
    except Exception:
        logger.exception("Failed to compute embeddings for uploaded file")
        return

    insert_sql = """
        INSERT INTO document_chunks (
            content, content_hash, source, file_name, page, embedding
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for doc, vec in zip(chunks, vectors):
                content_bytes = (doc.page_content or "").encode("utf-8")
                content_hash = hashlib.md5(content_bytes).hexdigest()

                try:
                    cursor.execute(
                        "SELECT id FROM document_chunks WHERE content_hash = %s LIMIT 1",
                        (content_hash,),
                    )
                    if cursor.fetchone():
                        continue
                except Exception:
                    logger.exception("DB check for existing content_hash failed (upload)")
                    continue

                cursor.execute(
                    insert_sql,
                    (
                        doc.page_content,
                        content_hash,
                        doc.metadata.get("source"),
                        doc.metadata.get("file_name"),
                        doc.metadata.get("page"),
                        vec,
                    ),
                )

        conn.commit()


def save_and_index_upload(upload: UploadFile, file_name: str = "") -> str:
    """Save an UploadFile to the service data dir and index it.

    Returns the saved filename (relative name).
    This is synchronous so it can be called via `run_in_threadpool`.
    """
    data_dir = Path(__file__).parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"uploaded_{uuid.uuid4().hex}.pdf"
    dest = data_dir / unique_name

    try:
        with dest.open("wb") as out_f:
            shutil.copyfileobj(upload.file, out_f)
    finally:
        try:
            upload.close()
        except Exception:
            pass

    # Index the saved file
    try:
        index_pdf_file(str(dest), file_name)
    except Exception:
        logger.exception("Failed to index uploaded file: %s", dest)
        # propagate so caller can surface as 500 if desired
        raise

    return unique_name


# def load_html() -> None:
    
#     """Load a single HTML file, chunk it, embed chunks, and index into DB."""
#     with open(DATA_HTML_FILE, "r", encoding="utf-8") as f:
#         return f.read()
    


def handle_chat(message: str, top_k: int = 5) -> str:
    try:
        query_vector = embeddings.embed_query(message)
    except Exception:
        logger.exception("Failed to embed query")
        query_vector = None
    # Retrieve similar chunks
    retrieved = []
    if query_vector is not None:
        try:
            retrieved = similarity_search(query_vector, limit=top_k) or []
        except Exception:
            logger.exception("Similarity search failed")
            retrieved = []
    logger.debug("Retrieved %d rows", len(retrieved))

    # Build a context string from retrieved rows
    context_text = build_context_from_retrieved(retrieved)

    # Prepare messages for the chat LLM
    human_prompt = f"Context:\n{context_text}\n\nQuestion:\n{message}"
    messages = [
        ("system", DOCUMENT_ASSISTANT_SYSTEM_PROMPT),
        ("human", human_prompt),
    ]

    # Invoke the LLM
    try:
        ai_msg = llm.invoke(messages)
    except Exception as e:
        return f"LLM error: {e}"
    # Extract a text reply from the returned AI message
    reply_text = extract_ai_reply(ai_msg)
    return reply_text


def build_context_from_retrieved(retrieved) -> str:
    """Construct a context text from retrieved DB rows.

    `retrieved` may be a list of tuples or dicts. Returns a joined string.
    """
    parts = []
    if not retrieved:
        return ""

    for row in retrieved:
        try:
            if isinstance(row, dict):
                content = row.get("content")
                source = row.get("source")
                page = row.get("page")
            else:
                # tuple: (id, content, source, file_name, page, distance)
                content = row[1]
                source = row[2]
                file_name = row[3]
                page = row[4]

            if isinstance(row, dict):
                file_name = row.get("file_name")
            source = file_name or source
            parts.append(
                f"Source: {file_name} (page {page})\n{content}"
            )
        except Exception:
            logger.exception("Failed to extract context from retrieved row")
            continue

    return "\n\n---\n\n".join(parts) if parts else ""


def extract_ai_reply(ai_msg) -> str:
    """Normalize various AI response shapes into a plain string reply."""
    try:
        if hasattr(ai_msg, "content"):
            content = ai_msg.content
            if isinstance(content, str):
                return content
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                return content[0].get("text", str(content[0]))
            return str(content)

        if hasattr(ai_msg, "generations"):
            # ChatResult-like object
            return ai_msg.generations[0][0].text

        return str(ai_msg)
    except Exception:
        logger.exception("Failed to extract reply from AI message")
        return str(ai_msg)
