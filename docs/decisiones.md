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
