import base64
import io
import json

from openai import OpenAI
import pdfplumber
from .models import ClassificationResult

client = OpenAI()
import logging
logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a specialist in analyzing financial documents for a Fund of Funds.
You classify documents and extract metadata from them with high precision."""

# Input schema determines enforces Claude to output in that exact JSON format
# Keeping all fields as nullable - ensures no hallucination
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "classify_document",
        "description": "Classify a financial document and extract its metadata. Return null for any field you are not confident about.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["invoice", "capital_call"],
                    "description": "Invoice: Request for payment for services/fees. Capital Call: Formal requests from a Private Equity fund for a limited partner to contribute capital."
                },
                "fund_name": {"type": "string", "description": "Full legal name of the fund as stated in the document"},
                "amount": {"type": "number", "description": "Numeric value only, no commas or currency symbols e.g. 1000"},
                "currency": {"type": "string", "description": "3-letter ISO code e.g. INR, USD, EUR, GBP"},
                "due_date": {"type": "string", "description": "DD-MM-YYYY format"}
            }
        }
    }
}

# Text Extractor form structured/unstructured files
def _extract_text(content: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    else:
        return base64.standard_b64encode(content).decode() # for ".png" or any other types, let the LLM decide how to handle it

# Core specialist tool logic - the classifier LLM inference call
def classify(content: bytes, filename: str) -> ClassificationResult:
    logger.info(f"Classifying {filename}")
    text = _extract_text(content, filename)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        tools=[TOOL_DEFINITION],
        tool_choice={"type": "function", "function": {"name": "classify_document"}},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = ClassificationResult(**json.loads(tool_call.function.arguments))
    result.document_text = text
    logger.info(f"Classification result for {filename}: {result}")
    return result
