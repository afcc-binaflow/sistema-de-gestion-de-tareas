"""Acceso a SQLite: conexion, PRAGMA obligatorios y ciclo de vida por peticion.

Solo acceso a datos. Nada de HTTP ni de hashing aca (RNF-11).

El modulo tiene dos mitades a proposito:

- `conectar()` es Python puro y sin Flask, y es el seam que usan los tests de
  DAO: se les pasa una conexion en memoria y se ejercita el SQL sin levantar la
  aplicacion.
- `obtener_conexion()` y `cerrar_conexion()` son el ciclo de vida de Flask, que
  existe solo para que una peticion no abra una conexion por consulta.
"""

import sqlite3

from flask import current_app, g


def conectar(ruta):
    """Abre una conexion a SQLite lista para usar.

    Los PRAGMA se aplican aca, en el unico lugar donde se abre una conexion.
    `foreign_keys` es **por conexion**: olvidarlo en un solo punto deja el
    esquema sin integridad referencial, las claves foraneas decorativas y nada
    lo delata (RNF-07, TP-20). Concentrar la apertura es lo que hace que el
    olvido sea imposible en vez de improbable.

    `busy_timeout` evita "database is locked" cuando varios hilos escriben al
    mismo tiempo (RNF-16, TC-DB-08). Sin el, el primer bloqueo lanza de
    inmediato.

    `row_factory` hace que las filas se comporten como diccionarios, asi que la
    capa HTTP arma el JSON por nombre de columna y no por indice.
    """
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute("PRAGMA busy_timeout = 5000")
    return conexion


def obtener_conexion():
    """Devuelve la conexion de la peticion, abriendola la primera vez.

    Para bases en memoria reutiliza la conexion persistente que creo `init_db`,
    de modo que el esquema (y los datos) sobreviven entre peticiones.
    """
    if (
        current_app.config["DATABASE"] == ":memory:"
        and getattr(current_app, "_db_conexion_persistente", None) is not None
    ):
        return current_app._db_conexion_persistente
    if "conexion" not in g:
        g.conexion = conectar(current_app.config["DATABASE"])
    return g.conexion


def cerrar_conexion(excepcion=None):
    """Cierra la conexion al terminar la peticion.

    Flask llama a esta funcion aunque la vista haya fallado — para eso existe
    `teardown_appcontext`. Sin ella, una conexion por peticion queda abierta.
    """
    conexion = g.pop("conexion", None)
    if conexion is not None:
        conexion.close()


# DDL de record (docs/modelo-de-datos.md §2). init_db() lo ejecuta tal cual.
# Si este bloque y el documento se desincronizan, el documento tiene razon.
DDL = """
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
"""


def inicializar(conexion):
    """Crea las tablas si no existen. Idempotente (CREATE TABLE IF NOT EXISTS)."""
    conexion.executescript(DDL)
    conexion.commit()


def init_db(app):
    """Inicializa el esquema de la aplicacion.

    Recibe la app de forma explicita: `current_app` solo existe dentro de un
    contexto de aplicacion, y esta funcion corre al construirla, antes de que
    haya ninguno abierto.

    Para bases en archivo, abre una conexion, crea las tablas y la cierra: el
    archivo persiste en disco. Para bases en memoria, mantiene una conexion
    viva en la app, porque SQLite destruye una base `:memory:` cuando se cierra
    la ultima conexion que la referencia.
    """
    if app.config["DATABASE"] == ":memory:":
        conexion = conectar(":memory:")
        inicializar(conexion)
        app._db_conexion_persistente = conexion
    else:
        with app.app_context():
            conexion = obtener_conexion()
            inicializar(conexion)
            cerrar_conexion()


def init_app(app):
    """Registra el cierre de la conexion en el ciclo de vida de la app."""
    app.teardown_appcontext(cerrar_conexion)
