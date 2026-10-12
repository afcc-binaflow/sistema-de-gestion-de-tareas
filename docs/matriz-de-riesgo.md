# Risk matrix — Phase 0.4

**Purpose.** Rank the 25 test points by risk, so that test effort is allocated deliberately
instead of equally. This document does not decide *what* to test — `docs/requisitos.md` and
`docs/revision-testabilidad.md` already did that. It decides **what to write first, what gets
automated, and what may stay manual.**

**The premise.** Testing everything with equal rigour is not thoroughness; it is a way of
running out of time on the wrong things. The 25 test points do not carry the same risk, and the
matrix models the difference explicitly so that the ranking can be argued with and corrected
rather than assumed.

---

## 1. Method

### Probability (P) — will this defect reach delivery?

The question is not "could this bug exist?" but "would it still be there when the project is
handed in?". A defect that breaks the first manual attempt is not a real risk; a defect that
leaves a working-looking system is.

| Score | Meaning |
|---|---|
| **1** | **Unlikely.** A library guarantees it, the language prevents it, or it breaks loudly the instant anyone exercises the happy path. |
| **2** | **Possible.** Needs care, but an attentive implementation gets it right; it surfaces now and then under ordinary use. |
| **3** | **Likely.** The framework's default is wrong, or the rule has no natural guard, or it only appears under conditions nobody exercises by hand. |

### Impact (I) — what happens if it ships?

| Score | Meaning |
|---|---|
| **1** | **Minor.** Cosmetic, or a wrong-but-harmless status code, or a message. |
| **2** | **Significant.** A core feature is broken or returns wrong results, or data is corrupted. |
| **3** | **Critical.** Credentials are exposed or recoverable, data leaks across users, data is lost, or unauthorized access is possible. |

### Score and band

`score = P × I`, ranging from 1 to 9.

| Score | Band | What the band means for effort |
|---|---|---|
| 9 | **Critical** | Written first, with happy path, negative cases and boundaries. Automated. Never skipped for time. |
| 4–6 | **High** | Automated, with at least the happy path and the main negative case. |
| 2–3 | **Medium** | At least one case each; automate the cheap ones. |
| 1 | **Low** | One case, and it may stay manual. |

### The one adjustment: an impact floor

A plain `P × I` ranking has a known blind spot, and it is the reason most risk matrices quietly
fail. Consider TP-04: hashing a password with `werkzeug.security` has a probability of 1 — a
library does the work. Its impact is 3. Multiplied, it scores 3 and lands in *Medium*, below a
validation test at 6. But "medium" is the wrong answer for the one defect that loses every
user's password.

The arithmetic is not wrong; the interpretation is. **Multiplication is the wrong operator for
a catastrophe.** Rare-and-fatal must not be averaged against frequent-and-annoying.

So one rule is applied, and it is applied explicitly rather than by judgement:

> **Any test point whose impact is 3 is at minimum *High*, whatever its probability.**

TP-04 and TP-14 are the two test points this moves. Both are marked with `floor` in the table
so the adjustment is visible rather than silent. Within a band, the raw score still orders the
work, which is why the floored entries sit last inside *High*.

---

## 2. The grid

Rows are probability, columns are impact. The `←` column marks the cells the impact floor
lifted out of their arithmetic band.

| P \ I | Impact 1 | Impact 2 | Impact 3 |
|---|---|---|---|
| **Prob 3** | TP-18, TP-22, TP-23 | TP-02, TP-20 | TP-11 |
| **Prob 2** | TP-01, TP-12 | TP-03, TP-07, TP-17, TP-19 | TP-05, TP-08, TP-09, TP-10, TP-15, TP-16, TP-21 |
| **Prob 1** | TP-25 | TP-06, TP-13, TP-24 | TP-04, TP-14 ← |

The shape is the point. Every entry in the bottom-right cell is a defect that no amount of
manual clicking would reveal. Every entry in the bottom-left and bottom-middle cells is
something a person would hit within a minute of trying the project. **The tests it feels most
natural to write first — register, log in, run a CRUD cycle — are the ones least likely to find
anything. The ones that get skipped are where the defects live.**

---

## 3. The matrix

Sorted by band, then score, then TP number.

| TP | Area | P | I | Score | Band | Why these scores |
|---|---|---|---|---|---|---|
| TP-11 | Authorization | 3 | 3 | **9** | Critical | The owner filter has to be repeated in every query, and forgetting it is invisible: your own tasks still behave perfectly. Manual use never reveals it. The single highest-risk defect in the project. |
| TP-02 | Validation | 3 | 2 | 6 | High | Validation is where defects concentrate, and RF-01 now carries four rejection rules after F-05 (missing field, wrong type, empty, over-length). |
| TP-05 | Response shape | 2 | 3 | 6 | High | Returning the whole row dict is the natural implementation, and it carries `password_hash` with it. |
| TP-08 | Token integrity | 2 | 3 | 6 | High | Requires an explicit algorithm allowlist. `alg: none` is a known attack that a permissive decode accepts. |
| TP-09 | Token lifetime | 2 | 3 | 6 | High | `exp` is verified by default but sits one flag away from being disabled, and nothing else in the system would notice. |
| TP-10 | Middleware | 2 | 3 | 6 | High | Six endpoints must each carry the check. Five correct and one forgotten looks exactly like a working system. |
| TP-15 | Persistence | 2 | 3 | 6 | High | Corruption is unlikely (SQLite is ACID), but `database is locked` under concurrent threads is a documented footgun — and RNF-16 makes threaded access the deployment model. |
| TP-16 | Error handling | 2 | 3 | 6 | High | Flask exposes the Werkzeug debugger when debug is on. The same careless flag that leaks a stack trace also opens remote code execution. |
| TP-20 | Schema | 3 | 2 | 6 | High | `PRAGMA foreign_keys` is **per connection**. One connection opened without it silently disables every foreign key, and the schema still looks correct. |
| TP-21 | Representation | 2 | 3 | 6 | High | The page is public by design (D-04 revisada), so the guarantee moved to "carries no data" — and passing tasks into the template context by accident is a leak. |
| TP-03 | Uniqueness | 2 | 2 | 4 | High | Needs the `UNIQUE` constraint, `COLLATE NOCASE` and the exception mapping to line up. Three places for one rule. |
| TP-07 | Enumeration | 2 | 2 | 4 | High | Returning a different message for "no such user" and "wrong password" is the obvious implementation, and it is useful to an attacker. |
| TP-17 | Client contract | 2 | 2 | 4 | High | Field-name and status-code drift between client and API is the classic integration defect. F-03 and F-04 in Phase 0.3 were precisely this class. |
| TP-19 | Uniqueness | 2 | 2 | 4 | High | SQLite compares case-sensitively by default, so `Juan` and `juan` coexist unless the column says otherwise. |
| TP-04 | Hashing | 1 | 3 | 3 `floor` | High | `werkzeug.security` makes plaintext storage unlikely. The impact is total credential loss, so a probability argument does not get to demote it. |
| TP-14 | SQL injection | 1 | 3 | 3 `floor` | High | Parameter binding is the natural idiom. But one string-formatted query anywhere is a full database read. |
| TP-18 | Input handling | 3 | 1 | 3 | Medium | `request.get_json()` raises without `silent=True`, and the default failure is a 415 HTML page, not the required 400 JSON. |
| TP-22 | Error handling | 3 | 1 | 3 | Medium | Flask answers 404, 405 and 500 with HTML unless every one of them is overridden. |
| TP-23 | Encoding | 3 | 1 | 3 | Medium | Three encoding boundaries in a row — console, HTTP, SQLite — with `cp1252` at the first one. |
| TP-01 | Routing | 2 | 1 | 2 | Medium | Flask's automatic 405 is HTML, so the contract fails unless it is overridden. |
| TP-06 | Login | 1 | 2 | 2 | Medium | The happy path. Any defect is visible in the first manual attempt. |
| TP-12 | Validation | 2 | 1 | 2 | Medium | Needs an explicit length check; the consequence is bad data, not a breach. |
| TP-13 | CRUD flow | 1 | 2 | 2 | Medium | The happy path again: wide, but shallow. |
| TP-24 | Scope boundary | 1 | 2 | 2 | Medium | It only breaks if a password policy is introduced that the brief never asked for, and D-14 decided not to. |
| TP-25 | Session | 1 | 1 | 1 | Low | Nothing is implemented to test. The assertion is that no blacklist exists and the README says so. |

| Band | Count |
|---|---|
| Critical | 1 |
| High | 15 |
| Medium | 8 |
| Low | 1 |
| **Total** | **25** |

*Fifteen of twenty-five in the top two bands is not an over-reaction.* The brief grades
authentication, authorization and persistence — those are exactly the areas that score 3 on
impact, and the impact floor keeps them there. The useful information is not the band counts;
it is the ordering inside each band.

---

## 4. Risk order is not execution order

These are two different orderings, and conflating them causes real mistakes.

**Risk** orders *effort*: how much attention, how many cases, automated or not.
**Dependency** orders *execution*: what must exist before a test can run at all.

The dependency chain introduces these constraints, which the matrix does not show:

1. TP-02 before TP-06 — there is no user to log in with until registration works.
2. TP-06 before TP-08, TP-09, TP-10 and TP-11 — there is no token to tamper with, expire, omit
   or authorize until login issues one.
3. TP-10 before TP-11 — owner isolation cannot be tested before the authentication check that
   establishes *who* the owner is.
4. TP-03 and TP-19 share one database fixture; written apart they duplicate setup.
5. TP-15 and the production-persistence check need the deployment, so they run in Phase 11 even
   though they score High.

So a test point can be High risk and late in the schedule (TP-21 needs a running app), and it
can be Medium risk and first in the chain (TP-02). **Neither fact contradicts the other.** The
matrix answers "how much", the chain answers "when".

---

## 5. Residual risk accepted

Declaring what is *not* tested is part of the analysis, not an omission from it. Each of these
is a deliberate decision, and each is traceable:

| Not tested | Why it is accepted |
|---|---|
| Throughput and latency under load | The brief specifies no performance requirement. TP-15 covers concurrency *correctness*, not speed. |
| Multi-process concurrency | Removed by design: RNF-16 deploys a single worker with threads, so the failure mode cannot occur. |
| Visual rendering and layout of the welcome page | No layout or design requirement exists. The page is verified as HTML that carries no data. |
| Cross-browser matrix | One browser, one capture (E-04). The page has no scripting. |
| Fuzzing or broader penetration testing | TP-14 stays at the documented injection plus a review of every statement. No fuzzing requirement exists. |
| Mobile clients | Out of scope: no mobile deliverable. |
| TLS/HTTPS configuration | Terminated by the hosting platform, not by this application. |
| Hosting availability and failover | Outside the project's control. Only the app's behaviour across a deploy is covered: SQLite persistence (D-08). |
| Password strength | D-14 decided there is no policy beyond non-empty, because the brief's own `1234` example must keep working (TP-24). Nothing exists to test. |
| Server-side token revocation | Declared a non-goal in D-17. TP-25 asserts the limitation is documented rather than pretending it is absent. |

---

## 6. What this changes in the plan

1. **Test-as-you-go becomes concrete.** Each Critical and High test point is written alongside
   the feature it covers, not collected at the end. This is the specific failure the previous
   session's plan had, and Phase 2.4/2.5 already moved the infrastructure forward to fix it.
2. **Automation is decided by economics, not by band.** TP-18, TP-22 and TP-23 score only
   Medium, but each covers a framework default, each has probability 3, and each is a handful
   of lines once the fixture exists. All three get automated. Conversely TP-25 scores Low and
   is a single assertion — also automated, because manual evidence for it would cost more than
   the test.
3. **TP-21 changed meaning** in Phase 0.3 and its risk was re-scored against the new
   requirement: the page is public, so the test now asserts that it carries no data. Same
   impact, different thing being verified.
4. **The matrix is an input to the traceability matrix** in Phase 9.2, which must show every RF
   mapped to at least one test. Risk determines the depth of each mapping, not its existence.

---

## 7. Cross-references

| Concern | Document |
|---|---|
| What must be tested, with verification criteria | `docs/requisitos.md` |
| Why the requirement statements are testable, and the defects found | `docs/revision-testabilidad.md` |
| Why each scope and design choice was made | `docs/decisiones.md` |
| The test point catalog and test cases derived from it | `docs/casos-de-prueba.md` (Phase 1.6) |
| The forward link TP → TC → test file → result | built in Phase 9.2 |
