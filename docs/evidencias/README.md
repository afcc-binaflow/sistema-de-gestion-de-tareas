# Evidence — PFO 2

Each file below is the **verbatim output** of a command run against the project at the
commit that closes Phase 10. None of them is a screenshot: they are reproducible,
and the command that regenerates each one is written next to it. If a file cannot be
regenerated with its command, it is not evidence — it is a memory.

| # | File | What it proves | Regenerate with |
|---|---|---|---|
| 01 | `01-pytest-v.txt` | The whole suite is green (156 tests) | `python -m pytest -v` |
| 02 | `02-cobertura.txt` | 99 % coverage, 2 misses, both `__main__` entry points | `python -m pytest -q --cov=cliente --cov=config --cov=db --cov=repository --cov=routes --cov=security --cov=servidor --cov-report=term-missing` |
| 03 | `03-bienvenida.html` | `GET /tareas` returns `200 text/html; charset=utf-8` with no token (RF-09, RNF-10) | `curl -s http://127.0.0.1:5000/tareas` (with the API running) |
| 04 | `04-curl-flow.txt` | Register → login → create → list → update → delete with the documented status codes | see the commands inside the file |
| 05 | `05-cliente-ciclo.txt` | Full cycle through the console client, including the UTF-8 round trip of `ñ` | `printf '1\nmaria\n1234\n2\nmaria\n1234\n4\nEstudiar SQLite\n3\n5\n1\nEstudiar SQLite a fondo\ns\n3\n6\n1\n3\n7\n' \| python cliente.py` |

Two of the six captures the assignment asks for are **not** in this folder, because
they cannot be produced from this repository alone:

- `pytest -v` and the coverage report above cover items 1 and 2.
- The `curl` flow and the welcome page cover items 3 and 4.
- The console client cycle covers item 5.
- **Item 6 (the deployed public API responding) and the screenshots themselves**
  require a running deployment and a human with a browser. They are produced in
  Phase 11 and Phase 10.4 respectively, and are added to this folder at that point.

Run every command from the repository root, inside the virtualenv of
`requirements.txt`, on Python 3.13.
