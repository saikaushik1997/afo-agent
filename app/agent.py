from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from .classifier import classify
from .database import SessionLocal
from .models import ClassificationResult, Document

import logging
logger = logging.getLogger(__name__)

# In memory state that gets passed around between nodes
class AgentState(TypedDict):
    doc_id: str
    content: bytes
    filename: str
    result: Optional[ClassificationResult]
    error: Optional[str]

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
    logger.info(f"Analyzing document {state['doc_id']}")
    try:
        result = classify(state["content"], state["filename"])
        logger.info(f"Classification successful for {state['doc_id']}: {result.doc_type}")
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=result,
            error=None
        )
    except Exception as e:
        logger.error(f"Classification failed for {state['doc_id']}: {e}", exc_info=True)
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=None,
            error=str(e)
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
        db.query(Document).filter(Document.id == state["doc_id"]).update({"status": "pending_review"})
        db.commit()
    finally:
        db.close()
    return state

# Unexpected technical error - just sits in mailbox for now, cant be processed further
# TODO - mark the email as undread for retries
def fail(state: AgentState) -> AgentState:
    logger.error(f"Document {state['doc_id']} failed: {state['error']}")
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.id == state["doc_id"]).update({
            "status": "failed",
            "error": state["error"],
        })
        db.commit()
    finally:
        db.close()
    return state


# Decision edge, explicit error - fail node
# doc_type is None after classification - human review, make changes to file, resume after
def _route(state: AgentState) -> str:
    if state.get("error"):
        return "fail"
    if state["result"].doc_type is None:
        return "pending_review"
    return "complete"


# Creating the graph structure
graph = StateGraph(AgentState)
graph.add_node("acknowledge", acknowledge)
graph.add_node("analyze", analyze)
graph.add_node("complete", complete)
graph.add_node("pending_review", pending_review)
graph.add_node("fail", fail)

graph.set_entry_point("acknowledge") # Entry point
graph.add_edge("acknowledge", "analyze") # Linear, only goes to analyze, after acknowledge
graph.add_conditional_edges("analyze", _route, {
    "complete": "complete",
    "pending_review": "pending_review",
    "fail": "fail"
})

# Valid END states
graph.add_edge("complete", END)
graph.add_edge("pending_review", END) # TODO - change to wait for interrupt - when PATCH endpoint is implemented
graph.add_edge("fail", END)

workflow = graph.compile()

# Triggered once poller finds an email with valid attachment
def run_workflow(doc_id: str, content: bytes, filename: str):
    workflow.invoke({
        "doc_id": doc_id,
        "content": content,
        "filename": filename,
        "result": None,
        "error": None,
    })

