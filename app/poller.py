import time
import uuid
from pathlib import Path

from .agent import run_workflow
from .database import SessionLocal
from .models import Document
import logging
logger = logging.getLogger(__name__)

MAILBOX = Path("mailbox") # TODO - replace with an actual IMAP/Email call
POLL_INTERVAL = 10  # seconds

# called on startup, runs in background thread
def start_poller():
    MAILBOX.mkdir(exist_ok=True)
    while True:
        _poll()
        time.sleep(POLL_INTERVAL)

# calls run_workflow, blocks thread for now, processes one file at a time
# TODO - async processing of files
def _poll():
    db = SessionLocal()
    try:
        for filepath in MAILBOX.iterdir():
            if not filepath.suffix.lower() in (".pdf", ".png"):
                continue

            already_seen = db.query(Document).filter(Document.filename == filepath.name).first()
            if already_seen: # ignore duplicates, TODO - Mark email as read/delete processed email
                logger.debug(f"Skipping already seen file: {filepath.name}")
                continue

            content = filepath.read_bytes()
            doc = Document(id=str(uuid.uuid4()), filename=filepath.name) # create the db record with received status(default)
            db.add(doc)
            db.commit()
            db.refresh(doc)
            logger.info(f"Created document {doc.id} for {filepath.name}")

            try:
                run_workflow(doc.id, content, filepath.name)
            except Exception as e:
                logger.error(f"Workflow failed for {doc.id}: {e}", exc_info=True)
                db.query(Document).filter(Document.id == doc.id).update({"status": "failed", "error": str(e)})
                db.commit()
            logger.info(f"Workflow completed for {doc.id}")
    
    except Exception as e:
        logger.error(f"Poller error: {e}", exc_info=True)
    finally:
        db.close()
