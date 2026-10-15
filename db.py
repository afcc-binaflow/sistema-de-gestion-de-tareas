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

    `row_factory` hace que las filas se comporten como diccionarios, asi que la
    capa HTTP arma el JSON por nombre de columna y no por indice.
    """
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def obtener_conexion():
    """Devuelve la conexion de la peticion, abriendola la primera vez."""
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


def init_app(app):
    """Registra el cierre de la conexion en el ciclo de vida de la app."""
    app.teardown_appcontext(cerrar_conexion)
