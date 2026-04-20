import base64
import io
import json

from openai import OpenAI
import pdfplumber
from .models import ClassificationResult

from .database import SessionLocal
from .models import Examples
from langsmith import traceable
from prompts.classifier.v1 import SYSTEM_PROMPT, TOOL_DEFINITION

client = OpenAI()
import logging
logger = logging.getLogger(__name__)

# Text Extractor form structured/unstructured files
def _extract_text(content: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    else:
        return base64.standard_b64encode(content).decode() # for ".png" or any other types, let the LLM decide how to handle it

# Human review corrections go to the Examples table
# Fetching the corrected examples - to few-shot the prompt, to avoid repetition of same/similar issues
def _get_few_shot_examples() -> list:
    db = SessionLocal()
    try:
        examples = db.query(Examples).all()
        messages = []
        for i, ex in enumerate(examples):
            # Sample Input
            messages.append({
                "role": "user",
                "content": ex.document_text
            })
            # Sample assitant response
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": "classify_document",
                        "arguments": json.dumps({
                            "doc_type": ex.doc_type,
                            "fund_name": ex.fund_name,
                            "amount": ex.amount,
                            "currency": ex.currency,
                            "due_date": ex.due_date
                        })
                    }
                }]
            })
            # Sample tool call - ghost tool call
            messages.append({
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": json.dumps({
                    "doc_type": ex.doc_type,
                    "fund_name": ex.fund_name,
                    "amount": ex.amount,
                    "currency": ex.currency,
                    "due_date": ex.due_date
                })
            })
        return messages
    finally:
        db.close()

# Core specialist tool logic - the classifier LLM inference call
@traceable
def classify(content: bytes, filename: str) -> ClassificationResult:
    logger.info(f"Classifying {filename}")
    text = _extract_text(content, filename)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        tools=[TOOL_DEFINITION],
        tool_choice={"type": "function", "function": {"name": "classify_document"}},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *_get_few_shot_examples(),
            {"role": "user", "content": text}
        ]
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = ClassificationResult(**json.loads(tool_call.function.arguments))
    result.document_text = text
    logger.info(f"Classification result for {filename}: {result}")
    return result
