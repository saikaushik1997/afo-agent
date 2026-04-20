# Prompt versioning - to capture improvements

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
