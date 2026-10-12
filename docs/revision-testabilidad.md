# Testability review — Phase 0.3

**Purpose.** Static review of every requirement before a single line of code exists. This is
the earliest and cheapest quality activity available: a defect found in a requirement costs
minutes, the same defect found in production costs days.

**Technique.** Each requirement is checked against four questions. If any answer is "no", the
requirement is defective — not the test that would have caught it.

| Question | What it catches | Where the defect goes |
|---|---|---|
| **Claro** — is there only one possible interpretation? | Ambiguity that two developers resolve differently | Back to Phase 0.2 as a decision |
| **Medible** — is the result concrete and observable? | Statements that cannot become a test case with a pass/fail outcome | Rewritten in this phase |
| **Alcanzable** — is it buildable inside the closed scope? | Scope creep, and requirements that are impossible as written | Descoped, or decided in Phase 0.2 |
| **Consistente** — does it contradict another requirement? | Two documents that disagree, which no test will ever run | Fixed in this phase |

**Scope of this review:** 17 functional requirements, 16 non-functional requirements and
8 deliverables — 41 items.

---

## 1. Summary

| Verdict | Count | Meaning |
|---|---|---|
| APROBADO | 31 | Passes all four questions |
| OBSERVADO | 10 | At least one question failed; a defect is recorded below |
| **Total** | **41** | |

| Severity | Count |
|---|---|
| HIGH | 1 |
| MEDIUM | 6 |
| LOW | 3 |

---

## 2. Defects found

| ID | Requirement | Finding | Severity | Disposition |
|---|---|---|---|---|
| F-01 | RF-09 | The HTML page requires a token in the `Authorization` header. A browser navigation **cannot send that header**, so the page is reachable only by curl or a custom client — yet its own verification says "browser, authenticated". The requirement is not reachable as written, and it drifts from the brief's intent, which is a page the teacher opens. | **HIGH** | **RESOLVED** — Phase 0.2 revised D-04; the welcome page is now public and carries no data (§3) |
| F-02 | RF-14 | RF-14 declares that a 415 response uses the standard error shape, but RF-15 mandates **400** for a missing `Content-Type`. No requirement can ever produce a 415, so the contract advertises a status that does not exist. | MEDIUM | **FIXED** — 415 removed from RF-14; RF-15's 400 stands, consistent with D-12 |
| F-03 | RF-05 | The requirement says `/login` returns "a token" but never names the JSON field. The console client cannot be written against this, and a mismatch here is precisely the contract bug TP-17 exists to catch. | MEDIUM | **FIXED** — the field is named `token` |
| F-04 | RF-10 | The CRUD is listed by route and method only. Neither the request body for create/update nor the shape of a task in a response is defined, so the client and the API would diverge on field names — the same class of defect as F-03. | MEDIUM | **FIXED** — bodies and response shape specified; the owner id is never exposed |
| F-05 | RF-01 | States what is accepted, never what is rejected. A body missing `contraseña`, or sending a number instead of a string, has no defined outcome, so the requirement cannot be converted into a pass/fail case on its own. | MEDIUM | **FIXED** — rejection rule added (400) |
| F-06 | RF-17 | "Readable messages" and "never a stack trace" are partly subjective. Without a concrete criterion the requirement is not verifiable, and two reviewers would disagree about whether it passes. | MEDIUM | **FIXED** — the criterion is now a single-line message with the status code or the network failure, a non-zero exit code, and no traceback |
| F-07 | DEL-04 | "Screenshots of successful tests" does not say of what, or how many. As written it is satisfiable by one blurred image. | MEDIUM | **FIXED** — bound to the evidence plan, each capture carrying the command that produced it |
| F-08 | RNF-10 | The verification depends on a Windows console in `cp1252`. The requirement is correct, but its verification is environment-dependent, so it can pass on one machine and be untestable on another. | LOW | **ACCEPTED** — recorded as a known dependency on the local environment, not a defect to fix |
| F-09 | RNF-14 | Requires documentation in English, but the working plan is deliberately in Spanish. The rule does not carve out that exception, so a consistent reading of RNF-14 would flag the plan as a violation. | LOW | **ACCEPTED** — the plan is not a versioned project artifact (D-24), so it is outside the scope of "documentation of the project" |
| F-10 | RNF-15 | "No dependency without a requirement that demands it" is a process constraint verified by review, not a measurable outcome. It cannot become an automated test. | LOW | **ACCEPTED** — verified by code review; recorded so it is not mistaken for an untested requirement |

---

## 3. F-01 in detail — the defect that blocked a phase

The requirement says the page requires a valid token, and the token travels in the
`Authorization` header. That works for `curl`, for `requests`, and for `fetch()` from
JavaScript. It does **not** work for a browser navigation: when a person types a URL or clicks
a link, the browser sends cookies, not a bearer header. There is no way to authenticate a
plain page view with this scheme.

Consequences:

1. `GET /tareas` can only ever be demonstrated with a command-line client.
2. Evidence **E-04** ("browser, authenticated") cannot be produced as written. The evidence
   plan is therefore broken too, and that is a defect in its own right — the plan is what the
   brief asks to see.
3. The brief's intent is a page the teacher opens in a browser. As written, the requirement
   satisfies the letter of the brief while failing its purpose.

**Note the shape of this defect.** It was invisible in Phase 0.1 and in the code that does not
exist yet. It only appeared by asking "can this actually be reached?" — the *alcanzable*
question. This is the entire reason a testability review runs before implementation instead of
after it.

### Options considered

| Option | How it works | Cost |
|---|---|---|
| **A — Public landing page, protected data** (recommended) | `GET /tareas` becomes a public welcome page with no data on it. The JSON CRUD at `/api/tareas` stays fully protected. A *welcome* page has nothing to protect, so this matches both the brief's wording and its intent. | Revises D-04 (which said `/tareas` is protected) and inverts TP-21's HTML half: it would then assert 200 **without** a token, which is the assertion a browser can actually satisfy. |
| B — Cookie plus header | `/login` also sets a session cookie, and the HTML route accepts either the header or the cookie. | Adds cookie handling to the scope: new surface, new tests, and cookie security questions (`HttpOnly`, `Secure`, `SameSite`) that the brief never asks for. Contradicts D-17's non-goals. |
| C — Accept curl-only | Keep the requirement; change E-04 to a curl capture and document that the page is not browser-reachable. | Cheapest in code, but ships a page no human can open — a poor look for the graded deliverable, and dishonest evidence. |

The recommendation is **A**: a welcome page exists to be read, not to be guarded, and the
guarding requirement was only ever about the data.

### Resolution — 2026-10-12

Option **A** was chosen. D-04 is revised in `docs/decisiones.md` §7: the CRUD routes keep
requiring a token and keep isolating data per owner, and `GET /tareas` becomes a public page
with no data on it. RF-09 was rewritten accordingly, so the requirement, the decision and the
test now say the same thing.

Note carefully what this changed and what it did not. It did **not** weaken security: the page
it unguards never carried a task, a user, or anything else worth reading. It removed a rule
that was protecting an empty document while simultaneously making that document impossible to
open. *A control over a resource with nothing in it does not add protection — it adds the
illusion of protection.* This is the defect that would have sailed through a review which only
asked "is there a control here?" and never asked "what does this control actually protect, and
can anyone reach it?"

---

## 4. Checklist matrix

`✓` = passes the question · `✗` = fails, see the defect column

| ID | Claro | Medible | Alcanzable | Consistente | Verdict | Defect |
|---|---|---|---|---|---|---|
| RF-01 | ✗ | ✓ | ✓ | ✓ | OBSERVADO | F-05 |
| RF-02 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-03 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-04 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-05 | ✗ | ✓ | ✓ | ✓ | OBSERVADO | F-03 |
| RF-06 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-07 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-08 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-09 | ✓ | ✓ | ✗ | ✗ | OBSERVADO | **F-01** |
| RF-10 | ✗ | ✓ | ✓ | ✓ | OBSERVADO | F-04 |
| RF-11 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-12 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-13 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-14 | ✓ | ✓ | ✓ | ✗ | OBSERVADO | F-02 |
| RF-15 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-16 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RF-17 | ✗ | ✗ | ✓ | ✓ | OBSERVADO | F-06 |
| RNF-01 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-02 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-03 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-04 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-05 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-06 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-07 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-08 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-09 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-10 | ✓ | ✗ | ✓ | ✓ | OBSERVADO | F-08 |
| RNF-11 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-12 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-13 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| RNF-14 | ✓ | ✓ | ✓ | ✗ | OBSERVADO | F-09 |
| RNF-15 | ✓ | ✗ | ✓ | ✓ | OBSERVADO | F-10 |
| RNF-16 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-01 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-02 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-03 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-04 | ✗ | ✗ | ✓ | ✓ | OBSERVADO | F-07 |
| DEL-05 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-06 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-07 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |
| DEL-08 | ✓ | ✓ | ✓ | ✓ | APROBADO | — |

---

## 5. Accepted observations (F-08, F-09, F-10)

These are recorded rather than fixed. A review that fixes everything it finds is usually a
review that found nothing: some observations are properties of the environment or the process,
and the honest action is to name them and move on.

| ID | Why it stays as it is |
|---|---|
| F-08 | The requirement is correct; only the *proof* depends on a Windows console. Any machine can assert UTF-8 handling over HTTP; the console part is verified once, on the target machine, with its own evidence. |
| F-09 | The Spanish working plan is not versioned (D-24), so it is not project documentation. Documenting the carve-out here is the carve-out. |
| F-10 | A process constraint cannot be automated, and pretending otherwise would create a test that verifies nothing. Review is the correct verification method for it. |

---

## 6. Corrections applied in this phase

These were unambiguous — they make a requirement precise without changing any decision — so
they were applied directly. F-01 needed a decision, so it waited; it appears below as well,
marked as such.

| Defect | Requirement | What changed |
|---|---|---|
| F-02 | RF-14 | 415 removed from the list of statuses using the standard error shape |
| F-03 | RF-05 | The response field is named: `token` |
| F-04 | RF-10 | Create/update bodies and the task response shape defined; the owner id is not exposed |
| F-05 | RF-01 | Rejection rule added: missing field or non-string field → 400 |
| F-06 | RF-17 | Rewritten to a measurable criterion |
| F-07 | DEL-04 | Bound to the evidence plan, each capture carrying its command |
| F-01 | RF-09 | **Applied after the D-04 revision:** the page is public, it carries no data, and its test asserts both facts |

---

## 7. Re-verification status

| Item | Status |
|---|---|
| RF-01, RF-05, RF-10, RF-14, RF-17, DEL-04 | **Corrected.** Each is now expressible as a test case with a concrete expected result. |
| RF-09 (F-01) | **Corrected after the decision.** `GET /tareas` is public, carries no data, and its test asserts exactly that. Recorded as D-04 revisada in `docs/decisiones.md` §7. |
| Evidence plan (E-04) | **Unblocked.** It becomes a plain browser capture with no authentication — which is now the very reason the page exists. |
| TP-10 | Unaffected. It tests an expired token on a route that still requires one. |
| TP-21 | **Reworded.** It no longer asserts that both representations are protected. It now asserts that the HTML page returns 200 **without** a token and leaks no task data, while the JSON CRUD still returns 401 without one. |
| TP-18 | **Reworded.** It said `400/415`; F-02 established that 415 is never produced by any requirement, so it now asserts 400 only. |

**Phase 0.3 gate: closed.** All 10 findings are disposed — 7 corrected, 3 accepted and
documented. Every requirement can now be turned into a test case with a concrete expected
result, which is the exit criterion this phase was defined by.

**Handed to Phase 1.2:** `docs/api.md` must state that `/api/tareas` requires a token on every
method and that `/tareas` does not. That is now the only open consequence, and it is a
documentation task, not a decision.
