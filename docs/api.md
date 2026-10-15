# API contract — PFO 2

**Purpose.** The agreement between this API and everything that consumes it: the console
client (Phase 8), the test suite (Phases 2.4 onward), and the grader's `curl`. Written
**before** the code that implements it, on purpose — see "Why this document exists first".

**Status.** Phase 1.2. Six of the eight endpoints are **specified, not yet implemented**.
`GET /tareas` is the only one already running (Phase 1.1).

**Satisfies:** every functional requirement in `docs/requisitos.md` (RF-01 … RF-17), the
status-code requirement RNF-04, and decisions D-04 revisada, D-06, D-07, D-09, D-10, D-11,
D-12, D-14, D-19, D-21, D-22, D-23.

**Traceability:** the last section maps endpoint → RF → TP.

---

## 1. Authentication at a glance

This is the single most important table here, because it is the one place where the project
deliberately breaks its own rule.

| Route | Token required |
|---|---|
| `GET /tareas` | **No.** It is public and carries no user data |
| Every `/api/tareas` route | **Yes.** Every method, without exception |
| `POST /registro` | No — it is how you get an account |
| `POST /login` | No — it is how you get a token |

**Why the HTML page is the exception** (D-04 revisada). The original rule gated both
representations of `/tareas` with one rule. The Phase 0.3 testability review found that rule is
unsatisfiable: **a browser navigation cannot send an `Authorization` header**, so a token-gated
HTML page is reachable only by `curl`. The requirement contradicted its own intent — a page for
a person to open — and its own evidence plan, which asked for a browser capture (E-04). Only
the HTML half changed. The isolation rule was never in question: a welcome page with no data on
it protects nothing by being gated.

**How a token is sent.** One header, one scheme, no alternatives:

```
Authorization: Bearer <token>
```

**Anything else is a 401** — missing header, missing `Bearer` prefix, empty token, malformed
token, tampered signature, expired token, or a token signed with another key. Four causes, one
outcome, one identical body. See §5.

---

## 2. Quick path

The whole contract in six requests. This sequence is also evidence **E-03**.

```bash
# 1. Register. 201, and the response never contains the password or its hash.
curl -s -X POST http://localhost:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"usuario": "juan", "contraseña": "1234"}'
# -> {"usuario": "juan"}

# 2. Log in. 200, and the token lives in the field named exactly "token".
curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "juan", "contraseña": "1234"}'
# -> {"token": "eyJhbGciOiJIUzI1NiIs..."}

# 3. Create a task. 201, with the full task representation.
curl -s -X POST http://localhost:5000/api/tareas \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"titulo": "Estudiar SQLite"}'
# -> {"id": 1, "titulo": "Estudiar SQLite", "completada": false}

# 4. List your own tasks only.
curl -s http://localhost:5000/api/tareas -H "Authorization: Bearer $TOKEN"
# -> [{"id": 1, "titulo": "Estudiar SQLite", "completada": false}]

# 5. Update it.
curl -s -X PUT http://localhost:5000/api/tareas/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"titulo": "Estudiar SQLite", "completada": true}'
# -> {"id": 1, "titulo": "Estudiar SQLite", "completada": true}

# 6. Delete it. 204 — no body at all.
curl -s -i -X DELETE http://localhost:5000/api/tareas/1 -H "Authorization: Bearer $TOKEN"
# -> HTTP/1.1 204 NO CONTENT

# The welcome page needs no token at all.
curl -s -i http://localhost:5000/tareas
# -> 200, Content-Type: text/html; charset=utf-8
```

---

## 3. The one error shape

Every error response in this API — every status code, every endpoint — uses this shape and
nothing else:

```json
{"error": "<mensaje>"}
```

with `Content-Type: application/json`.

**Why one shape (RF-14).** A client that knows how to read one error knows how to read all of
them. The alternative — a status code whose body is sometimes a string, sometimes a list,
sometimes an HTML page — forces the client to branch on shape before it can branch on meaning.

**Never in an error body:** a stack trace, an internal file path, the `SECRET_KEY`, a password
hash, or the plaintext password (RNF-06, RNF-01).

**Consequences of this rule that are easy to forget.** `404` from an unknown URL, `405` from a
wrong method, and `500` from an unhandled exception must **all** come back as JSON. Flask's
default is an HTML error page, so each of those needs an explicit error handler. Getting this
wrong is invisible in the happy path and breaks the client only when something goes wrong —
which is exactly when the client most needs to read the error.

---

## 4. Endpoints

### 4.1 `POST /registro`

**Auth:** none.

**Request body**

```json
{"usuario": "juan", "contraseña": "1234"}
```

Both fields are required and both must be JSON strings.

| Status | Body | When |
|---|---|---|
| `201` | `{"usuario": "juan"}` | User created |
| `400` | `{"error": "..."}` | A field is missing, is not a string, or is empty; the JSON is malformed; or `Content-Type` is not `application/json` |
| `405` | `{"error": "..."}` | Method other than `POST` |
| `409` | `{"error": "..."}` | `usuario` already exists — **case-insensitively** |

**Behaviour rules**

- `usuario` is stripped of surrounding whitespace before validation, so `"  juan  "` and
  `"juan"` are the same account (D-21).
- `contraseña` is **never** stripped. Trimming a typed password silently rewrites the user's
  secret and produces login failures nobody can explain (D-21).
- **Both fields must be non-empty.** For `usuario` that is evaluated *after* stripping, so
  `"   "` is rejected; `contraseña` is used exactly as typed. Note that RF-01 read literally
  would accept `""`, because `""` is a string — the non-empty rule comes from D-14 and D-21,
  not from RF-01's own wording. See §7.
- Case-insensitive uniqueness comes from `UNIQUE COLLATE NOCASE`, so registering `juan` when
  `Juan` exists is a `409`, not a second account (D-11).
- The password policy is **non-empty only**. No minimum length (D-14) — the brief's own example
  password is `1234`, and a "best practice" minimum would reject the grader's own test case
  while claiming to follow the brief.
- **The response never contains the password or its hash** (RF-04). Not in the body, not in a
  header, not in an error.
- `409` is not `400`. A client can react differently to "your data is malformed" than to "that
  name is taken", and collapsing both into `400` destroys that.

### 4.2 `POST /login`

**Auth:** none.

**Request body** — same fields as registration.

```json
{"usuario": "juan", "contraseña": "1234"}
```

| Status | Body | When |
|---|---|---|
| `200` | `{"token": "eyJhbGciOi..."}` | Credentials match |
| `400` | `{"error": "..."}` | A field is missing or not a string; malformed JSON; wrong `Content-Type` |
| `401` | `{"error": "..."}` | The user does not exist, **or** the password is wrong |
| `405` | `{"error": "..."}` | Method other than `POST` |

**The field is named `token`.** Not `access_token`, not `jwt`, not `data.token`. The console
client reads `token`, so a rename here breaks the E2E test at the far end of the project.

**The `401` body is byte-identical for both causes** (RF-06). This is a contract guarantee, not
a nicety: telling a caller "that user does not exist" hands an attacker a user-enumeration
oracle. One error path, one message.

**Token contents** (RF-07, D-20)

| Property | Value |
|---|---|
| Algorithm | `HS256`, signed with `SECRET_KEY` from the environment |
| `sub` | The user id **as a string** — the JWT spec requires it, so the integer is converted |
| `iat` | Issued-at |
| `exp` | Issued-at + 8 hours |
| Carries the password or hash? | **Never.** A JWT is signed, not encrypted — anyone can read the payload by decoding base64 |

### 4.3 `GET /tareas` — the welcome page

**Auth:** **none.** Public and data-free (D-04 revisada).

| Status | Body | When |
|---|---|---|
| `200` | HTML document | Always, once the app is running |
| `405` | `{"error": "..."}` | Any method other than `GET` |

**Contract, precisely:** `Content-Type: text/html; charset=utf-8`, and the body carries **no
user data** — no tasks, no usernames, no ids. That guarantee is what makes the route being
public acceptable: there is nothing on it to protect.

**Not part of the contract:** the page's wording, layout and markup. The HTML is a deliverable
in its own right (RF-09), but no client parses it, so changing the copy is not a breaking
change. This is also why the console client never calls this route — a console cannot consume
HTML, which is the whole reason the JSON CRUD lives at a separate path (D-06).

### 4.4 `POST /api/tareas`

**Auth:** Bearer token.

**Request body**

```json
{"titulo": "Estudiar SQLite", "completada": false}
```

`titulo` is required. `completada` is optional and defaults to `false`.

| Status | Body | When |
|---|---|---|
| `201` | `{"id": 1, "titulo": "...", "completada": false}` | Task created, owned by the token's user |
| `400` | `{"error": "..."}` | `titulo` missing, not a string, empty after stripping, or longer than 200 characters; `completada` not a boolean; malformed JSON; wrong `Content-Type` |
| `401` | `{"error": "..."}` | Missing, malformed, tampered or expired token |
| `405` | `{"error": "..."}` | Wrong method |

- The `200`-character title limit is D-19: it bounds an input the client controls, so one
  request cannot store an unbounded string.
- The owner is taken **from the token**, never from the body. A client that sends `usuario_id`
  is ignored — that field is not part of the contract, and honouring it would be an IDOR.

### 4.5 `GET /api/tareas`

**Auth:** Bearer token.

| Status | Body | When |
|---|---|---|
| `200` | `[ {"id": 1, "titulo": "...", "completada": false} ]` | Always — an empty list when the user has no tasks, never `404` |
| `401` | `{"error": "..."}` | Invalid token |
| `405` | `{"error": "..."}` | Wrong method |

**Returns only the authenticated user's tasks** (RF-11). The filter is applied **in the SQL
query** (`WHERE usuario_id = ?`), not by filtering in Python afterwards. Filtering afterwards
means that forgetting the filter once returns another user's data — and nothing in the happy
path would reveal it.

### 4.6 `GET /api/tareas/<id>`

**Auth:** Bearer token. `<id>` is an integer.

| Status | Body | When |
|---|---|---|
| `200` | `{"id": 1, "titulo": "...", "completada": false}` | The task exists **and** belongs to the token's user |
| `401` | `{"error": "..."}` | Invalid token |
| `404` | `{"error": "..."}` | The task does not exist, **or** it belongs to another user |
| `405` | `{"error": "..."}` | Wrong method |

**`404` for both cases is deliberate** (D-07, D-09). Answering `403` for someone else's task
confirms that the task exists. `404` reveals nothing, and it is consistent with `/login` not
revealing whether a username exists. Same message, same status, indistinguishable.

A non-integer segment — `/api/tareas/abc` — is a `404` as well: it matches no route.

### 4.7 `PUT /api/tareas/<id>`

**Auth:** Bearer token.

**Request body** — the complete resource, as `POST`:

```json
{"titulo": "Estudiar SQLite a fondo", "completada": true}
```

| Status | Body | When |
|---|---|---|
| `200` | `{"id": 1, "titulo": "...", "completada": true}` | Updated |
| `400` | `{"error": "..."}` | Same validation as `POST` |
| `401` | `{"error": "..."}` | Invalid token |
| `404` | `{"error": "..."}` | Not found, or not yours |
| `405` | `{"error": "..."}` | Wrong method |

**`PUT`, not `PATCH`** (D-17, no-goals). A full-resource replacement is idempotent and simpler
to test: no partial-field semantics to define, no "what does omitting a field mean" ambiguity.
`PATCH` semantics are an explicit non-goal.

**The `WHERE` clause filters by owner** exactly as in `DELETE` — an update targeting another
user's task is a `404`, not a silent no-op and not a success.

### 4.8 `DELETE /api/tareas/<id>`

**Auth:** Bearer token.

| Status | Body | When |
|---|---|---|
| `204` | **(empty — no body at all)** | Deleted |
| `401` | `{"error": "..."}` | Invalid token |
| `404` | `{"error": "..."}` | Not found, or not yours |
| `405` | `{"error": "..."}` | Wrong method |

**`204` means "done, nothing to return"** (D-23). Returning `{"ok": true}` would contradict the
status code and give the client a body to parse for no reason. The response has no
`Content-Type` because it has no content.

---

## 5. Status code catalogue

| Code | Meaning in this API |
|---|---|
| `200` | Read or update succeeded, and the resource is in the body |
| `201` | Created; the new resource is in the body |
| `204` | Deleted; no body |
| `400` | The request is malformed or invalid — never "the server broke" |
| `401` | Not authenticated: bad credentials at `/login`, or a bad token everywhere else |
| `404` | Not found — **or not yours**, deliberately indistinguishable |
| `405` | The route exists, the method does not |
| `409` | Conflict with current state: the `usuario` is taken |
| `500` | Unhandled server error; JSON body, no traceback |

### What the `401` bodies look like

| Cause | Example message |
|---|---|
| `/login`, user does not exist | `{"error": "Usuario o contraseña incorrectos."}` |
| `/login`, wrong password | `{"error": "Usuario o contraseña incorrectos."}` — **byte-identical** |
| Protected route, missing token | `{"error": "Token ausente o inválido."}` |
| Protected route, malformed/tampered/expired token | `{"error": "Token ausente o inválido."}` — **byte-identical** |

The first pair is required by RF-06. The second pair is the same idea applied to tokens, and it
is one of the values this contract pins rather than derives — see §7.

---

## 6. Field reference

| Field | Type | Where | Rules |
|---|---|---|---|
| `usuario` | string | `/registro`, `/login` request; `/registro` response | Required, non-empty after stripping, unique case-insensitively |
| `contraseña` | string | `/registro`, `/login` request | Required, non-empty, **never** stripped, no minimum length |
| `token` | string | `/login` response | JWT, `HS256`, 8-hour expiry |
| `error` | string | Every error response | Always present, never any other key |
| `id` | integer | Task responses; `<id>` in paths | Server-assigned, never sent by the client |
| `titulo` | string | Task request and response | Required, non-empty after stripping, at most 200 characters |
| `completada` | boolean | Task request and response | Optional on write, defaults to `false` |

**The task representation is exactly `{"id", "titulo", "completada"}`** (RF-10). The owner's id
is **never** exposed — a client cannot see, guess or tamper with the ownership column, because
it never leaves the server.

**A note on `completada`:** SQLite stores it as an `INTEGER` `0`/`1`. The JSON contract is
`true`/`false`. The conversion is the repository layer's job, and it is the kind of detail that
leaks into the API if nobody writes it down.

---

## 7. Values this contract pins (not fixed by a requirement)

The requirements fix the shape, the status codes and the rules. They deliberately do not fix
the wording of messages or a few structural details. This contract has to pin them, or two
valid implementations would disagree. They are listed here so a reviewer can see exactly where
this document decided, and object to it.

| # | Pinned value | Why this choice |
|---|---|---|
| 1 | Error messages are written in **Spanish with accents** | The whole API surface is Spanish by decision D-10 (`usuario`, `contraseña`, `titulo`, `completada`). Mixed-language field names and messages would be worse. RNF-10/TP-23 already requires the Windows console to handle `ñ` end to end, so this adds no new encoding risk |
| 2 | All bad-token `401`s share one body | RF-08 only requires the `401`. Pinning one message keeps the test surface at one case instead of four. Unlike `/login`, there is no enumeration risk here: the caller already holds the token |
| 3 | `PUT` requires `titulo`, and an omitted `completada` becomes `false` | `PUT` replaces the whole resource, so an omitted field reverts to its default. This keeps `PUT` idempotent — sending the same body twice leaves the same resource — which RF-10's "create and update accept" wording implies but does not state |
| 4 | An empty string is invalid for both `usuario` and `contraseña` | Empty-after-strip follows from D-21, and non-empty is exactly D-14's password policy. **Gap worth noting:** RF-01 says "missing **or not a string**" → `400`, and `""` is a string, so RF-01 read literally would accept an empty username. The rule comes from D-14 and D-21, not from RF-01 |
| 5 | Trailing slashes are strict: `/api/tareas/` is a `404`, never a redirect | D-23 requires exactly one documented slash behaviour. A `308` redirect is the trap: many HTTP clients do not replay a `POST` body across a redirect, so the request silently loses its data |
| 6 | `<id>` is an integer; a non-integer segment is a `404` | The route simply does not match, so no special case is needed |
| 7 | The welcome page's HTML content is **not** contractual | No client parses it. Pinning the markup would turn a copy edit into a breaking change |
| 8 | `titulo` is validated **after stripping**, but stored **as typed** | Validating after stripping rejects a title made only of spaces, which carries no information. Storing as typed does not mutate user content — the same reasoning D-21 uses when it refuses to strip `contraseña`. **Gap worth noting:** RF-13 says only "non-empty", so `"   "` would pass RF-13 read literally. The intent comes from working-plan step 7.3, and `PLAN.md` is **not versioned** (D-24) — so this contract is where the rule first becomes durable |
| 9 | `Content-Type: application/json` is required **only on requests that carry a body** (`POST`, `PUT`) | A `GET` has nothing to parse, so demanding a header for an empty body would fail a correct client for no reason. RF-15 says "a JSON endpoint called without a JSON `Content-Type`" without drawing that line, and a test suite that over-applies the rule is wrong in the other direction |

---

## 8. Out of scope (D-17)

Named here so their absence reads as a decision rather than an oversight. **None of these are
implemented, and their absence is not a defect:**

CORS · refresh tokens · token revocation or a server-side logout blacklist · rate limiting ·
roles and permissions beyond owner isolation · pagination · search and filtering · an ORM ·
Docker · caching · background jobs · async · an admin panel · `PATCH` semantics.

**What "logout" means in this API:** nothing server-side. A JWT is stateless, so the client
forgets the token and it expires within 8 hours. There is no way to revoke it early. That is a
documented limitation (TP-25), not a hidden bug — and the README must say so.

---

## 9. Traceability

Forward link only. The full matrix `RF ↔ TP ↔ TC ↔ test file ↔ result` is built in Phase 1.6
and completed in Phase 9.2.

| Endpoint | Requirements | Test points |
|---|---|---|
| `POST /registro` | RF-01, RF-02, RF-03, RF-04, RF-15 | TP-02, TP-03, TP-04, TP-05, TP-18, TP-19, TP-24 |
| `POST /login` | RF-05, RF-06, RF-07 | TP-06, TP-07, TP-08, TP-09 |
| `GET /tareas` | RF-09 | TP-21 |
| `/api/tareas`, all methods | RF-10, RF-13, RF-16 | TP-12, TP-13, TP-17 |
| Owner isolation (`GET`-one, `PUT`, `DELETE`, list) | RF-11, RF-12 | TP-11 — the only Critical in the risk matrix |
| Any protected route, bad token | RF-08 | TP-08, TP-09, TP-10 |
| Error shape, status codes and the values the client prints | RF-14, RNF-04, RF-17 | TP-01, TP-16, TP-17, TP-22 |

**Not in this table, on purpose.** Requirements that do not describe an HTTP surface belong to
another layer, and listing them here would imply this document owns them: SQL parameter binding
(RNF-05 → TP-14), persistence and the single-worker deployment (RNF-02, RNF-16 → TP-15),
referential integrity (RNF-07 → TP-20), and the console's UTF-8 handling (RNF-10 → TP-23). They
are real requirements with real test points, and the full matrix in Phase 9.2 carries them.

---

## 10. Why this document exists before the code

The contract is the **agreement** between the API and the client. If it is not written first,
the client is built against an assumption: it reads `usuario`, the API returns `username`, and
the mismatch is discovered at the far end of the project during the E2E test — where the
failure looks like a client bug, a server bug, or a network problem, and nothing says which.

Writing it first has three concrete effects:

1. **The client can be built in parallel** and its code is provably correct before the API it
   calls exists.
2. **The tests have an oracle.** Every test in Phases 5 to 7 asserts against this document
   rather than against whatever the code happens to do. A test derived from the implementation
   only ever proves the implementation agrees with itself.
3. **Every `400`/`401`/`404` decision gets made once, deliberately,** instead of per endpoint,
   in the middle of implementation, under time pressure — which is how one endpoint ends up
   returning `403` where another returns `404` for the same situation.

This document is also the reason `docs/api.md` is versioned: `PLAN.md` is not, and the
requirement is that the contract lives **inside the repository**, where the grader and the
client can both rely on it.
