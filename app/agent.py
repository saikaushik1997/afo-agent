from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph

from .classifier import classify
from .database import SessionLocal
from .models import ClassificationResult, Document
from .judge import judge as run_judge
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg
import os

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
            judge_score=None,
            judge_reasoning=None,
            document_text=result.document_text
        )
    except (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError) as e:
        logger.warning(f"Transient error for {state['doc_id']}, retrying: {e}")
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=None,
            error=str(e),
            retry_count=state["retry_count"] + 1,
            judge_score=None,
            judge_reasoning=None,
            document_text=state.get("document_text")
        )
    except Exception as e:
        logger.error(f"Permanent error for {state['doc_id']}, skipping retries: {e}", exc_info=True)
        return AgentState(
            doc_id=state["doc_id"],
            content=state["content"],
            filename=state["filename"],
            result=None,
            error=str(e),
            retry_count=3, # Setting retry count to 3 - since error is not transient - goes to pending review
            judge_score=None,
            judge_reasoning=None,
            document_text=state.get("document_text")
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
            "document_text": state.get("document_text"),
            "error": None,
        })
        db.commit()
    finally:
        db.close()
    return state

# Escalate to human review queue
def pending_review(state: AgentState) -> AgentState:
    logger.info(f"Document {state['doc_id']} flagged for pending review")
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.id == state["doc_id"]).update({
            "doc_type": state["result"].doc_type if state.get("result") else None,
            "fund_name": state["result"].fund_name if state.get("result") else None,
            "amount": state["result"].amount if state.get("result") else None,
            "currency": state["result"].currency if state.get("result") else None,
            "due_date": state["result"].due_date if state.get("result") else None,
            "document_text": state.get("document_text"),
            "status": "pending_review",
            "error": state.get("error") or state.get("judge_reasoning") # error when transient failures exhaust retries, judge_reasoning for low scores by judge LLM
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
graph.add_edge("pending_review", "complete") # pending_review is a temorary
graph.add_conditional_edges("judge", _route, {
    "complete": "complete",
    "pending_review": "pending_review",
    "analyze": "analyze"
})

# Valid END states
graph.add_edge("complete", END)

DB_URI = os.getenv("DATABASE_URL", "postgresql://afo:afo@localhost:5432/afo")

connection = psycopg.connect(DB_URI, autocommit=True)
checkpointer = PostgresSaver(connection)
checkpointer.setup()

# Interrupt after pending review, before complete
# routes to complete, post successful human review
workflow = graph.compile(
    checkpointer=checkpointer,
    interrupt_after=["pending_review"]
)

# Triggered once poller finds an email with valid attachment
# Using UUID doc_id for uniquely identifying thread_id, to support LangGraph interrupt state tracking
def run_workflow(doc_id: str, content: bytes, filename: str):
    config = {"configurable": {"thread_id": doc_id}}
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
    }, config)

# Triggered by LangGraph interrupt, when human_review is done
# Used saved state to resume a paused graph
def resume_workflow(doc_id: str, corrected_result: ClassificationResult):
    logger.info(f"Resuming workflow for {doc_id}")
    config = {"configurable": {"thread_id": doc_id}}
    workflow.update_state(config, {
        "result": corrected_result,
        "judge_score": 1.0,
        "judge_reasoning": "Human reviewed and corrected"
    }, as_node="judge")
    logger.info(f"State updated for {doc_id}, invoking...")
    workflow.invoke(None, config)
    logger.info(f"Workflow resumed for {doc_id}")
