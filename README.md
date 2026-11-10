# PFO 2 — Task Manager API

A small Flask REST API for managing personal tasks, with JWT authentication, a
SQLite database, and a console client. Built for the *PFO 2 (API REST + SQLite +
JWT + console client)* assignment of the TSDS/Redes course.

The API is multi-user: every task belongs to the user who created it, and the
database enforces that boundary at the SQL level, not in Python.

## What is in the box

| Piece | File | Role |
|---|---|---|
| API entry point | `servidor.py` | Composes the app, initialises the database |
| HTTP layer | `routes.py` | Parses requests, calls the DAO, responds |
| Persistence (DAO) | `repository.py` | All SQL lives here |
| Database | `db.py` | Connection, schema, migrations |
| Passwords and JWT | `security.py` | Hashing and token signing/verification |
| Configuration | `config.py` | Reads `os.environ`, never hard-codes a secret |
| Console client | `cliente.py` | Two layers: `ApiDeTareas` (transport) + `menu` (UI) |
| Tests | `tests/` | 156 tests, 99 % coverage (see `docs/trazabilidad.md`) |

## Requirements

- **Python 3.13** — this is the version the deployment target (PythonAnywhere)
  supports. Using a newer interpreter locally will only build something the
  hosting image cannot run. The development machine also has 3.14, which is *not*
  what this project declares.
- `pip` (and a virtual environment, recommended).

## Installation

```bash
# 1. Clone
git clone <repository-url>
cd PFO2

# 2. Create and activate a virtualenv with Python 3.13
python3.13 -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# bash / zsh:
source venv/bin/activate

# 3. Install the five direct dependencies
pip install -r requirements.txt
```

There are only five direct dependencies: Flask, PyJWT, requests, pytest and
pytest-cov. Everything else is pulled in by pip. `werkzeug.security` ships with
Flask, so password hashing costs no extra package.

## Configuration

The API reads two environment variables (see `.env.example`, which is versioned
on purpose and contains no real value):

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `SECRET_KEY` | **Yes** (production) | — | Signs and verifies every JWT. The server refuses to start without it |
| `DATABASE_PATH` | No | `instance/pfo2.db` | Path to the SQLite file |

The project **does not load `.env` automatically** — there is no `python-dotenv`
in `requirements.txt` on purpose. Set the variables in the shell that launches
the app:

```powershell
# Windows PowerShell
$env:SECRET_KEY = "a long random value"
$env:DATABASE_PATH = "instance/pfo2.db"   # optional
python servidor.py
```

```bash
# bash / zsh
export SECRET_KEY="a long random value"
export DATABASE_PATH="instance/pfo2.db"   # optional
python servidor.py
```

Generate a real key — do not type a word:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The `instance/` directory (and any `*.db`) is ignored by `.gitignore`, so the
database can never reach the repository.

## Running the API

```bash
python servidor.py
```

The server starts on `http://127.0.0.1:5000`. `debug` is never enabled by
default: Werkzeug's debugger allows remote code execution, so leaving it on is a
security defect, not a convenience.

The welcome page is served at `GET /tareas` and needs no token. The JSON API
lives under `/api/tareas`.

## Running the console client

In a second terminal, with the API already running:

```bash
python cliente.py
```

The client talks to `http://127.0.0.1:5000` by default. Point it at another
API with `PFO2_API_URL`:

```powershell
$env:PFO2_API_URL = "http://another-api.test"
python cliente.py
```

Menu:

```
=== Gestor de tareas ===
Sin sesión iniciada.
1. Registrarse
2. Iniciar sesión
3. Listar tareas
4. Crear tarea
5. Editar tarea
6. Borrar tarea
7. Salir
```

The token lives **only in memory** (`self.token`) and is never written to disk.
Closing the client loses the session — that is deliberate: a JWT saved in plain
text on disk is exactly what the hashing exists to prevent.

## API quick reference

Full contract in [`docs/api.md`](docs/api.md). Summary of the routes:

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/tareas` | none | Welcome page (HTML) |
| `POST` | `/registro` | none | Create an account |
| `POST` | `/login` | none | Obtain a JWT (`{"token": "..."}`) |
| `GET` | `/api/tareas` | Bearer | List the authenticated user's tasks |
| `POST` | `/api/tareas` | Bearer | Create a task |
| `GET` | `/api/tareas/<id>` | Bearer | Read one task |
| `PUT` | `/api/tareas/<id>` | Bearer | Replace a task |
| `DELETE` | `/api/tareas/<id>` | Bearer | Delete a task |

The token travels in the `Authorization: Bearer <token>` header, never in the
URL or in a cookie — URLs end up in logs, history and proxies.

### Example session with curl

```bash
# 1. Register
curl -s -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"usuario": "juan", "contraseña": "1234"}'
# -> {"usuario": "juan"}

# 2. Log in — the field is named exactly "token"
curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "juan", "contraseña": "1234"}'
# -> {"token": "eyJhbGciOi..."}

TOKEN="eyJhbGciOi..."

# 3. Create a task
curl -s -X POST http://127.0.0.1:5000/api/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"titulo": "Estudiar SQLite", "completada": false}'
# -> {"id": 1, "titulo": "Estudiar SQLite", "completada": false}

# 4. List (only your own tasks)
curl -s http://127.0.0.1:5000/api/tareas \
  -H "Authorization: Bearer $TOKEN"
# -> [{"id": 1, "titulo": "Estudiar SQLite", "completada": false}]

# 5. Update (full replacement)
curl -s -X PUT http://127.0.0.1:5000/api/tareas/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"titulo": "Estudiar SQLite a fondo", "completada": true}'

# 6. Delete — 204, no body
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE http://127.0.0.1:5000/api/tareas/1 \
  -H "Authorization: Bearer $TOKEN"
# -> 204

# Public route, no token needed
curl -s http://127.0.0.1:5000/tareas | head -c 80
```

Tokens expire after **8 hours** (D-20) and carry only the user id (`sub`) and the
expiry — never the password or its hash. A JWT is signed, not encrypted: anyone
can decode the payload.

## Running the tests

```bash
# All tests
python -m pytest -q

# With coverage
python -m pytest -q --cov=cliente --cov=config --cov=db \
  --cov=repository --cov=routes --cov=security --cov=servidor --cov-report=term-missing
```

Result at the current commit: **156 passed**, 99 % coverage (431 statements,
2 misses — both `if __name__ == "__main__":` entry points). The suite runs
against an **in-memory** database; it never touches `instance/pfo2.db`.

The test strategy is a pyramid: 20 unit (hashing + DAO), 109 integration
(endpoints via Flask's `test_client`) and 22 end-to-end (the real console client
against the real app, no port opened). See `docs/casos-de-prueba.md` and
`docs/trazabilidad.md` for the full catalogue and the requirement-to-test map.

## Scope decisions (declared, not silent)

This project deliberately builds **only** what the assignment asks for. Three
additions go beyond the brief and are declared here, as `AGENTS.md` requires:

- **Real task CRUD** (D-01). The brief's placeholder is replaced by a working
  `POST/GET/PUT/DELETE` over `/api/tareas`, because a placeholder is not a
  deliverable.
- **Console client as a deliverable** (D-05). It is a required hand-in item, so
  it is a first-class component with its own tests, not a script.
- **`completada` field** (D-22). The brief's example task needs a status flag;
  it is added as a boolean.

Everything else is a **non-goal** (D-17): no user roles or permissions beyond
owner isolation, no pagination, no search or filtering, no refresh tokens, no
rate limiting, no Docker, no ORM, no caching, no background jobs, no async, no
admin panel and no `PATCH` (full replacement via `PUT` is simpler and
idempotent). No speculative abstractions or "future" extension points exist.

## Known limitations

These are deliberate and documented, not oversights:

- **Login timing oracle.** `/login` takes longer for a wrong password than for a
  missing user (~296× measured). Closing it needs a decoy hash on every failed
  login with no rate limiting in scope. Documented as D-29, not hidden.
- **No server-side token revocation.** A stolen token stays valid until it
  expires (8 h). Logout is client-side by design (D-17), pinned by `TC-CLI-01`.
- **No password policy.** `1234` is a valid password — the brief's own example
  must keep working (TP-24).
- **No rate limiting.** Credential brute force is bounded only by password
  entropy. Out of scope per YAGNI.
- **SQLite concurrency.** With several writers at once you get
  `database is locked`. The deployment uses a single worker with threads
  (`--workers 1 --threads 4`), which is enforced by the run command, not by code.

## Deployment

Two different things are deployed, and conflating them is the common mistake:

1. **Static site (GitHub Pages)** — `docs/` only. Pages serves HTML, CSS and
   JavaScript; **it cannot run Flask or any Python** (R-02). It hosts the
   presentation site and the documentation, never the API.
2. **Runtime (API)** — a Python hosting service. The API runs under `gunicorn`
   (Flask's built-in server is for development only). `gunicorn` is a *host*
   dependency, not a project one — `requirements.txt` declares only the five
   runtime deps, and on PythonAnywhere you do not use gunicorn at all: you point
   the hosting's WSGI configuration at `create_app()`.

   ```bash
   # On a host that runs gunicorn directly:
   gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8000 servidor:create_app()
   ```

   `SECRET_KEY` comes from the environment, `debug=False`, and the database is
   initialised on startup.

   **Persistence caveat (D-08).** On most free hosts the filesystem is
   *ephemeral*: the container is recreated on every deploy and restart, and the
   SQLite file disappears with it. PythonAnywhere keeps a persistent filesystem
   on the free tier, so the database survives there. On Render/Railway the same
   code runs, but the database resets on each deploy — which is an honest
   limitation, not a bug, and it demonstrates the difference between a local
   file and a persistent volume.

## Project structure

```
PFO2/
├── servidor.py          # app factory + entry point
├── routes.py            # HTTP layer
├── repository.py        # DAO: all SQL
├── db.py                # connection + schema
├── security.py          # hashing + JWT
├── config.py            # environment-driven config
├── cliente.py           # console client (transport + UI)
├── requirements.txt
├── pytest.ini
├── templates/
│   └── bienvenida.html  # public welcome page
├── tests/               # pytest suite
└── docs/
    ├── api.md           # full API contract
    ├── requisitos.md    # requirements (RF/RNF/DEL)
    ├── casos-de-prueba.md
    ├── matriz-de-riesgo.md
    ├── trazabilidad.md  # requirement ↔ test matrix, secret scan, verdict
    ├── decisiones.md    # decision log (D-01 … D-30)
    ├── modelo-de-datos.md
    ├── revision-testabilidad.md
    └── diagramas/
        └── flujo-pfo2.drawio
```

## Further reading

- [`docs/api.md`](docs/api.md) — the full API contract, field reference and
  status code catalogue.
- [`docs/requisitos.md`](docs/requisitos.md) — every functional and
  non-functional requirement.
- [`docs/trazabilidad.md`](docs/trazabilidad.md) — forward and reverse
  traceability matrix, secret scan of the whole history, residual risk and the
  Phase 9 verdict.
- [`docs/decisiones.md`](docs/decisiones.md) — the decision log behind every
  choice above.

## License

Academic project. No license granted for reuse.
