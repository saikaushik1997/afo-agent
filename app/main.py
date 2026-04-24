import threading
import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agent import resume_workflow, run_workflow, workflow
from .database import get_db, init_db
from .models import Document, DocumentOut, ClassificationResult, ReviewInput, Examples
from .poller import start_poller
from .email_poller import start_email_poller
from .auditor import start_auditor
from .embeddings import embed

from fastapi.responses import FileResponse
import os
import mimetypes

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # anything before yield runs on startup, anything after runs on shutdown
    init_db()
    threading.Thread(target=start_poller, daemon=True).start() # starting poller TODO - remove after email poller is implemented
    threading.Thread(target=start_email_poller, daemon=True).start() # starting email poller 
    threading.Thread(target=start_auditor, daemon=True).start() # starting workflow auditor
    yield


app = FastAPI(title="AFO Agent", lifespan=lifespan)

# Allowing all cross domain requests for demo
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/documents", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.status != "discarded").order_by(Document.created_at.desc()).all()


@app.get("/api/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc

@app.patch("/api/documents/{doc_id}/review", response_model=DocumentOut)
def review_document(doc_id: str, body: ReviewInput, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.status != "pending_review":
        raise HTTPException(400, f"Document is not pending review, current status: {doc.status}")

    # Save to examples table for few-shot injection later
    # If one or more fields are empty in the PATCH call, we use existing fields
    example = Examples(
        id=str(uuid.uuid4()),
        document_text=doc.document_text,
        doc_type=body.doc_type or doc.doc_type,
        fund_name=body.fund_name or doc.fund_name,
        amount=body.amount if body.amount is not None else doc.amount,
        currency=body.currency or doc.currency,
        due_date=body.due_date or doc.due_date,
        human_reason=body.human_reason or "",
    )
    # Embed the document text for similarity search to retrieve only relevant Examples for few-shot
    if doc.document_text:
        example.embedding = embed(doc.document_text)
        
    db.add(example)
    db.commit()

    # Resume LangGraph workflow with corrected result - will go to complete state
    # If one or more fields are empty in the PATCH call, we use existing fields
    corrected = ClassificationResult(
        doc_type=body.doc_type or doc.doc_type,
        fund_name=body.fund_name or doc.fund_name,
        amount=body.amount if body.amount is not None else doc.amount,
        currency=body.currency or doc.currency,
        due_date=body.due_date or doc.due_date,
    )
    try:
        resume_workflow(doc_id, corrected)
    except Exception as e:
        logger.error(f"Resume workflow failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to resume workflow: {str(e)}")

    db.refresh(doc)
    return doc

# Human Reviewer decides its a garbage doc that cant be classified and needs to be discarded
@app.post("/api/documents/{doc_id}/discard", response_model=DocumentOut)
def discard_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    # Discard possible only on pending review docs
    if doc.status not in ("pending_review", "failed"):
        raise HTTPException(400, f"Document is neither pending review nor failed, current status: {doc.status}")
    db.query(Document).filter(Document.id == doc_id).update({"status": "discarded"})
    db.commit()
    db.refresh(doc)
    workflow.checkpointer.delete_thread(doc_id)
    return doc

# Endpoint for file preview for human reviewer - mounted the mailbox folder to docker
# processed files go in mailbox
@app.get("/api/documents/{doc_id}/file")
def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    path = f"/app/mailbox/{doc.filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found on disk")
    media_type, _ = mimetypes.guess_type(doc.filename) # looks at file extension, and gets the media type
    return FileResponse(path, media_type=media_type or "application/octet-stream") # handle unknown media type

# Endpoint for retrying a failed document - starts a new workflow
@app.post("/api/documents/{doc_id}/retry", response_model=DocumentOut)
def retry_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.status != "failed":
        raise HTTPException(400, f"Document is not failed, current status: {doc.status}")
    
    path = f"/app/mailbox/{doc.filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "File not found on disk")

    db.query(Document).filter(Document.id == doc_id).update({"status": "received", "error": None})
    db.commit()
    db.refresh(doc)

    with open(path, "rb") as f:
        content = f.read()

    threading.Thread(target=run_workflow, args=(doc_id, content, doc.filename), daemon=True).start()
    return doc
