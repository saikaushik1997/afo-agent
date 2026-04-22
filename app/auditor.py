import logging
import time
from datetime import datetime, timedelta

from .database import SessionLocal
from .models import Document
from .agent import workflow

logger = logging.getLogger(__name__)

INTERVAL = 1  # run every 1 minute
TIMEOUT  = 0.5   # mark failed if stuck in processing for more than 30 seconds

def start_auditor():
    while True:
        time.sleep(INTERVAL)
        try:
            _audit()
        except Exception as e:
            logger.error(f"Auditor error: {e}", exc_info=True)

def _audit():
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=TIMEOUT) # If stuck in processed for more than 30 seconds - mark failed
        stale = db.query(Document).filter(
            Document.status == "processing",
            Document.created_at < cutoff
        ).all()

        if not stale:
            return

        for doc in stale:
            logger.warning(f"Auditor: {doc.id} ({doc.filename}) stuck in processing, marking failed")
            try:
                workflow.checkpointer.delete_thread(doc.id) # deletes checkpoint - cleanup the workflow
            except Exception as e:
                logger.error(f"Auditor: failed to delete checkpoint for {doc.id}: {e}")

        # Same condition, mark document as failed in db
        db.query(Document).filter(
            Document.status == "processing",
            Document.created_at < cutoff
        ).update({"status": "failed", "error": "Workflow timed out"})
        db.commit()

        # Now, cleaning up workflows for documents already marked as failed
        failed_docs = db.query(Document).filter(Document.status == "failed").all()
        for doc in failed_docs:
            try:
                workflow.checkpointer.delete_thread(doc.id)
            except Exception as e:
                logger.error(f"Auditor: failed to delete checkpoint for {doc.id}: {e}")
    finally:
        db.close()
