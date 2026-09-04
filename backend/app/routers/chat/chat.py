from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from starlette.concurrency import run_in_threadpool
from pathlib import Path
import uuid
import shutil

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat, index_pdf_file, save_and_index_upload

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, message: str | None = Form(None), file: UploadFile | None = File(None)):
    """Chat endpoint that also accepts an optional PDF file upload in multipart form.

    Supports JSON payloads (application/json) with `{ "message": "..." }` or
    multipart/form-data with `message` and optional `file` fields.
    """
    # If message wasn't provided as form, attempt to parse JSON body
    if not message:
        try:
            body = await request.json()
            message = body.get("message")
        except Exception:
            message = None

    try:
        chat_req = ChatRequest(message=message)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")

    message = chat_req.message

    if not message and not file:
        raise HTTPException(status_code=400, detail="Either `message` or `file` must be provided")

    unique_name = None
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        try:
            unique_name = await run_in_threadpool(save_and_index_upload, file)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to index uploaded PDF")

    # If message is empty after upload, return success ack
    if not message:
        return ChatResponse(reply=f"Uploaded {unique_name}")

    # Handle the chat using the (possibly newly indexed) document context
    reply = handle_chat(message)
    return ChatResponse(reply=reply)


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Receive a PDF from the frontend, save it to app/data and trigger indexing."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    data_dir = Path(__file__).parents[2] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"uploaded_{uuid.uuid4().hex}.pdf"
    dest = data_dir / unique_name

    try:
        with dest.open("wb") as out_f:
            shutil.copyfileobj(file.file, out_f)
    finally:
        await run_in_threadpool(file.close)

    # Trigger indexing in a threadpool so the request returns quickly
    try:
        await run_in_threadpool(index_pdf_file, str(dest))
    except Exception:
        # Indexing errors should not expose internals to the frontend
        raise HTTPException(status_code=500, detail="Failed to start indexing")

    return {"status": "ok", "filename": unique_name}