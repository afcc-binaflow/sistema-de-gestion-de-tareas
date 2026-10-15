# Data model — PFO 2

The schema of record for the two tables behind the API described in `docs/api.md`.

`PLAN.md` is not versioned (D-24), so this document — not the working plan — is where the DDL
is frozen. Phase 3.1's `init_db()` executes the block in §2; if the two ever disagree, this
document is right and the code is wrong.

**This is a design artefact.** Phase 1 writes no Python (the Fase 1 definition of done), so
nothing here is executed by the application yet. What *is* executed is the verification
described in §5: the block in §2 was run against SQLite and every claim below is a measured
result, not an expectation.

---

## 1. Scope

Two tables, and no more.

| Table | Holds | Ownership |
|---|---|---|
| `usuarios` | one row per registered account | — |
| `tareas` | one row per task | every row belongs to exactly one `usuarios` row |

The eight endpoints of `docs/api.md` are the only consumers. A task is represented as
`{"id", "titulo", "completada"}` and never exposes its owner (RF-10), which is why
`usuario_id` exists in the table and appears in no response body.

---

## 2. The DDL (frozen)

<!-- The artefact. Phase 3.1 copies this block; the verification in §5 runs it as-is. -->

```sql
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tareas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo     TEXT NOT NULL CHECK (length(titulo) <= 200),
    completada INTEGER NOT NULL DEFAULT 0 CHECK (completada IN (0, 1)),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE
);
```

Two lines differ from `PLAN.md` step 1.3. Both differences are deliberate, both are recorded
as D-27, and §5 justifies them and proves nothing else moved.

---

## 3. Clause by clause

### `usuarios.id`

`INTEGER PRIMARY KEY` is already an alias for SQLite's internal rowid and already assigns a
value on insert. `AUTOINCREMENT` adds exactly one guarantee on top: **ids are never reused
after a delete**. Measured: after deleting the row with id 1, the next insert received id 51,
not 1.

That matters here because `ON DELETE CASCADE` deletes tasks. Without `AUTOINCREMENT`, a
recycled user id would make any stale reference held by a client point at a *different*
account than the one it was issued for. The cost is one extra table, `sqlite_sequence`, which
SQLite creates itself.

### `usuarios.usuario`

One line carrying three rules, each measured:

- **`NOT NULL`** — a row with `usuario = NULL` is refused.
- **`UNIQUE`** — a second row with the same value is refused with
  `IntegrityError: UNIQUE constraint failed: usuarios.usuario`.
- **`COLLATE NOCASE`** — uniqueness ignores case. `juan` and `JUAN` are both refused while
  `Juan` exists. This is D-11 and RF-03, whose own verification column asks the DAO for an
  `IntegrityError`.

The collation is declared **on the column**, so it applies to comparisons in every query, not
only to the unique index. Measured: `WHERE usuario = 'jUaN'` finds the row stored as `'Juan'`.
That is what lets `/login` be case-insensitive without `UPPER()` wrapped around the SQL.

There is no length bound on this column, on purpose — see §6.

### `usuarios.password_hash`

Stores the hash produced by `werkzeug.security`, never the password (RF-02, TP-04). `NOT NULL`
is measured. No `CHECK` constrains the hash's shape, on purpose — see §6.

### `tareas.id`

As above. This is the `<id>` in the API paths. The API contract pins it to an integer and a
non-integer segment to a `404` (`docs/api.md` §7, value 6).

### `tareas.titulo`

`NOT NULL` is measured. The `CHECK` enforces D-19 and RF-13 at the storage layer.

`length()` in SQLite counts **characters**, not bytes. Measured: the accented string
`descripción` reports `length()` = 11 while its UTF-8 encoding is 12 bytes. So this bound means
the same thing as RF-13's "at most 200 characters" and as Python's `len()`. Had `length()`
counted bytes, this constraint would have rejected legitimate accented titles — which is why
it was measured rather than assumed.

The bound is inclusive: 200 characters are accepted, 201 are refused.

### `tareas.completada`

D-22. SQLite has no boolean type, so the column is an `INTEGER` and the contract carries the
conversion: `docs/api.md` §6 states that SQLite stores `0`/`1` and the JSON contract is
`true`/`false`, with the conversion as the repository layer's job.

Measured: omitting the field yields `0`; `0` and `1` are accepted; `7`, `-1` and `2` are
refused. Note that `2` is refused as well — JSON `true` decodes to Python `True`, which SQLite
stores as `1`, so this changes nothing for a correct client.

### `tareas.usuario_id`

The ownership column, and the reason RNF-07 exists. `NOT NULL` is measured.

`REFERENCES usuarios(id) ON DELETE CASCADE` means two things: a task cannot point at a user
that does not exist, and deleting a user deletes that user's tasks. **Neither is enforced
unless `PRAGMA foreign_keys = ON` is set on the connection** — see §4.

Ownership is enforced in the queries, not in the schema: the schema says a task has an owner,
it cannot say *which* client may read it. Isolation per owner is RF-11/RF-12 and is the DAO's
`WHERE usuario_id = ?` plus the 404 rule.

---

## 4. The PRAGMA that makes `REFERENCES` real

`PRAGMA foreign_keys` is **per connection**. It is not a property of the schema and it is not
persisted in the database file.

Measured on one single database file, with two connections:

| Connection | `PRAGMA foreign_keys` | Inserting a task for a nonexistent user |
|---|---|---|
| A, after `PRAGMA foreign_keys = ON` | `1` | refused — `FOREIGN KEY constraint failed` |
| B, opened on the same file, no PRAGMA | `0` | **accepted** — an orphan row is stored |

The cascade behaves the same way: with the PRAGMA on, deleting the user left 0 tasks; with it
off, deleting the user left the task behind as an orphan, and the `CASCADE` did nothing.

So the `REFERENCES` clause is decorative unless every connection turns the PRAGMA on. That is
why `db.py` sets it inside `conectar()`, the single place where a connection is opened
(committed in `b52894f`): concentrating the opening makes forgetting it impossible instead of
improbable. It is deliberately **not** in `init_db()`.

This is RNF-07, and its verification column asks for exactly the two measurements above.

---

## 5. Deviations from `PLAN.md`, and the measurement behind them

`PLAN.md` step 1.3 gives an explicit DDL and the plan presents it as "el DDL exacto". Two
lines were changed. The deviation is deliberate, it is recorded as D-27, and it was approved
before this document was written.

The plan's own justification for having a schema at all is that the database is *the last line
of defence*: "aunque un bug en el codigo se salte la validacion, el `UNIQUE` y el `NOT NULL`
siguen ahi". The DDL as written honoured that for two rules out of four. Measured against the
plan's block verbatim, before any change:

| Rule the project has | Enforced by the plan's DDL? |
|---|---|
| `usuario` unique, case-insensitively (D-11, RF-03) | yes |
| no `NULL` in a required column | yes |
| title at most 200 characters (D-19, RF-13) | **no** — a 5000-character title was accepted |
| `completada` is a boolean (D-22) | **no** — `7`, `-1` and `2` were accepted |

**Deviation 1 — `CHECK (length(titulo) <= 200)`.**

D-19 exists to bound "an input the client controls, so one request cannot store an unbounded
string". With the bound living only in the HTTP layer, the failure D-19 was written to prevent
is exactly the failure that survives a validation bug. The change costs one clause and, when
measured, rejects 201 characters while still accepting 200 accented ones.

**Deviation 2 — `CHECK (completada IN (0, 1))`.**

This enforces precisely what `docs/api.md` §6 already documents — that the column holds `0` or
`1` — so the schema stops contradicting the contract by being laxer than it. `docs/api.md` also
requires a `400` when `completada` is not a boolean, so rejection happens in the HTTP layer
before the database is reached; this `CHECK` is a backstop, not the primary rule.

**What was verified after the change.** With both `CHECK`s in place, and re-measured: 200
characters accepted (ASCII and accented), 201 refused, 5000 refused, `completada` `0`/`1`/
default accepted and `7`/`-1`/`2` refused, and — unchanged — case-insensitive uniqueness still
refused `juan`, the `NOCASE` lookup still found `Juan` from `jUaN`, and `NULL` was still
refused. Nothing that the plan's DDL guaranteed was weakened.

**Minimality.** Comparing the plan's block against the block in §2 line by line, after
ignoring the indentation the plan's markdown adds, the only two differing lines are the two
`titulo` and `completada` definitions. No other clause was touched.

---

## 6. Deliberately not in the schema

Each of these is an omission with a reason, not an oversight.

- **No length bound on `usuario`.** No requirement bounds it: RF-01 asks only that it be
  non-empty after stripping (D-21). Adding a bound here would reject input that no rule
  rejects, and if a bound is ever wanted it belongs in the contract first.
- **No `CHECK` on the shape of `password_hash`.** A constraint on an algorithm prefix would
  break on a `werkzeug` upgrade without any requirement being violated.
- **No index on `tareas.usuario_id`.** Every read of this table is already scoped to one owner
  and the project holds a handful of rows. An index here would be speculative; it is worth
  adding on a measured need, not in advance.
- **No timestamps, no soft delete, no `descripcion`, no admin flag.** Not in the brief, and
  named as non-goals in D-17. "We might want it later" is how scope creep enters a project.
- **No `DEFAULT` on `titulo`.** A task without a title is not a task; the API answers `400`
  instead of silently inventing one.

---

## 7. How this DDL is executed, and what it will not do

- `init_db()` lives in Phase 3.1, not here: in Phase 1 there is no schema to apply and no test
  demanding the code, which is why the plan defers it.
- `CREATE TABLE IF NOT EXISTS` makes the DDL **idempotent** — running it twice is measured as
  a no-op — so it can run on every start without destroying anything.
- The flip side, and the trap: `IF NOT EXISTS` means the DDL **never migrates**. Changing a
  column here does nothing to a database file that already exists; the old table simply stays.
  With no migration tooling in scope, the way to apply a change is to delete
  `instance/pfo2.db` and let it be recreated. That is acceptable only because the database is
  disposable and never versioned (D-13). If real data ever lives here, this decision has to be
  revisited before the schema changes again.

---

## 8. Mapping to requirements

Every clause traces to a rule, and every rule has a test point. Verified against
`docs/requisitos.md`.

| Clause | Rule | Decision | Requirement | TP |
|---|---|---|---|---|
| `usuarios.usuario` `UNIQUE COLLATE NOCASE` | unique and case-insensitive | D-11 | RF-03 | TP-03, TP-19 |
| `usuarios.password_hash NOT NULL` | the plaintext password is never persisted | D-14 | RF-02 | TP-04 |
| `tareas.titulo CHECK (length <= 200)` | title at most 200 characters | D-19 | RF-13 | TP-12 |
| `tareas.completada CHECK (IN (0,1))` | a task carries a boolean | D-22 | RF-10 | TP-13, TP-17 |
| `tareas.usuario_id REFERENCES ... ON DELETE CASCADE` + the PRAGMA | referential integrity | D-11 | RNF-07 | TP-20 |
| every `NOT NULL` | a required column is never absent | — | RF-02, RF-10, RF-13 | TP-04, TP-13, TP-12 |
| `usuario_id` absent from every response | the owner is never exposed | D-01, D-06 | RF-10 | TP-13, TP-21 |

The complete `RF ↔ TP ↔ TC ↔ test file ↔ result` matrix is built in Phase 1.6 and closed in
Phase 9.2. This table is the schema's share of it.
