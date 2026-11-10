# Decision log — PFO 2

**Purpose.** Every scope and design decision made in this project, with the reason and the
alternative that was rejected. `AGENTS.md` forbids silent deviations: a decision that is not
written here does not exist, and a reviewer cannot distinguish it from an accident.

Each decision has a stable ID, cited from `docs/requisitos.md`, the API contract, the test
suite and commit messages.

**Status: every entry below is closed.** To reopen one, add a new dated entry at the bottom —
never edit an entry in place. That preserves the record of why the original choice was made.

**References:** `R-xx` = defect found in the assignment brief (Part A of the working plan) ·
`RF-xx` / `RNF-xx` = requirement (see `docs/requisitos.md`) · `TP-xx` = test point.

---

## 1. Scope decisions

| ID | Decision | Why | Alternative rejected | Closes |
|---|---|---|---|---|
| D-01 | Tasks are a real CRUD, not a welcome placeholder. | The brief's only task endpoint returns static HTML. Five real endpoints make the exercise a portfolio piece and give the console client something to consume. | A single placeholder endpoint — would leave the client and every E2E test meaningless. | R-01 |
| D-02 | GitHub Pages hosts documentation and the presentation page only. The API runs on a Python runtime. | Pages serves static files; Flask needs a running Python process. The brief asks for something technically impossible. | Serving the API from Pages — not possible. | R-02 |
| D-03 | Authentication uses JWT. | A signed, self-contained token is precisely testable: signature, expiry, claims. No server-side session store needed. | HTTP Basic, the brief's literal "basic auth" — would make `/login` redundant, since credentials travel on every request. An opaque token — less to verify and no standard claims. | R-03 |
| D-04 | `/tareas` and every CRUD route require a valid token, and data is isolated per owner. | "Allows access to the tasks" implies the route is gated. The brief never names the isolation rule, but without it any user can read anyone's tasks. | A public `/tareas` behind a login that grants nothing — a login protecting nothing. | R-05 |
| D-05 | The console client is a graded deliverable. | It appears in the brief's objectives but not in its deliverables list. It is also what makes the API meaningful and what enables E2E testing. | Skipping it — leaves the API with no real consumer. | R-08 |
| D-06 | `GET /tareas` returns a welcome HTML page; the JSON CRUD lives at `/api/tareas`. | Satisfies the brief literally and still gives the console client a JSON contract. Two representations become two routes instead of a branch inside one handler. | All-JSON at `/tareas` — ignores an explicit brief requirement. Content negotiation via `Accept` — puts conditional logic in the handler and doubles the test surface. | R-01 |
| D-07 | Requesting another user's task returns 404, not 403. | 403 confirms the resource exists; 404 reveals nothing. Consistent with not revealing whether a user exists at login. | 403 — more conventional and self-documenting, but it leaks existence. | R-05 |
| D-08 | The API is deployed on PythonAnywhere. | Its free tier has a persistent filesystem, so the SQLite file survives deploys and restarts. Other free hosts recreate the container and silently erase the database, which would make the brief's "persistence" fiction. | Render or Railway — simpler deploys, but ephemeral storage; acceptable only if declared as a limitation. | R-02 |

---

## 2. Interface and behaviour decisions

| ID | Decision | Why | Alternative rejected | Closes |
|---|---|---|---|---|
| D-09 | Authorization outcomes: missing, malformed, tampered or expired token → 401. Another owner's resource → 404. | One consistent rule, verifiable with a single table of cases. | Mixed 401/403 — forces the client to branch and leaks existence. | R-04, R-05 |
| D-10 | The JSON fields are exactly `usuario` and `contraseña`, with the ñ. | The brief specifies them, and a grader may well test with those exact names. | `username`/`password` — friendlier to tooling, but breaks the brief's own examples. | R-06, R-12 |
| D-11 | `usuarios.usuario` is `UNIQUE COLLATE NOCASE`. | Without an explicit rule SQLite treats `Juan` and `juan` as different users, so one person can register twice. | Case-sensitive uniqueness — simpler, but leaves the business rule undefined and ambiguous to the user. | R-06 |
| D-12 | A malformed or missing JSON body returns 400, via `request.get_json(silent=True)`. | Turns a library-level failure into a controlled, consistent response. | Letting the exception reach the framework — yields a 500 or an HTML error page. | R-07 |
| D-13 | The database lives at `instance/pfo2.db` and is never versioned. | Flask's conventional instance path, outside the package, and `*.db` is already ignored. | Committing the database — publishes user password hashes. | R-09 |
| D-14 | The password policy is "non-empty" only. No minimum length. | The brief's own example password is `1234`. A minimum-length rule would reject the grader's test case while claiming to follow best practice. | Minimum 8 characters — would break the brief's example. | R-11 |
| D-15 | Routes live at the root, with no `/api/v1` prefix: `/registro`, `/login`, `/tareas`. | Matches the brief's paths exactly, and a grader will call those paths. | A versioned prefix — more professional for a real API, but it renames paths the brief already fixed. | R-12 |
| D-16 | Libraries: `werkzeug.security` for hashing, `PyJWT` for tokens, `pytest` and `pytest-cov` for tests. | `werkzeug` already ships with Flask, so hashing adds no dependency. `PyJWT` is minimal and explicit: the payload and the verification stay under our control. | `bcrypt`/`argon2` — stronger defaults, but a new dependency for no requirement gain. `flask-jwt-extended` — more convenience, more hidden behaviour, harder to test precisely. | R-11 |
| D-17 | Explicit non-goals: CORS, refresh tokens, token revocation, rate limiting, roles beyond owner isolation, pagination, search, an ORM, Docker, caching, background jobs, `PATCH` semantics. | Declaring them shows the scope was chosen on purpose. Each would add surface without a requirement demanding it. | "We'll add it if there is time" — that is how scope creep enters a project. | — |

---

## 3. Values fixed in this phase (open in `docs/requisitos.md` before this phase)

| ID | Decision | Why | Alternative rejected | Closes |
|---|---|---|---|---|
| D-18 | `servidor.py` is the runnable entry point; the logic lives in separate modules. | The brief names `servidor.py`; `AGENTS.md` requires separated responsibilities. An entry point that composes modules satisfies both. | One monolithic file — conflicts with the `AGENTS.md` SRP rule. Dropping `servidor.py` — conflicts with the brief's deliverable. | A-04 |
| D-19 | A task title is at most 200 characters. | Bounds an input the client controls, so one request cannot store an unbounded string. | No limit — unbounded storage from untrusted input. A short limit such as 50 — would reject legitimate descriptive titles. | A-01 |
| D-20 | Tokens expire 8 hours after issue. | Long enough for a study or demo session, short enough that a leaked token is not permanent. | No expiry — a stolen token works forever. 15 minutes — makes the console client unusable without refresh tokens, which are out of scope. | A-05 |
| D-21 | `usuario` is stripped of surrounding whitespace before validation; `contraseña` is never stripped. | Trimming a name avoids accidental duplicate accounts. Silently altering a typed password changes the credential and produces unexplainable login failures. | Stripping both — silently rewrites the user's secret. Stripping neither — `" juan"` and `"juan"` become two accounts. | A-03 |
| D-22 | `completada` stays as a task field (boolean, default false). | A task CRUD whose only field is a title is a notes list. One boolean gives `PUT` something meaningful to change and makes the portfolio piece credible. | Dropping it — strictly YAGNI, and would leave `PUT` with no purpose beyond renaming. **This is an addition beyond the brief and must be declared in the README.** | A-06 |
| D-23 | `DELETE` returns 204 with an empty body, and routes are strict about the trailing slash. | 204 means "done, nothing to return"; a body would contradict the code. One documented slash behaviour prevents a client calling `/tareas/` and getting a redirect it cannot follow. | `DELETE` returning `{"ok": true}` — redundant with the status code. Resolving both `/tareas` and `/tareas/` — two contracts for one route. | A-07, A-08 |

---

## 4. Process and repository conventions

| ID | Decision | Why | Alternative rejected | Closes |
|---|---|---|---|---|
| D-24 | The working plan (`PLAN.md`) is not versioned. It is excluded by a local rule in `.git/info/exclude`. | The repository is public and graded; the working plan is internal. A local exclude rule does not publish the file's existence, unlike a `.gitignore` entry. | Committing the plan — exposes internal working notes to the grader. Adding it to `.gitignore` — publishes a rule naming a file that is not in the repository. | — |
| D-25 | Published history is append-only: corrections go forward in a new commit. | The stray lines committed in `.gitignore` are cosmetic, not a leaked secret. Rewriting public history would risk the remote for no gain. | `amend`/`rebase` plus force push — rewrites published history and risks the remote's state. | — |
| D-26 | `.env.example` is versioned, and `.gitignore` needs a negation rule so it is not ignored. | It documents which variables exist without exposing their values. The current `.env.*` rule silently ignores it, so the file could never be committed. | Listing the variables in the README — they would drift from the code. | R-09 |

---

## 5. Brief defects closed by something other than a decision

| Defect | How it is closed |
|---|---|
| R-10 — the brief states no acceptance criteria, so nothing is objectively verifiable | Closed by producing acceptance criteria and test cases in Phase 1.6 (`docs/casos-de-prueba.md`), not by a decision |

---

## 6. Reopening a decision

Add a new dated entry in this format:

```markdown
### D-XX revisada — <YYYY-MM-DD>

- **Replaces:** D-XX
- **New decision:** ...
- **Why the original no longer holds:** ...
```

Never edit the original entry. The value of this document is the record of *why*, and that
record is only trustworthy if it is immutable.

---

## 7. Revisions

### D-04 revisada — 2026-10-12

- **Replaces:** D-04
- **New decision:** Every CRUD route under `/api/tareas` still requires a valid token, and data
  is still isolated per owner. `GET /tareas`, the welcome page, is **public**: it carries no
  user data, so there is nothing on it to protect.
- **Why the original no longer holds:** The original gated *both* representations of `/tareas`
  with a single rule. The Phase 0.3 testability review (finding F-01) showed that rule is
  unsatisfiable for the HTML representation: a browser navigation cannot send an
  `Authorization` header, so a token-gated HTML page is reachable only by `curl`. The
  requirement contradicted its own intent — a page for a person to open — and its own evidence
  plan, which asked for a browser capture (E-04). Only the sub-clause about the HTML page
  changed. The isolation rule was never in question: a *welcome* page with no data on it
  protects nothing by being gated.
- **Alternatives rejected:** A cookie set at login alongside the header — works in a browser,
  but adds `HttpOnly`/`Secure`/`SameSite` surface and session tests the brief never asks for,
  against the non-goals in D-17. Keeping the rule and changing the evidence to a `curl`
  capture — cheapest in code, but ships a page no person can open, which is visible in a graded
  deliverable.
- **Closes:** F-01. Affects RF-09 (rewritten), TP-21 (its HTML half inverts: 200 **without** a
  token, and the body must carry no task data).

---

## 8. Decisions added after Phase 0.2

The tables in §1–§4 were frozen at the end of Phase 0.2. Later phases append here instead of
editing them, for the reason §6 gives: the record of *why* is only trustworthy if it is
immutable.

### D-27 — 2026-10-15

- **Decision:** The `CREATE TABLE` statements frozen in `docs/modelo-de-datos.md` carry two
  `CHECK` constraints that `PLAN.md` step 1.3 does not give:
  `titulo TEXT NOT NULL CHECK (length(titulo) <= 200)` and
  `completada INTEGER NOT NULL DEFAULT 0 CHECK (completada IN (0, 1))`. Every other clause of
  the plan's DDL is unchanged, verified line by line.
- **Why:** The plan justifies having a schema at all by calling the database the last line of
  defence — in its own words, *aunque un bug en el codigo se salte la validacion, el UNIQUE y el
  NOT NULL siguen ahi*. Measured against the plan's own block, that guarantee held for two of
  the four rules this project has: it accepted a 5000-character `titulo` (D-19 allows at most
  200) and it accepted `completada = 7` (D-22 says boolean). The two constraints make the schema
  defend the same rules the requirements and the contract already state. The second one enforces
  exactly what `docs/api.md` declares — that the column holds `0` or `1` — so the schema stops
  being laxer than the contract it backs.
- **What was measured before deciding:** `length()` in SQLite counts characters, not bytes
  (`descripción` is 11 characters and 12 bytes), so a 200-character bound refuses 201 characters
  while still accepting legitimate accented titles. `0`, `1` and an omitted value are accepted;
  `7`, `-1` and `2` are refused. Case-insensitive uniqueness, the `NOCASE` lookup and every
  `NOT NULL` were re-measured afterwards and are unaffected. The JSON `true`/`false` conversion
  is also unaffected: a JSON `true` decodes to Python `True`, which SQLite stores as `1`.
- **Alternatives rejected:** Keeping the plan's DDL verbatim and enforcing both rules only in
  the HTTP layer — zero deviation, but it leaves a client-controlled string unbounded at the
  storage layer, which is the exact failure D-19 exists to prevent. Adding only the `titulo`
  bound — defensible, but it makes *which* rules the database defends a matter of taste instead
  of a consistent rule.
- **Consequence accepted:** a `CHECK` turns a hypothetical validation bug into a visible
  failure rather than silently stored data. In particular, a non-boolean `completada` that
  reached the database would raise `IntegrityError` instead of being stored as `2`. The contract
  already requires a `400` before that point, so this is a backstop, not a new failure path for a
  correct client.
- **Closes:** nothing new. D-19 and D-22 stand as written; this decision is about *where* they
  are enforced.
- **Affects:** `docs/modelo-de-datos.md` §2 (the DDL of record) and its §5 (the deviation
  record).

### D-28 — 2026-10-15

- **Decision:** The project targets **Python 3.13**. `requirements.txt` declares it, and
  the virtualenv created in Phase 2.1 is built with 3.13 — not with the development
  machine's default interpreter.
- **Why:** The API is deployed on PythonAnywhere (D-08, DEL-08). Its newest system image,
  `innit`, supports up to Python 3.13 and offers no 3.14 at all. The development machine
  defaults to Python 3.14.6, so leaving the version implicit would mean building and
  testing on an interpreter the deployment cannot run, and finding that out at deployment
  time. Naming the version is also what RNF-13 asks for: reproducibility means pinned
  dependencies *and* a documented Python version.
- **What was measured before deciding:** the supported-versions table on PythonAnywhere's
  help site, read on 2026-10-15, tops out at 3.13. Python 3.13.14 is installed on the
  development machine and registered with the `py` launcher alongside the 3.14 default.
  Against 3.13.14, in an empty virtualenv: the four pinned packages install
  (`Flask==3.1.3`, `PyJWT==2.13.0`, `pytest==9.1.1`, `pytest-cov==7.1.0`), werkzeug's
  default scrypt hashing produces and verifies a hash, and the four modules committed in
  Phase 1 parse unchanged. Nothing in the project required 3.14.
- **Alternatives rejected:** targeting 3.14 because that is what the development machine
  runs — it would make DEL-08 unsatisfiable on the chosen host. Targeting a much older
  version for maximum compatibility — compatibility with hosts this project does not use,
  paid for with a needlessly old language level for no requirement gain.
- **Affects:** `requirements.txt` (which declares the version), RNF-13 (its
  documented-version clause), and Phase 2.1, whose virtualenv must be created with 3.13.
  Also worth knowing when the deployment is set up.

### D-29 — 2026-11-10

- **Decision:** `POST /login` returns a byte-identical `401` for "user does not exist" and
  "wrong password" — same status, same body, same `Content-Type` — and the **remaining
  response-time difference is accepted as a documented residual risk**, not fixed. The measured
  gap is real and large, and it is recorded here rather than left silent.
- **Why:** TP-07 asks that the two failure causes be indistinguishable to the client, and the
  contract's letter (`docs/api.md` §5) pins exactly three things: status, body bytes and the
  `Content-Type`. All three are identical and are tested that way (TC-LOG-04). Closing the
  timing channel, however, is a different change with a different cost: it makes every failed
  login pay a full scrypt verification (~200 ms of CPU) even when no account exists — converting
  a free, cheap request into an expensive one for the server. This project has no rate limiting
  (it is explicitly out of scope per YAGNI), so the fix would add a denial-of-service lever that
  does not exist today. Trading a hard-to-exploit information leak for an easy-to-exploit
  resource exhaustion is not an improvement; it is a different problem.
- **What was measured before deciding:** the reference implementation short-circuits —
  `if guardado is None or not security.verificar_password(...)` — so an unknown username never
  reaches scrypt. Measured through the test client, interleaved samples: **wrong password
  median 335.7 ms vs unknown user median 1.1 ms, ratio ~296x**, with p95 434.7 ms vs 1.9 ms and
  no overlap between the two distributions. A single `check_password_hash` on werkzeug's default
  `scrypt:32768:8:1` costs ~196 ms, which is the whole gap. The measurement was repeated
  independently and reproduced. This is not a hypothetical channel: it is deterministic and
  measurable from a single machine.
- **What the contract does and does not cover:** `docs/api.md` §5 fixes *what* the client reads,
  and forbids distinguishing the causes in the body. It says nothing about timing, and the
  project has no requirement about side-channel resistance. So this is genuinely an accepted
  risk, not a contract breach — but calling it "compliant" without saying *which* observable
  channel remains open would be dishonest, and that is what this entry prevents.
- **Alternatives rejected:** (1) **Always verify against a decoy hash** — technically the correct
  fix, closes the channel completely, and it was the option favored on pure security grounds.
  Rejected because it imposes a fixed ~200 ms CPU cost per failed login with no rate limiting to
  bound the amplification, in a project whose brief defines no availability requirement and
  whose deployment is a shared free-tier host. (2) **Add rate limiting plus the decoy hash** —
  the complete answer, but rate limiting is explicitly out of scope (YAGNI section of
  `AGENTS.md`), so it would be scope expansion decided by the implementer rather than by a
  requirement. (3) **Sleep a fixed interval on the fast path** — makes the two paths equal in
  time without the CPU cost, but it is a timing patch that only works while the slow path stays
  slower than the sleep, and it silently breaks the moment hashing parameters change.
- **Consequence accepted:** an attacker who can time the endpoint can determine whether a given
  username exists, at roughly 200 ms per probe of added noise once network jitter is in play.
  No credential, no hash and no account content is exposed by this, and the login stays
  rate-unlimited by design. If this project ever gets an availability requirement or a public
  deployment under real traffic, the correct order is: rate limiting first, then a decoy hash —
  both together, not the decoy alone.
- **Affects:** the docstring of `routes.py::iniciar_sesion` and the module docstring of
  `tests/test_login.py`, which both state the limit so nobody later mistakes the passing suite
  for a closed channel. No test asserts anything about timing, deliberately: a timing assertion
  would be flaky, and its absence is the decision, not an oversight.
- **Closes:** nothing new. TP-07 is met as written; D-20 and D-21 are unaffected.

### D-30 — 2026-11-10

- **Decision:** The console client is two layers with one seam. `ApiDeTareas` owns the
  transport (URL, `Authorization`, `timeout`, error translation) and receives its HTTP session
  by parameter (`sesion=None` resolves to `requests.Session()`); `menu` owns the presentation and
  takes `leer`/`escribir` by parameter too. The token lives only in `ApiDeTareas.token`. Every
  call carries an explicit `timeout` (5 s). `POST /registro` and `POST /login` are sent with
  `autenticada=False`, so they never carry the `Authorization` header; a `401` on any *other*
  call clears the token in memory and the message asks the person to log in again, while a `401`
  from `/login` is reported as bad credentials and touches no session state.
- **Why:** RF-17 asks for one line and a non-zero exit on failure, and TP-17 asks that the
  client's field names and status codes match `docs/api.md`. Neither can be asserted by typing at
  a keyboard. The seam is what makes the client runnable from pytest against the real app through
  `test_client`: production and tests exercise the same `_enviar`, so a wrong field name or a
  missing `Bearer` fails the suite instead of the demo.
- **Why this is not a speculative abstraction** (the YAGNI ⇄ SOLID gate in `AGENTS.md`): there is
  a real second implementation — the test adapter over Flask's `test_client` — and it is the only
  way to satisfy TC-E2E-01…04 without opening a port. No interface with a single implementation is
  introduced: the client depends on the four method calls it actually uses
  (`get`/`post`/`put`/`delete`) and on nothing else.
- **Alternatives rejected:** (1) **Point `requests` at a live server** — the most faithful, and
  the reason this phase also runs one manual session against a real server; rejected *for the
  suite* because it needs a free port, a start wait and cleanup, which turns a fast test file into
  a flaky one. (2) **Test only the presentation against a fake transport** — proves the menu and
  nothing about the contract, which is exactly the bug TP-17 exists to catch (the client expects
  `usuario` while the API answers `username`). (3) **`urllib.request` to avoid the dependency** —
  one line less in `requirements.txt`, at the cost of `URLError` and `HTTPError` overlapping in the
  same `except`. Rejected: the plan fixes `requests`, and `Session` reuses the connection across the
  menu's calls.
- **Exit code:** 1 if any operation failed during the session, 0 otherwise. A failure does not
  close the program — the person corrects the input and continues — so the code summarizes the
  session instead of aborting it. Input that ends (Ctrl+Z, closed pipe) exits with the same code
  and without a traceback.
- **Consequence accepted:** a wrong password or a deleted task sets the session's exit code to 1
  even when the following operations succeed. Deliberate: RF-17 names the non-zero exit as the
  machine-readable signal, and per-operation success is already on screen.
- **What is *not* asserted:** the rendering of the real Windows console. `_configurar_utf8` forces
  UTF-8 on `stdout`/`stderr` and one test pins that call, but whether `ñ` *looks* right in
  `cmd.exe` depends on the terminal, so it is evidenced manually (E-05) rather than tested.
- **Affects:** `cliente.py`, `tests/test_cliente.py`, `requirements.txt`.
- **Closes:** RF-16, RF-17 and the client half of RNF-10. TC-CLI-01 keeps D-17's limitation
  visible: `cerrar_sesion` is local and the token stays valid on the server until it expires, which
  the README (Phase 9) has to state in words.

