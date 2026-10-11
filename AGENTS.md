# AGENTS.md — PFO 2: Task Manager API

Project-wide engineering rules. These apply to **every** line of code, every test,
and every decision made in this repository, by a human or by an AI agent.

## How AI agents operate here

This file is a contract, not a suggestion. Any AI agent working in this
repository **must**:

1. Read this file completely before writing code.
2. Propose a short plan (approach + files) before implementing; the human leads
   and approves.
3. Add nothing that a requirement or a test does not demand (see YAGNI and the
   YAGNI ⇄ SOLID gate below).
4. Write or update tests for any behavior change, and run the suite before
   declaring work done.
5. Report results honestly, including failures. Never claim "done" without
   evidence.
6. Never commit, push, or open a PR unless explicitly asked.
7. If a request conflicts with these rules, STOP and ask. Silent deviations are
   forbidden (see Decision log).

## Project scope

Flask REST API + SQLite persistence + a console client, with password hashing
and JWT authentication, a pytest suite, and a README. The authoritative scope is
the PFO 2 activity brief plus the approved scope decisions:

- Real task CRUD (not a placeholder).
- Auth via JWT.
- `/tareas` is protected and isolated per owner (no cross-user access).
- Console client is a deliverable.
- API deployed on a Python runtime; GitHub Pages only for docs/presentation.

Nothing outside that scope is built. If a request implies new scope, it must be
explicitly approved first.

## Engineering principles

### 1. YAGNI — "You Aren't Gonna Need It"

- Build **only** what a requirement needs. No more.
- Do **not** add, unless explicitly required: user roles/permissions beyond
  owner isolation, pagination, search/filtering, refresh tokens, rate limiting,
  Docker, an ORM, caching, background jobs, async, admin panels, or "future"
  extension points.
- No speculative abstractions, config flags, or parameters "for later".
- No code without a requirement or a test that demands it.

### 2. KISS — "Keep It Simple"

- Choose the **simplest** solution that satisfies the requirement.
- One function = one job. Keep functions small and readable.
- Flat beats nested. Prefer early returns over deep `if/else` chains.
- Use plain **parameterized SQL** instead of an ORM at this size.
- Add a design pattern only when it removes real complexity — never to look
  "professional". If you add one, justify it in the commit/PR.
- Prefer the standard library and dependencies already present (Flask, its
  bundled `werkzeug`) over new packages.

### 3. SOLID — mapped to this project

- **SRP (Single Responsibility).** One reason to change per module/function:
  - `security.py` — only hashing and verifying passwords.
  - `repository.py` (DAO) — only database access, nothing else.
  - `routes.py` — only the HTTP layer: parse, call, respond.
  - `config.py` — only configuration.
  - A function never mixes HTTP parsing with SQL or with hashing.
- **OCP (Open/Closed).** Add new behavior by adding a new module/function, not
  by growing an existing god-function.
- **LSP (Liskov Substitution).** Any implementation of a defined interface must
  honor its full contract (same inputs, same guarantees, same error behavior).
- **ISP (Interface Segregation).** Keep interfaces small and focused; never
  force a consumer to depend on methods it does not use.
- **DIP (Dependency Inversion).** Business logic must not depend directly on
  HTTP or DB details; it depends on a small interface (e.g. `UserRepository`,
  `TaskRepository`). **See the gate below.**

### Resolving the YAGNI ⇄ SOLID tension

SOLID pushes toward abstraction; YAGNI pulls back. The rule that settles it:

> Introduce an abstraction **only** when a real seam is needed for testing, or
> when a real second consumer/implementation exists. Otherwise, keep it concrete
> and simple.

No full dependency-injection container. No interface with a single implementation
"just in case". When in doubt, pick the simpler option and **document the
decision** in the commit or PR. Never silently deviate from these rules.

## Clean Code (also mandatory)

- Names express intent. No abbreviations (`hashear_password`, not `hp`).
- Functions stay small and single-purpose.
- No repetition (DRY) — but do not over-DRY; premature extraction is an SRP
  and YAGNI violation too.
- Explicit error handling. Never a bare `except:` that swallows failures.
- Configuration (secret key, DB path) comes from the environment, never
  hardcoded, and secrets never get committed.

## Language conventions

Deliberate choice (see Decision log):

- **Documentation** (README, this file, design/spec docs): **English**.
- **Code** (identifiers, test names, comments/docstrings): **Spanish**, matching
  the domain (e.g. `/tareas`, `hashear_password`,
  `test_login_con_password_incorrecta_devuelve_401`).
- **Commit messages**: **Spanish**.
- Never mix languages inside a single artifact.

## Testing rules

- Runner: `pytest`. Layers: unit (hashing, DAO) → integration (endpoints via
  `test_client` + in-memory DB) → E2E (console client against the API).
- One behavior per test. The test name states scenario + expectation
  (e.g. `test_login_con_password_incorrecta_devuelve_401`).
- Every endpoint covers: happy path + boundary values + negative cases +
  security (per the 17 test points in the project's testing table).
- Tests are code: they obey every rule above.

## Definition of Done (per work unit)

- [ ] Requirement implemented — nothing more (YAGNI), nothing less.
- [ ] Tests written and green.
- [ ] No dead code, no unused parameters, no commented-out blocks.
- [ ] Responsibilities separated (SRP layering respected).
- [ ] Committed with a Conventional Commit message.

## Decision log

When a rule and a requirement conflict, or when you deliberately deviate,
document the decision and the reason in the commit/PR. Silent deviations are
not allowed.
