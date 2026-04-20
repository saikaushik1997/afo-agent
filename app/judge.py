import json
import logging
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel
from .models import JudgeResult
from langsmith import traceable
from prompts.judge.v5 import SYSTEM_PROMPT, TOOL_DEFINITION

logger = logging.getLogger(__name__)
client = OpenAI()

# classification dict, and initial text both passed as context for the LLM to judge
# classification is what the classifier model returned
@traceable
def judge(document_text: str, classification: dict) -> JudgeResult:
    logger.info(f"Judging classification: {classification}")

    response = client.chat.completions.create(
        model="gpt-4o",
        tools=[TOOL_DEFINITION],
        tool_choice={"type": "function", "function": {"name": "judge_classification"}},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Document:\n{document_text}\n\nClassification result:\n{json.dumps(classification, indent=2)}"}
        ]
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = JudgeResult(**json.loads(tool_call.function.arguments))
    logger.info(f"Judge result: confidence={result.confidence}, reasoning={result.reasoning}")
    return result
