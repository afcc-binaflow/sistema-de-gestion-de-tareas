# Requirements — PFO 2

**Purpose.** Single, numbered source of truth for what the system must do (RF) and how it
must behave (RNF). Every requirement has a stable ID so it can be cited from the API
contract, the test suite, the traceability matrix, and commit messages.

**How this document is used.**

| Phase | Use |
|---|---|
| 0.2 | Decisions referenced here (`D-xx`) are consolidated into `docs/decisiones.md` |
| 0.3 | Testability review runs over this table, requirement by requirement. Findings and corrections: `docs/revision-testabilidad.md` |
| 0.4 | Priority column feeds the risk matrix |
| 1.2 | `docs/api.md` must satisfy every RF in the "Verification" column |
| 9.2 | Traceability matrix requires every RF to map to at least one test |

**Source column:** `CONSIGNA` = stated in the assignment brief · `D-xx` = scope decision,
walked through the analysis in Phase 0.2 and consolidated in `docs/decisiones.md` ·
`AGENTS.md` = project engineering contract.

**Priority:** `P1` = security, integrity, or critical path · `P2` = core functionality ·
`P3` = quality and deliverables.

---

## Functional requirements

| ID | Requirement | Source | Verification | TP | Prio |
|---|---|---|---|---|---|
| RF-01 | The API accepts `POST /registro` with a JSON body containing the string fields `usuario` and `contraseña`. A body missing either field, or where either field is not a string, is rejected with 400. | CONSIGNA | Valid body → 201; missing field and non-string field → 400 | TP-02 | P1 |
| RF-02 | A successful registration persists the user with the password stored as a hash produced by the hashing library. The plaintext password is never persisted in any column. | CONSIGNA, D-14 | Inspect `usuarios.password_hash` in the DB; assert it differs from the input | TP-04 | P1 |
| RF-03 | `usuario` is unique and the comparison is case-insensitive: registering `juan` when `Juan` already exists is rejected with 409. | D-11 | Integration → 409; DAO → `IntegrityError` | TP-03, TP-19 | P1 |
| RF-04 | The `/registro` response body never contains the password or its hash. | CONSIGNA (implied), RNF-06 | Assert response keys; search body for the plaintext and the hash | TP-05 | P1 |
| RF-05 | The API accepts `POST /login` with `usuario` and `contraseña` and returns 200 with the token in a JSON field named `token` when the credentials match a stored user. | CONSIGNA | Valid credentials → 200 and a non-empty `token` field | TP-06, TP-17 | P1 |
| RF-06 | When the user does not exist, and when the password is wrong, `/login` returns 401 with a **byte-identical** body in both cases. | D-09, RNF-06 | Two tests, bodies compared for equality | TP-07 | P1 |
| RF-07 | The token issued by `/login` is a JWT signed with the server's `SECRET_KEY`, carrying `sub` (user id as a string), `iat` and `exp` (8 hours after issue, D-20). | D-03, D-20 | Unit: decode → claims present and signature valid | TP-08, TP-09 | P1 |
| RF-08 | Any request to a protected route with a missing, malformed, tampered, or expired token is rejected with 401. | D-04, D-09 | Integration with four token variants | TP-08, TP-09, TP-10 | P1 |
| RF-09 | `GET /tareas` returns a **public** welcome HTML document (`text/html`), with no authentication and no user data on it (D-04 revisada). | CONSIGNA, D-06, D-04 revisada | Without any header → 200 + `text/html`; the body carries no task data | TP-21 | P2 |
| RF-10 | The API exposes the task CRUD as JSON under `/api/tareas`: create (`POST /api/tareas`), list own (`GET /api/tareas`), read one (`GET /api/tareas/<id>`), update (`PUT /api/tareas/<id>`), delete (`DELETE /api/tareas/<id>`). Create and update accept `{"titulo": <string>}` and optionally `completada` (boolean, default false). A task in a response is `{"id", "titulo", "completada"}`; the owner id is never exposed. | D-01, D-06 | Full create→list→read→update→delete cycle; assert the exact response keys | TP-13, TP-17 | P2 |
| RF-11 | `GET /api/tareas` returns only the tasks owned by the authenticated user. | D-04 | Two users create tasks; each list contains only its own | TP-11 | P1 |
| RF-12 | Reading, updating, or deleting a task owned by another user returns 404, even though that task exists. | D-07 | A targets B's task via GET, PUT and DELETE → 404 | TP-11 | P1 |
| RF-13 | A task requires a non-empty `titulo` of at most 200 characters (D-19). A missing, empty, over-length, or non-string value is rejected with 400. | CONSIGNA (implied), D-19 | Four invalid bodies → 400 | TP-12 | P2 |
| RF-14 | Every error response uses the same JSON shape `{"error": "<mensaje>"}` with `Content-Type: application/json`, for 400, 401, 404, 405, 409 and 500. | R-04, D-09 | Parameterized test over each status code | TP-16, TP-22 | P2 |
| RF-15 | A malformed JSON body, or a JSON endpoint called without a JSON `Content-Type`, returns 400 — never a 500 and never an HTML error page. | R-07, D-12 | Malformed body and missing header → 400 | TP-18 | P2 |
| RF-16 | The console client can register, log in, and perform the full task CRUD against the API, keeping the token in memory for the session only. | D-05, D-17 | E2E test against the app test client | TP-17 | P2 |
| RF-17 | On a network failure or an HTTP error, the console client prints one line naming the failure — the HTTP status code together with the API's `error` value, or the network failure itself — and exits with a non-zero code. It never prints a traceback and never fails silently. | D-17 | E2E with the API unreachable; forced 400 and 401 responses | TP-17 | P2 |

---

## Non-functional requirements

| ID | Requirement | Source | Verification | TP | Prio |
|---|---|---|---|---|---|
| RNF-01 | Passwords are hashed with a library (`werkzeug.security`), never stored, returned, or logged in plaintext. | CONSIGNA | Inspection test; response-body scan | TP-04, TP-05 | P1 |
| RNF-02 | Persistence uses SQLite through the standard library. No external database server. | CONSIGNA | Code review; no DB service in the deploy | TP-15 | P1 |
| RNF-03 | `SECRET_KEY` and the database path come from the environment. No secret is hardcoded in a tracked file. | AGENTS.md, D-13 | Secret scan over the working tree and the full Git history | — | P1 |
| RNF-04 | HTTP status codes are semantically correct and consistent across endpoints (201 created, 400 invalid input, 401 unauthenticated, 404 not found or not yours, 405 wrong method, 409 conflict, 500 internal). | R-04 | Contract tests per endpoint | TP-01, TP-22 | P2 |
| RNF-05 | Every SQL statement uses parameter binding. No query is assembled by string interpolation. | AGENTS.md | `' OR 1=1 --` test plus code review of every statement | TP-14 | P1 |
| RNF-06 | No response or error exposes the password hash, a stack trace, internal file paths, or the `SECRET_KEY`. | R-05, AGENTS.md | Leak tests plus a forced 500 | TP-16 | P1 |
| RNF-07 | Referential integrity is enforced by SQLite: `PRAGMA foreign_keys = ON` on every connection, so a task cannot reference a nonexistent user and deleting a user cascades to its tasks. | D-11, TP-20 | DAO test with an invalid `usuario_id` → `IntegrityError`; cascade test | TP-20 | P1 |
| RNF-08 | JWT verification uses an explicit algorithm allowlist. `alg: none` and algorithm substitution are rejected. | TP-08 | Unit: token with `alg: none`, and a token signed with another key → rejected | TP-08 | P1 |
| RNF-09 | Tokens carry an expiry (`exp`) that the server enforces. | D-03 | Unit: token generated with a past `exp` → rejected | TP-09 | P1 |
| RNF-10 | Text is handled as UTF-8 end to end: `contraseña` with `ñ` works from HTTP clients and from the Windows console. | TP-23 | E2E register + login with a `ñ` password | TP-23 | P2 |
| RNF-11 | Layers are separated per the AGENTS.md SRP mapping: config, database access, security, HTTP routes, client. No function mixes HTTP parsing with SQL or hashing. | AGENTS.md | Code review per module | — | P2 |
| RNF-12 | The test suite runs with pytest against an in-memory or temporary database and never touches the production database file. | AGENTS.md | Fixture review; assert the production file is unmodified after a full run | — | P1 |
| RNF-13 | The project is reproducible: pinned dependency versions, a documented Python version, and a README that works from a clean clone. | AGENTS.md | Clean-environment walkthrough (10.3) | — | P2 |
| RNF-14 | Documentation is written in English. Code identifiers, test names, docstrings and commit messages are written in Spanish. | AGENTS.md | Review per artifact | — | P3 |
| RNF-15 | No dependency is added without a requirement that demands it. Each entry in `requirements.txt` is justified. | AGENTS.md | Review of `requirements.txt` | — | P2 |
| RNF-16 | The deployment mitigates SQLite's concurrency limit by running a single worker process with threads, not multiple processes. | TP-15, D-08 | Review of the deployed run command | TP-15 | P2 |

---

## Assignment deliverables

Requirement IDs are separate from RF/RNF: these are hand-in items, not system behaviour.

| ID | Deliverable | Source | Evidence |
|---|---|---|---|
| DEL-01 | `servidor.py` — Flask API plus SQLite. It exists as the runnable entry point. | CONSIGNA | E-03; see A-04 |
| DEL-02 | Console client. | D-05 | E-05 |
| DEL-03 | `README.md` with instructions to run and test the project. | CONSIGNA | E-01, 10.3 walkthrough |
| DEL-04 | Screenshots of successful tests, per the evidence plan (E-01 … E-08). Each capture carries the command that produced it. | CONSIGNA | E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-08 |
| DEL-05 | Repository published on GitHub. | CONSIGNA | Repo URL |
| DEL-06 | Project hosted on GitHub Pages. | CONSIGNA | E-08 for the static site |
| DEL-07 | Written answers: why hash passwords, and the advantages of SQLite here. | CONSIGNA | `docs/respuestas-conceptuales.md` |
| DEL-08 | Working API on a public Python runtime (PythonAnywhere, per D-08). | CONSIGNA, D-08 | Post-deploy smoke test |

---

## Out of scope (explicit non-goals, D-17)

Declaring these is deliberate: it shows the scope was decided on purpose rather than cut
by lack of time.

CORS · refresh tokens · token revocation / server-side logout blacklist · rate limiting ·
roles and permissions beyond owner isolation · pagination · search and filtering · an ORM ·
Docker · caching · background jobs · async · admin panel · `PATCH` semantics.

---

## Previously open values (resolved in Phase 0.2)

These were deliberately left open in Phase 0.1. Phase 0.2 closed all of them; the decision
that resolved each one is recorded in `docs/decisiones.md` with its rationale.

| ID | Item | Resolution |
|---|---|---|
| A-01 | Maximum `titulo` length | **D-19** — 200 characters |
| A-02 | Password policy | **D-14** — non-empty only, so the brief's `1234` example keeps working |
| A-03 | `usuario` whitespace handling | **D-21** — `usuario` is stripped; `contraseña` is never stripped |
| A-04 | `servidor.py` entry point vs. separated responsibilities | **D-18** — the entry point composes separate modules |
| A-05 | Token lifetime | **D-20** — 8 hours |
| A-06 | `completada` goes beyond the brief | **D-22** — kept; must be declared in the README |
| A-07 | `DELETE` returns 204 with an empty body | **D-23** — confirmed; materialised in `docs/api.md` (Phase 1.2) |
| A-08 | Trailing-slash behaviour | **D-23** — strict, one documented behaviour |

The Phase 0.3 testability review no longer has open values to resolve. Its job is now to
review the requirement statements themselves — clarity, measurability, reachability and
consistency — and to return any defective requirement to Phase 0.2.

---

## Traceability seed (RF → TP)

Forward link only. The full matrix `RF ↔ TP ↔ TC ↔ test file ↔ result` is built in Phase 9.2.

| TP | Covered by |
|---|---|
| TP-01 | RF-14, RNF-04 |
| TP-02 | RF-01, RF-15 |
| TP-03 | RF-03 |
| TP-04 | RF-02, RNF-01 |
| TP-05 | RF-04, RNF-01 |
| TP-06 | RF-05 |
| TP-07 | RF-06 |
| TP-08 | RF-07, RF-08, RNF-08 |
| TP-09 | RF-07, RF-08, RNF-09 |
| TP-10 | RF-08 |
| TP-11 | RF-11, RF-12 |
| TP-12 | RF-13 |
| TP-13 | RF-10 |
| TP-14 | RNF-05 |
| TP-15 | RNF-02, RNF-16 |
| TP-16 | RF-14, RNF-06 |
| TP-17 | RF-16, RF-17 |
| TP-18 | RF-15 |
| TP-19 | RF-03 |
| TP-20 | RNF-07 |
| TP-21 | RF-09, RF-10 |
| TP-22 | RF-14, RNF-04 |
| TP-23 | RNF-10 |
| TP-24 | A-02, RF-01 |
| TP-25 | RF-16, D-17 |
