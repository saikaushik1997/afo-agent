# AFO Agent — Interview Prep

## Architecture

**Why LangGraph?**
- State object passed through nodes, selectively updated at each step
- Non-linear routing — retry loops, conditional branching
- Interrupt/resume via PostgreSQL checkpointer — survives container restarts
- A simple pipeline can't do any of these cleanly

**Why two LLMs?**
- Classifier (`gpt-4o-mini`) — fast, cheap, specialist extraction
- Judge (`gpt-4o`) — more capable, independent validation of classifier output
- Self-validation by one LLM is less reliable than an independent second pass
- Judge catches semantic issues `_route` can't — wrong date type, dual-purpose docs, partial payments

**What if both LLMs are wrong?**
- 0.9 threshold is deliberately high — any doubt routes to human review
- Missing fields also route to review regardless of confidence
- Downstream wire approval is a separate human-approved process outside AFO
- Corrections go to Examples table — system learns and improves

**Why not ReAct?**
- ReAct gives LLM autonomy over routing — introduces non-determinism
- Financial docs require auditable, predictable routing
- Deterministic `_route` with LLM-as-judge is more defensible for this domain

---

## LLM Design

**Temperature 0?**
- Same document must produce same result every run
- Wire amounts and due dates can't vary based on sampling randomness

**Tool use for structured output?**
- Forces JSON schema-conformant output via `tool_choice`
- All fields optional — model returns `null` rather than hallucinating
- `null` fields trigger human review

**Confidence threshold 0.9?**
- Financial docs require high precision — wrong wire amount has real consequences
- Validated against test cases, set empirically
- In prod would move to 0.99, tuned based on observed false positive/negative rates

---

## Prompt Engineering

**How do you test prompt changes?**
- Prompt versioning — new version for each change
- Every version validated against all prior test cases before replacing previous
- In prod: env variables for prompts, no redeployment needed
- Next step: LangSmith prompt hub for versioning + rollback

**How do you know self-improvement works?**
- Correct one document, generate similar document with same ambiguity, verify classifier gets it right
- `conflicting_due_date` documents proven this — correction generalised correctly
- In prod: golden eval set run against every Examples table update

**Rollback if bad example poisons few-shot?**
- Examples ingested at query time — delete the row, next classify call won't see it
- No redeployment needed

**Preventing few-shot conflicts?**
- Currently not handled — works at low volume
- At scale: similarity filtering via embeddings, only inject relevant examples
- Vector DB natural next step when Examples table grows large enough

---

## HITL

**SLA for human review queue?**
- Not defined yet — depends on ops team capacity and document due date proximity
- Capital calls near due date need faster review than invoices
- In prod: priority flag based on `due_date` proximity, queue cleared within business hours

**What stops a human making a wrong correction?**
- Correction saved to Examples with `human_reason` — reviewable and deletable
- Bad example can be removed from DB immediately, no redeployment
- In prod: example validation before saving, periodic curation of Examples table

---

## Scale & Production

**Scale to 1000 docs/day?**
- Current: synchronous single-threaded poller, good for a few hundred docs/day
- At scale: S3 + EventBridge + SQS to decouple producer/consumer
- Gmail API webhooks replace IMAP polling
- ECS with multiple worker containers — LangGraph `thread_id` isolation means no coordination needed

**Latency per document?**
- ~5-8s end to end — text extraction (0.5-2s) + classifier (2-3s) + judge (2-3s)
- Sequential dependency: judge needs classifier output, can't parallelise
- Latency not critical — ingestion is async, no user waiting on response
- Horizontal scaling increases throughput, not per-doc latency

**Deduplication?**
- Email poller: IMAP `UNSEEN` flag + `message_id` DB check
- File poller: filename DB check
- `message_id` is mail-server assigned, guaranteed unique per email

**Monitoring?**
- LangSmith — every LLM call traced with inputs, outputs, confidence, latency
- Python logging on every node transition, error, retry
- Dashboard — failed count, pending review queue depth as operational signals
- Missing for prod: CloudWatch/Datadog alerting on queue depth spikes

**PostgreSQL over Redis for checkpointing?**
- Redis is in-memory by default — checkpoints lost on restart
- PostgreSQL persistence guaranteed out of the box
- Already using PostgreSQL for documents table — one less infra dependency

**Checkpoint cleanup?**
- `complete` node calls `delete_thread` — checkpoint removed on successful completion
- Auditor runs every 60s — marks docs stuck in `processing` > 30s as `failed`, deletes checkpoint
- Discard and failed both clean up checkpoints

**Why not vector DB for examples?**
- PostgreSQL works at current scale
- At scale: vector DB for similarity search — inject only relevant examples, detect conflicts semantically
- Don't over-engineer before token limits or relevance degrades
