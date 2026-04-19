import email
import imaplib
import logging
import uuid
import os

from .agent import run_workflow
from .database import SessionLocal
from .models import Document

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10

# called on startup - poll once every POLL_INTERVAL seconds
def start_email_poller():
    import time
    import os

    host = os.getenv("IMAP_HOST", "imap.gmail.com")
    user = os.getenv("IMAP_USER")
    password = os.getenv("IMAP_PASSWORD")

    while True:
        try:
            _poll(host, user, password)
        except Exception as e:
            logger.error(f"Email poller error: {e}", exc_info=True)
        time.sleep(POLL_INTERVAL)

def _poll(host: str, user: str, password: str):
    mail = imaplib.IMAP4_SSL(host)
    mail.login(user, password) # login to email
    mail.select(os.getenv("IMAP_FOLDER"))  # Look in shared email folder/label

    _, data = mail.search(None, "UNSEEN")
    message_ids = data[0].split()

    # No Unread/new emails
    if not message_ids:
        logger.debug("No unread emails found")
        mail.logout()
        return
    
    for m_id in message_ids:
        _, msg_data = mail.fetch(m_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        message_id = msg.get("Message-ID")

        db = SessionLocal()
        try:
            # Safety net on top "UNSEEN" - in case an already processed email gets through
            already_seen = db.query(Document).filter(Document.message_id == message_id).first()
            if already_seen:
                logger.debug(f"Skipping already seen email: {message_id}")
                continue

            # Attachments in the email
            for part in msg.walk():
                content_type = part.get_content_type()
                filename = part.get_filename()

                if not filename:
                    continue
                if not filename.lower().endswith((".pdf", ".png")): # Supports png images, or pdfs
                    continue

                content = part.get_payload(decode=True)
                doc = Document(id=str(uuid.uuid4()), filename=filename, message_id=message_id)
                db.add(doc)
                db.commit()
                db.refresh(doc)
                logger.info(f"New email attachment: {filename} ({doc.id})")

                mail.store(m_id, "+FLAGS", "\\Seen") # Marks email as Seen, to prevent processing again
                run_workflow(doc.id, content, filename)

        finally:
            db.close()
    
    mail.logout() # logout
 


