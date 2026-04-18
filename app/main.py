import threading
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .agent import run_workflow
from .database import get_db, init_db
from .models import Document, DocumentOut
from .poller import start_poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    # anything before yield runs on startup, anything after runs on shutdown
    init_db()
    threading.Thread(target=start_poller, daemon=True).start() # starting poller
    yield


app = FastAPI(title="AFO Agent", lifespan=lifespan)

# Allowing all cross domain requests for demo
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/documents", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@app.get("/api/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc
