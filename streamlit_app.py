import streamlit as st
import requests

API = "http://app:8000" # points to the FastAPI app

st.title("AFO Agent")

docs = requests.get(f"{API}/api/documents").json()

# Just fetches the docs for a status check
# TODO - add more interactable UI, with HITL feature
if not docs:
    st.info("No documents processed yet. Drop a PDF into the mailbox/ folder.")
else:
    for doc in docs:
        status_color = {
            "completed": "🟢",
            "failed": "🔴",
            "pending_review": "🟡",
            "processing": "🔵",
            "received": "⚪"
        }.get(doc["status"], "⚪")

        with st.expander(f"{status_color} {doc['filename']} — {doc['status']}"):
            st.json(doc)
