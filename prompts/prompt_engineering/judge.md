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

### TC-3 — Partial Payment

```
CAPITAL CALL NOTICE
Alter Domus Fund VI Management LLC

Notice Date: April 1, 2024
Due Date: April 20, 2024
Reference: CC-2024-0061
To: Harborview Institutional Fund LP
From: Alter Domus Fund VI Management LLC

Dear Limited Partner,

Pursuant to the Limited Partnership Agreement, this notice confirms Capital Call #4 in the
amount of $1,000,000. As per our records, a partial remittance was received on March 20, 2024.
Please wire the remaining portion of your commitment by the due date specified above to avoid
default provisions.

Your account reflects a credit of $400,000 applied against the original call. Please ensure the
balance is settled no later than April 20, 2024.

Capital Call Amount: $1,000,000

Wire Instructions:
Bank: Wells Fargo Bank NA
ABA: 121000248
Account: 8841930076
Ref: CC-2024-0061

Please reference CC-2024-0061 in your wire instructions. Contact investor.relations@alterdomus.com
for any queries regarding your payment history.

Alter Domus Fund VI Management LLC
```

**Expected:** `confidence <= 0.7`, flagged for human review — extracted amount reflects original call ($1,000,000) but body confirms a $400,000 partial payment was already received, so the outstanding balance is $600,000.

---

## Versions

### V1

**Prompt change:** Baseline — scoring rubric only, no ambiguity handling.

**TC-1:** FAIL
**TC-2:** FAIL (non-deterministic — same document returned `confidence=0.92` on some runs, slipping through to `completed` with wrong `due_date=30-04-2024`)
**TC-3:** UNTESTED

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
**TC-3:** UNTESTED

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
**TC-3:** FAIL

```
confidence=0.95
reasoning=The document is clearly a capital call notice, as explicitly stated in the document header
and body. All expected fields are present, and the due date is consistent with the document's
details. This aligns unambiguously with the classification of a capital call document.
```

---

### V4

**Prompt change:** Added few-shot example targeting partial payments — original call amount is prominent but body references a prior partial payment received.

```
Example 3 — partial payment
Document states original call amount prominently but body text references
a prior partial payment received.
Extracted amount: 1000000
Correct response: confidence=0.7, flag for human review
Reasoning: Document contains evidence of prior partial payment. Extracted
amount reflects original call, not outstanding balance. Human review required
to confirm correct wire amount.
```

**TC-1:** PASS (inherited from V3)
**TC-2:** PASS (inherited from V3)
**TC-3:** PASS

```
confidence=0.7
reasoning=The document is correctly classified as a capital call. However, the extracted amount
reflects the original call of $1,000,000, while the document mentions a partial payment received
and a balance remaining. Therefore, it requires human review to determine the correct outstanding
balance to be wired.
```

---

<!-- TEMPLATE — copy block below for each new version

### VN

**Prompt change:** <what changed and why>

**TC-1:** PASS | FAIL
**TC-2:** PASS | FAIL
**TC-3:** PASS | FAIL

```
confidence=
reasoning=
```

-->
