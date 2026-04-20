# Judge Prompt Engineering

## Test Cases

### TC-1 — Dual-Purpose Document

```
Date: March 15, 2024
Reference: FN-2024-0892
To: Sunrise Capital Partners LP
From: Alter Domus Fund IV Management LLC

Dear Limited Partner,

Pursuant to Section 4.2 of the Limited Partnership Agreement, please remit the following amount
by April 1, 2024:

Management Fee (Q1 2024): $50,000
Capital Contribution (Call #3): $450,000
Total Amount Due: $500,000

Wire Instructions:
Bank: JPMorgan Chase
ABA: 021000021
Account: 4872910034
Ref: FN-2024-0892

This notice serves as both your quarterly fee invoice and capital call notification per fund agreement terms.

Alter Domus Fund IV Management LLC
```

**Expected:** `confidence < 0.7`, flagged for human review — document explicitly describes itself as dual-purpose.

---

### TC-2 — Conflicting Due Dates

```
CAPITAL CALL NOTICE
Alter Domus Fund V Management LLC

Notice Issued: March 1, 2024
Due Date: April 30, 2024
Reference: CC-2024-0047
To: Crestview Partners LP
From: Alter Domus Fund V Management LLC

Dear Limited Partner,

Please be advised that Fund V is making its second capital call in connection with the acquisition
of Portfolio Company Holdings Inc. The call amount reflects your pro-rata share of the total
commitment.

In order to ensure timely settlement and avoid disruption to the closing process, all limited
partners are required to wire funds no later than March 15, 2024. The April 30, 2024 date
referenced above reflects the final reconciliation deadline for fund accounting purposes only and
does not represent the wire deadline.

Capital Call Amount: $1,200,000

Wire Instructions:
Bank: Goldman Sachs Bank USA
ABA: 026015937
Account: 9912740055
Ref: CC-2024-0047

Questions regarding this notice should be directed to your relationship manager. Please do not use
the April 30 reconciliation date for wire scheduling.

Alter Domus Fund V Management LLC
```

**Expected:** `confidence <= 0.7`, flagged for human review — header `Due Date: April 30, 2024` contradicts the explicit wire deadline of March 15, 2024 in the body.

---

## Versions

### V1

**Prompt change:** Baseline — scoring rubric only, no ambiguity handling.

**TC-1:** FAIL
**TC-2:** FAIL (non-deterministic — same document returned `confidence=0.92` on some runs, slipping through to `completed` with wrong `due_date=30-04-2024`)

```
confidence=1.0
reasoning=The document is clearly identified as a 'capital_call' based on the content of the
document. All relevant fields have been extracted correctly: the fund name 'Alter Domus Fund IV
Management LLC', the total amount due of 500,000 USD, and the due date '01-04-2024'. The document
serves as both a fee invoice and a capital call notification, which aligns with the classification.
There are no missing critical fields, and the classification is unambiguous.
```

---

### V2

**Prompt change:** Added few-shot example targeting dual-purpose `doc_type` ambiguity.

```
Example 1 — doc_type ambiguity
Document explicitly states it serves both invoice and capital call purposes.
Extracted doc_type: capital_call
Correct response: confidence=0.5, flag for human review
Reasoning: Any document explicitly describing itself as dual-purpose MUST
score below 0.7. The classification cannot be confirmed without human review.
```

**TC-1:** PASS
**TC-2:** FAIL (inherited — no date conflict handling yet)

```
confidence=0.5
reasoning=The document explicitly states it serves both as a quarterly fee invoice and a capital
call notification. Therefore, the classification as 'capital_call' alone is ambiguous and potentially
incorrect. Critical information, such as the dual-purpose nature, is missing from the extracted
fields, necessitating human review.
```

---

### V3

**Prompt change:** Added few-shot example targeting conflicting due dates — labeled header field contradicts wire deadline in body text.

```
Example 2 — date conflict
Document contains: "Due Date: April 30, 2024" in header
Document body says: "wire funds no later than March 15, 2024. The April 30 date is for reconciliation purposes only"
Extracted due_date: 30-04-2024
Correct response: confidence=0.7, flag for human review
Reasoning: Extracted date matches labeled header field but contradicts explicit wire deadline in body.
Operational deadline takes precedence over reconciliation date.
```

**TC-1:** PASS (inherited from V2)
**TC-2:** PASS

```
confidence=0.7
reasoning=The due date extracted is April 30, 2024, which is a reconciliation date and not the
operational due date, which is March 15, 2024. Given the instructions to not use the reconciliation
date for wire scheduling, the extracted due date conflicts with the operational requirement.
Classification as a 'capital_call' is correct, but the date extraction requires human review
for correction.
```

---

<!-- TEMPLATE — copy block below for each new version

### VN

**Prompt change:** <what changed and why>

**TC-1:** PASS | FAIL
**TC-2:** PASS | FAIL

```
confidence=
reasoning=
```

-->
