from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from .classifier import classify
from .database import SessionLocal
from .models import ClassificationResult, Document
from .judge import judge as run_judge

import openai
import logging
logger = logging.getLogger(__name__)

# In memory state that gets passed around between nodes
class AgentState(TypedDict):
    doc_id: str
    content: bytes
    filename: str
    result: Optional[ClassificationResult]
    error: Optional[str]
    retry_count: int
    judge_score: Optional[float]
    judge_reasoning: Optional[str]
    document_text: Optional[str]


# Acknowledge node - entry point for workflow
# Updates the status of the doc in db to processing
def acknowledge(state: AgentState) -> AgentState:
    logger.info(f"Acknowledging document {state['doc_id']}")
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.id == state["doc_id"]).update({"status": "processing"})
        db.commit()
    finally:
        db.close()
    return state


# calls the classifier LLM, model attempts to classify and extract metadata
# successful -> result is modified
# failed -> error is modified
def analyze(state: AgentState) -> AgentState:
    logger.info(f"Analyzing document {state['doc_id']}, attempt {state['retry_count'] + 1}")
    try:
        result = classify(state["content"], state["filename"])
        logger.info(f"Classification successful for {state['doc_id']}: {result.doc_type}")
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=result,
            error=None,
            retry_count=state["retry_count"],
            document_text=result.document_text,
        )
    except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError) as e:
        logger.warning(f"Transient error for {state['doc_id']}, retrying: {e}")
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=None,
            error=str(e),
            retry_count=state["retry_count"] + 1
        )
    except Exception as e:
        logger.error(f"Permanent error for {state['doc_id']}, skipping retries: {e}", exc_info=True)
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=None,
            error=str(e),
            retry_count=3 # Setting retry count to 3 - since error is not transient - goes to pending review
        )

# LLM as a Judge Node - takes in raw docs and classified outputs - to judge the main LLM
def judge(state: AgentState) -> AgentState:
    logger.info(f"Judging document {state['doc_id']}")
    result = run_judge(
        document_text=state["document_text"],
        classification=state["result"].model_dump()
    )
    return AgentState(
        doc_id=state["doc_id"],
        content=state["content"],
        filename=state["filename"],
        result=state["result"],
        error=state["error"],
        retry_count=state["retry_count"],
        document_text=state["document_text"],
        judge_score=result.confidence,
        judge_reasoning=result.reasoning
    )

# Update the db object as processing completed
def complete(state: AgentState) -> AgentState:
    logger.info(f"Completing document {state['doc_id']}")
    db = SessionLocal()
    try:
        result = state["result"]
        db.query(Document).filter(Document.id == state["doc_id"]).update({
            "status": "completed",
            "doc_type": result.doc_type,
            "fund_name": result.fund_name,
            "amount": result.amount,
            "currency": result.currency,
            "due_date": result.due_date,
        })
        db.commit()
    finally:
        db.close()
    return state

# Escalate to human review queue
# TODO - Need a PATCH endpoint for human to manually add the missing params
def pending_review(state: AgentState) -> AgentState:
    logger.info(f"Document {state['doc_id']} flagged for pending review")
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.id == state["doc_id"]).update({
            "status": "pending_review",
            "error": state.get("error")
        })
        db.commit()
    finally:
        db.close()
    return state

# Decision edge, explicit error - retry 3 times to handle transient failures, route to human review after
# doc_type is None after classification - human review, make changes to file, resume after
def _route(state: AgentState) -> str:
    if state.get("error"):
        return "analyze" if state["retry_count"] < 3 else "pending_review"
    if state["result"].doc_type is None:
        return "pending_review"
    if state["judge_score"] < 0.9:
        return "pending_review"
    if any(v is None for v in [state["result"].fund_name, state["result"].amount, state["result"].currency, state["result"].due_date]):
        # if any of the fields are missing, route to pending review
        return "pending_review"
    return "complete"


# Creating the graph structure
graph = StateGraph(AgentState)
graph.add_node("acknowledge", acknowledge)
graph.add_node("analyze", analyze)
graph.add_node("complete", complete)
graph.add_node("pending_review", pending_review)
graph.add_node("judge", judge)

graph.set_entry_point("acknowledge") # Entry point
graph.add_edge("acknowledge", "analyze") # Linear, only goes to analyze, after acknowledge
graph.add_edge("analyze", "judge") # Linear, only goes to judge, after analyze
graph.add_conditional_edges("judge", _route, {
    "complete": "complete",
    "pending_review": "pending_review",
    "analyze": "analyze"
})

# Valid END states
graph.add_edge("complete", END)
graph.add_edge("pending_review", END) # TODO - change to wait for interrupt - when PATCH endpoint is implemented

workflow = graph.compile()

# Triggered once poller finds an email with valid attachment
def run_workflow(doc_id: str, content: bytes, filename: str):
    workflow.invoke({
        "doc_id": doc_id,
        "content": content,
        "filename": filename,
        "result": None,
        "error": None,
        "retry_count": 0,
        "judge_score": None,
        "judge_reasoning": None,
        "document_text": None,
    })

