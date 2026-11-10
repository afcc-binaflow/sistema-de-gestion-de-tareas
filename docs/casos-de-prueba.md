# Test case catalogue — Phase 1.6

**Purpose.** Turn the 25 test points (`TP-xx`) into concrete, individually verifiable test
cases (`TC-xx`), each with the technique that generated it and the exact expected result,
**before** the code that they exercise exists.

**Why this document is versioned.** `docs/requisitos.md` cites `TP-xx` 54 times and
`docs/matriz-de-riesgo.md` 44 times. Those IDs were defined only in the working plan, which is
not versioned (D-24). A requirement that cites an undefined ID is an unverifiable requirement:
this file is where the catalog becomes part of the repository.

**Status.** Phase 1.6. Every case below is **specified, not yet implemented**. The "File" column
names the test module that will hold it; the "Phase" column, the phase that makes it runnable.

**Satisfies:** the traceability obligation of RF-14/RNF-04, the deliverables DEL-04 and DEL-03,
and the "test-as-you-go" rule of `AGENTS.md`. Completed with results in Phase 9.2.

---

## 1. Method

Four techniques from ISTQB CTFL, applied deliberately per case rather than by intuition:

| Technique | What it generates | Where it earns its place here |
|---|---|---|
| **Equivalence partitioning** | One representative per valid/invalid class | Request bodies: valid, missing field, wrong type, malformed JSON |
| **Boundary value analysis** | The edges of each partition | `titulo` at 200 and 201 characters · empty and whitespace-only strings · `exp` in the past · the brief's own `1234` |
| **Decision table** | Combinations of conditions with a distinct outcome | `/registro`: field present × is string × non-empty after rules → 201 / 400 / 409 |
| **State transition / use case** | Ordered sequences across states | The CRUD cycle, and the IDOR sequence (A authenticated, B's resource) |

Two further rules shape the catalog:

1. **Every negative case asserts the *specific* outcome, not just "not 200".** A test that
   accepts either 400 or 409 while the contract pins 409 proves nothing about the contract.
2. **A case is derived from `docs/api.md`, never from the implementation.** A test written
   after reading the code only proves the code agrees with itself.

### What a case is not

A test case is not a test *name*. Several cases may share one test function (a parameterized
test over the four invalid bodies of RF-13), and one case may need several assertions (a task
response must both have the right keys *and* not contain `usuario_id`). The ID exists so the
case can be cited, counted and traced — not so each one becomes a separate function.

---

## 2. Test point catalogue

The 25 test points, with the risk band assigned in `docs/matriz-de-riesgo.md` and the layer that
can observe them. Layer matters: a case asserted through the HTTP client cannot prove that a
foreign-key `PRAGMA` is on, and a case asserted against the DAO cannot prove the wire contract.

| TP | Area | Band | Observable at | Requirement | What it verifies |
|---|---|---|---|---|---|
| TP-01 | Routing | Medium | HTTP | RF-14, RNF-04 | Existing route + wrong method → 405; unknown route → 404 |
| TP-02 | Validation | High | HTTP | RF-01 | Registration body: presence, type, emptiness, length |
| TP-03 | Uniqueness | High | HTTP + DAO | RF-03 | Duplicate `usuario` → 409 / `IntegrityError` |
| TP-04 | Hashing | High `floor` | DAO + unit | RF-02, RNF-01 | Stored value ≠ plaintext; salt makes two hashes differ |
| TP-05 | Response shape | High | HTTP | RF-04, RNF-06 | `password_hash` and plaintext never travel to the client |
| TP-06 | Login | Medium | HTTP | RF-05 | Valid credentials → 200 with `token` |
| TP-07 | Enumeration | High | HTTP | RF-06 | Unknown user and wrong password → byte-identical 401 |
| TP-08 | Token integrity | High | Unit + HTTP | RF-07, RF-08, RNF-08 | Valid signature accepted; tampered, foreign-key-signed and `alg: none` rejected |
| TP-09 | Token lifetime | High | Unit + HTTP | RNF-09 | `exp` in the past → rejected |
| TP-10 | Middleware | High | HTTP | RF-08 | Every protected route rejects a missing/malformed token |
| TP-11 | Authorization | **Critical** | HTTP + DAO | RF-11, RF-12 | A cannot read, edit, delete or list B's tasks (404, and the filter lives in SQL) |
| TP-12 | Task validation | Medium | HTTP | RF-13 | `titulo`: missing, empty, whitespace-only, non-string, 200 and 201 chars |
| TP-13 | CRUD flow | Medium | HTTP | RF-10 | Create → list → read → update → delete, exact payload shapes |
| TP-14 | SQL injection | High `floor` | DAO | RNF-05 | `' OR 1=1 --` has no effect; every statement is parameterized |
| TP-15 | Persistence | High | DAO + deploy | RNF-02, RNF-16 | Concurrent writes do not corrupt; single worker with threads |
| TP-16 | Error handling | High | HTTP | RF-14, RNF-06 | 500 is JSON, carries no traceback, and is logged server-side |
| TP-17 | Client contract | High | E2E | RF-16, RF-17 | Field names and status codes match `docs/api.md`; failures are one line |
| TP-18 | Input handling | Medium | HTTP | RF-15 | Malformed JSON or missing `Content-Type` → 400, never 415 HTML |
| TP-19 | Case-insensitive uniqueness | High | HTTP + DAO | RF-03 | `Juan` and `juan` collide |
| TP-20 | Referential integrity | High | DAO | RNF-07 | Orphan task rejected; delete cascades |
| TP-21 | Representation | High | HTTP | RF-09, RF-10 | Welcome page is public, HTML, and carries no user data |
| TP-22 | Error shape | Medium | HTTP | RF-14, RNF-04 | 404/405/500 all answer `{"error": ...}` as JSON |
| TP-23 | Encoding | Medium | E2E | RNF-10 | `contraseña` with `ñ` survives console → HTTP → SQLite |
| TP-24 | Scope boundary | Medium | HTTP | RF-01, D-14 | The brief's `1234` password is accepted |
| TP-25 | Session | Low | E2E + docs | RF-16, D-17 | Logout is client-side only; the limitation is documented |

**Execution order is not risk order** (matrix §4). The dependency chain — TP-02 before TP-06,
TP-06 before TP-08/09/10/11 — decides *when* a case can run. Effort still follows the band.

---

## 3. Test cases by module

Each table: the case, the test point it belongs to, the technique, the precondition and input,
and the outcome that must be observed. Strings in `contraseña`/`titulo` are quoted exactly as
the API sees them.

### 3.1 Registration — `tests/test_registro.py` (Phase 5)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-REG-01 | TP-02 | Equivalence | `{"usuario": "juan", "contraseña": "1234"}` | 201; body has **exactly** the key `usuario` |
| TC-REG-02 | TP-02 | Equivalence | body without `contraseña` | 400 |
| TC-REG-03 | TP-02 | Equivalence | body without `usuario` | 400 |
| TC-REG-04 | TP-02 | Equivalence | `usuario: 123` | 400 |
| TC-REG-05 | TP-02 | Equivalence | `contraseña: null` | 400 |
| TC-REG-06 | TP-02 | Boundary | `usuario: ""` | 400 (RF-01 revisada) |
| TC-REG-07 | TP-18 | Equivalence | valid body sent with `Content-Type: text/plain` | 400 (not 415, not 201) |
| TC-REG-08 | TP-24 | Boundary | `contraseña: "1234"` — the brief's own example | 201 |
| TC-REG-09 | TP-19 | Decision | `Juan` exists; register `juan` | 409 |
| TC-REG-10 | TP-02 | Boundary | `usuario: "  juan  "` | 201; response `usuario` is `"juan"` (stripped, D-21) |
| TC-REG-11 | TP-02 | Boundary | `usuario: "   "` | 400 (empty after stripping) |
| TC-REG-12 | TP-03 | State | register the same `usuario` twice | 409 |
| TC-REG-13 | TP-05 | Negative scan | valid registration | body contains neither `password_hash` nor the plaintext, in any key or header |
| TC-REG-14 | TP-18 | Negative | body `{"usuario": ` (truncated) with JSON content type | 400, JSON error, no traceback |
| TC-REG-15 | TP-01 | Decision | `GET /registro` | 405 |
| TC-REG-16 | TP-02 | Boundary | `contraseña: ""` | 400 (D-14) |

### 3.2 Login — `tests/test_login.py` (Phase 6)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-LOG-01 | TP-06 | Equivalence | registered user, correct password | 200; `token` present, non-empty, and the only key |
| TC-LOG-02 | TP-07 | Equivalence | correct user, wrong password | 401 |
| TC-LOG-03 | TP-07 | Equivalence | user that was never registered | 401 |
| TC-LOG-04 | TP-07 | Oracle | compare `(status, raw body)` of TC-LOG-02 and TC-LOG-03 | **byte-identical** |
| TC-LOG-05 | TP-18 | Negative | malformed JSON body | 400 |
| TC-LOG-06 | TP-24 | Boundary | log in with `"1234"` | 200 |
| TC-LOG-07 | TP-02 | Boundary | user registered with `contraseña: " 1234 "`; log in with `" 1234 "` then with `"1234"` | 200, then **401** — the password is never stripped (D-21) |
| TC-LOG-08 | TP-02 | Equivalence | body without `contraseña` | 400 |
| TC-LOG-09 | TP-01 | Decision | `GET /login` | 405 |

### 3.3 Token and authentication - `tests/test_seguridad.py`, `tests/test_autorizacion.py` (Phase 4, 7)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-TOK-01 | TP-08 | Equivalence | decode a token issued by `crear_token` | `sub` equals the user id **as a string**; `iat` and `exp` present; `exp − iat` = 8 h |
| TC-TOK-02 | TP-08 | Fault injection | flip one character of the signature | rejected |
| TC-TOK-03 | TP-08 | Fault injection | token signed with a different `SECRET_KEY` | rejected |
| TC-TOK-04 | TP-08 | Fault injection | unsigned token with `alg: none` | rejected (RNF-08) |
| TC-TOK-05 | TP-09 | Boundary | token created with `exp` already in the past | rejected |
| TC-TOK-06 | TP-05 | Inspection | decode the payload as base64 | no password, no hash, no `SECRET_KEY` |
| TC-AUT-01 | TP-10 | Authorization | `GET /api/tareas` with no `Authorization` header | 401 |
| TC-AUT-02 | TP-10 | Parameterized | the five CRUD routes, each with no header | 401 on all five |
| TC-AUT-03 | TP-10 | Boundary | `Bearer` with empty token · `Basic x` · raw token without the `Bearer` prefix · `Bearer` followed only by spaces | 401 on each. **Not** a 401: `Bearer  <token>` with a double space, which RFC 7235 §2.1 allows (`1*SP`) |
| TC-AUT-04 | TP-21 | Exception | `GET /tareas` with no header | 200 — the one route that is public by design |
| TC-AUT-05 | TP-08 | Fault injection | a JWT signed with the real key but **without `exp`** | 401 — `decodificar_token` requires the claim, so D-20 cannot be bypassed by omission |
| TC-AUT-06 | TP-01 | Decision | `OPTIONS /api/tareas` and `OPTIONS /api/tareas/1` | 405 with a JSON body — Flask's automatic `OPTIONS` is disabled (`docs/api.md` §7, value 10) |

### 3.4 Task CRUD — `tests/test_tareas.py` (Phase 7)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-TAR-01 | TP-13 | Use case | `POST /api/tareas {"titulo": "Estudiar SQLite"}` | 201; keys exactly `{id, titulo, completada}`; `completada` is `false`; no `usuario_id` |
| TC-TAR-02 | TP-13 | Use case | create → list → read → update → delete | 201 → 200 → 200 → 200 → 204 |
| TC-TAR-03 | TP-13 | Boundary | `GET /api/tareas` with no tasks | 200 and `[]` — never 404 |
| TC-TAR-04 | TP-13 | Contract | `DELETE` | 204, **empty body**, no `Content-Type` (D-23) |
| TC-TAR-05 | TP-12 | Equivalence | no `titulo` | 400 |
| TC-TAR-06 | TP-12 | Boundary | `titulo: ""` | 400 |
| TC-TAR-07 | TP-12 | Boundary | `titulo: "   "` | 400 (RF-13 revisada) |
| TC-TAR-08 | TP-12 | Equivalence | `titulo: 42` | 400 |
| TC-TAR-09 | TP-12 | Boundary | `titulo` of exactly 200 characters | 201 (the limit is inclusive) |
| TC-TAR-10 | TP-12 | Boundary | `titulo` of 201 characters | 400 |
| TC-TAR-11 | TP-12 | Equivalence | `completada: "si"` | 400 |
| TC-TAR-12 | TP-12 | Fidelity | `titulo: "  hola  "` | 201 and the stored/returned title is **`"hola"`** — validated after stripping, stored stripped (`docs/api.md` §7, value 8) |
| TC-TAR-13 | TP-11 | Authorization (IDOR) | A requests B's task with `GET` | **404**, not 403, not 200 |
| TC-TAR-14 | TP-11 | Authorization (IDOR) | A updates B's task with `PUT` | 404, and the task is unchanged afterwards |
| TC-TAR-15 | TP-11 | Authorization (IDOR) | A deletes B's task with `DELETE` | 404, and the task still exists for B |
| TC-TAR-16 | TP-11 | Authorization (IDOR) | A lists tasks while B has tasks | only A's tasks, by count and by id |
| TC-TAR-17 | TP-11 | Authorization | A creates a task with `usuario_id` = B's id in the body | 201 and the task belongs to **A** — the body field is ignored |
| TC-TAR-18 | TP-01 | Decision | `PATCH /api/tareas/1` | 405 (PATCH is a non-goal) |
| TC-TAR-19 | TP-13 | Boundary | `GET`/`PUT`/`DELETE /api/tareas/9223372036854775808` (`2^63`) | 404 JSON — an id SQLite cannot store cannot exist, and the driver would raise on it |

### 3.5 Errors — `tests/test_errores.py` (Phase 7.5)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-ERR-01 | TP-16 | Fault injection | `monkeypatch` the DAO to raise, then hit a protected route with a valid token | 500; JSON body; no traceback, no file path, no `SECRET_KEY`; the exception appears in the server log (`caplog`) |
| TC-ERR-02 | TP-22 | Negative | `GET /api/tareas/999` with a valid token | 404 with `{"error": ...}` |
| TC-ERR-03 | TP-22 | Negative | `GET /ruta-inexistente` | 404 JSON — not Flask's HTML page |
| TC-ERR-04 | TP-22 | Decision | `PUT /registro` | 405 JSON |
| TC-ERR-05 | TP-14 | Invariant | every error response produced anywhere in the suite | top-level keys are exactly `{"error"}`; `Content-Type` is `application/json` |

*TC-ERR-05 is implemented as a shared assertion helper used by the other error cases, not as one
test that walks the whole suite. It exists as a case because "one error shape" (RF-14) is a
contract property that has to be checked in more than one place.*

### 3.6 Persistence — `tests/test_db.py` (Phase 3)

Asserted against a connection, not through HTTP: these properties are invisible from above.

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-DB-01 | TP-20 | Integrity | insert a task with a `usuario_id` that does not exist | `IntegrityError` |
| TC-DB-02 | TP-20 | State | delete a user that owns tasks | zero orphan tasks (`ON DELETE CASCADE`) |
| TC-DB-03 | TP-03 | Constraint | insert the same `usuario` twice | `IntegrityError` |
| TC-DB-04 | TP-19 | Collation | insert `Juan`, then `juan` | `IntegrityError` (`COLLATE NOCASE`) |
| TC-DB-05 | TP-14 | Injection | insert `usuario` = `' OR 1=1 --`, then query by name | user stored literally; other rows intact; nothing deleted |
| TC-DB-06 | TP-04 | Inspection | register through the API, then read `password_hash` from the table | the stored value differs from the plaintext (this is the only proof; the API never shows it) |
| TC-DB-07 | TP-11 | Isolation | `listar_tareas_de(A)` while B has tasks | only A's rows — the filter is in the `WHERE`, not in Python |
| TC-DB-08 | TP-15 | Concurrency | N threads each open their own connection and write | every write lands; no corruption; no `database is locked` inside the configured limit |

*TC-DB-08 is written in Phase 3 against the DAO, but the property that matters in production —
one worker with threads, RNF-16 — is re-verified against the deployment in Phase 11.*

### 3.7 Security unit — `tests/test_seguridad.py` (Phase 4)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-SEG-01 | TP-04 | Irreversibility | `hashear_password("1234")` | differs from `"1234"` |
| TC-SEG-02 | TP-04 | Salt | hash the same password twice | the two hashes differ |
| TC-SEG-03 | TP-04 | Equivalence | `verificar_password` with the right and the wrong password | `True`, then `False` |

### 3.8 Welcome page — `tests/test_bienvenida.py` (Phase 1.1, extended)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-HTML-01 | TP-21 | Equivalence | `GET /tareas` with no headers | 200 and `Content-Type: text/html; charset=utf-8` |
| TC-HTML-02 | TP-21 | Negative scan | same, with a database that has users and tasks | body contains no username, no task title and no task id |
| TC-HTML-03 | TP-01 | Decision | `POST /tareas` | 405 |

### 3.9 Encoding — `tests/test_encoding.py` (Phase 5–8)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-ENC-01 | TP-23 | Use case | register and log in with `contraseña: "contraseña"` (real `ñ`) | 201 then 200; the byte sequence that comes back is UTF-8, not `\u00f1` and not `cp1252` |

### 3.10 Console client E2E — `tests/test_cliente.py` (Phase 8)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-E2E-01 | TP-17 | Use case | register → log in → create → list → update → delete, through the client's transport functions | every operation OK; the values printed match the API's |
| TC-E2E-02 | TP-17 | Fault injection | the API is unreachable (closed port) | one line naming the network failure; non-zero exit; **no traceback** |
| TC-E2E-03 | TP-17 | Negative | the API answers 400 and 401 | one line with the status code and the API's `error` value; non-zero exit |
| TC-E2E-04 | TP-17 | Contract | compare the field names and status codes the client uses with `docs/api.md` | exact match (`token`, not `access_token`) |
| TC-E2E-05 | TP-17 | Boundary | inspect the timeout on every request the client sends | every request carries an explicit positive timeout |
| TC-E2E-06 | TP-25 | State | the client holds a token the API rejects (expired) | the 401 clears the token in memory and the message asks to log in again |
| TC-E2E-07 | TP-17 | Boundary | a session with one failed operation, then a clean session | exit code 1, then exit code 0 |
| TC-E2E-08 | TP-17 | Negative | unparseable input: id `abc`, `completada` = `tal vez`, option `99` | one line, no traceback, and the session keeps running |
| TC-E2E-09 | TP-23 | State | a `ñ` password (`contraseña`) through register and log in, and the client's output stream | the password round-trips and the stream is forced to UTF-8 |

### 3.11 Documented limitation — `tests/test_cliente.py` (Phase 8)

| ID | TP | Technique | Given / When | Expected |
|---|---|---|---|---|
| TC-CLI-01 | TP-25 | State | log out in the client, then reuse the same token against the API | **still valid** — no server-side revocation exists (D-17). The case exists to pin the limitation, and the README must state it |

---

## 4. Coverage check

Every test point has at least one case, and every case names a test point:

| Module | Cases | Test points covered |
|---|---|---|
| Registration | TC-REG-01 … 16 | TP-01, TP-02, TP-03, TP-05, TP-18, TP-19, TP-24 |
| Login | TC-LOG-01 … 09 | TP-01, TP-02, TP-06, TP-07, TP-18, TP-24 |
| Token and auth | TC-TOK-01 … 06, TC-AUT-01 … 06 | TP-01, TP-05, TP-08, TP-09, TP-10, TP-21 |
| Task CRUD | TC-TAR-01 … 19 | TP-01, TP-11, TP-12, TP-13 |
| Errors | TC-ERR-01 … 05 | TP-14, TP-16, TP-22 |
| Persistence | TC-DB-01 … 08 | TP-03, TP-04, TP-11, TP-14, TP-15, TP-19, TP-20 |
| Security unit | TC-SEG-01 … 03 | TP-04 |
| Welcome page | TC-HTML-01 … 03 | TP-01, TP-21 |
| Encoding | TC-ENC-01, TC-E2E-09 | TP-23 |
| Client E2E | TC-E2E-01 … 09 | TP-17, TP-23, TP-25 |
| Client limitation | TC-CLI-01 | TP-25 |

**86 cases over 25 test points.** Reverse check: the test points with the most cases are TP-02
(eleven), TP-12 (eight) and TP-17 (seven). Four test points carry a single case each — TP-06,
TP-09, TP-15 and TP-16.

Case count is not a risk ranking, and this distribution is where that shows: TP-02 is `High` while
TP-11 is `Critical`, yet the registration rules produce nearly twice as many cases. What drives the
count is the number of *distinct rules* a test point has to pin — every presence, type, emptiness
and length rule of RF-01 generates its own equivalence class or boundary — not the band. The band
drives execution order and priority (`docs/matriz-de-riesgo.md` §4), not the number of cases.

---

## 5. Automation decisions

| Case group | Automated? | Why |
|---|---|---|
| Everything in §3 except TC-DB-08's deployment half | Yes, pytest | Cheap once the fixture exists, and re-runnable at no cost |
| TC-DB-08 (DAO half) | Yes | A thread pool plus one connection per thread is a few lines |
| TC-DB-08 (deployment half) | No — Phase 11 | Needs the real single-worker configuration; recorded as evidence, not asserted |
| TC-E2E-01 … 09, TC-CLI-01 | Yes | The client separates transport from presentation exactly so this is testable from pytest |
| Evidence E-04, E-05, E-07 | Manual, with command captions | A browser page, a console session and a table inspection are the deliverable itself; the caption is what makes them reproducible |

---

## 6. Deliberately not covered

| Not covered | Why it is accepted |
|---|---|
| Response times, throughput | No performance requirement exists; TP-15 covers concurrency correctness only |
| Multiple browser engines | The page has no scripting; one capture (E-04) satisfies RF-09 |
| Fuzzing, broader penetration testing | TP-14 is the documented injection case plus a review of every statement |
| TLS configuration | Terminated by the hosting platform |
| Password strength | D-14 fixes the policy at "non-empty"; there is nothing to test (TP-24 asserts the boundary that matters) |
| Token revocation | Declared non-goal (D-17); TC-CLI-01 pins the limitation instead of pretending it is absent |

The full list of accepted residual risk lives in `docs/matriz-de-riesgo.md` §5; this table only
names the part that concerns the case catalog.

---

## 7. Revisions

Appended, never edited in place — same rule as `docs/decisiones.md` and `docs/requisitos.md`.

### 2026-10-20 — created (Phase 1.6)

- **Sources:** `docs/requisitos.md` (RF/RNF), `docs/matriz-de-riesgo.md` (§2–§4 bands and
  ordering), `docs/api.md` (every status code, message and pinned value), and the TP tables of
  the working plan, which are reproduced here because the plan is not versioned.
- **No requirement was added.** Every case cites the RF or the pinned value that demands it.
- **Two cases exist only to pin a decision that could otherwise be argued:** TC-TAR-12 (title
  validated after stripping but stored as typed) and TC-LOG-07 (`contraseña` is never stripped).
  Both come from D-21 and `docs/api.md` §7, and both would be silently "fixed" by a future
  contributor who thought the behaviour was a bug.
