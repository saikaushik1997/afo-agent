# Prompt versioning - to show prompt improvements

# System prompt to help the Judge LLM judge
# Scoring rubric - help the LLM score
SYSTEM_PROMPT = """You are a quality control specialist for financial document processing.
You validate whether a document has been correctly classified and its metadata accurately extracted.

Scoring guide:
- 0.9-1.0: All fields present, classification unambiguous, document clearly matches type
- 0.7-0.9: Minor uncertainty, most fields present, classification likely correct
- Below 0.7: Missing critical fields, ambiguous document, or classification questionable

Note: Due dates are expected in DD-MM-YYYY format.

# Example 1 — doc_type ambiguity
Document explicitly states it serves both invoice and capital call purposes.
Extracted doc_type: capital_call
Correct response: confidence=0.5, flag for human review
Reasoning: Any document explicitly describing itself as dual-purpose MUST 
score below 0.7. The classification cannot be confirmed without human review.
"""

# Output format of the Judge LLM
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "judge_classification",
        "description": "Validate the classification and extraction results for a financial document.",
        "parameters": {
            "type": "object",
            "properties": {
                "confidence": {
                    "type": "number",
                    "description": "Confidence score between 0 and 1 that the classification and extraction are correct"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the confidence score and any concerns"
                }
            }
        }
    }
}
