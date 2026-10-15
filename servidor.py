"""Punto de entrada: compone los modulos y arma la aplicacion (D-18).

`create_app(config)` es la pieza que habilita todo el testing: permite
instanciar la aplicacion con una base en memoria sin tocar el codigo de
produccion. Sin esta funcion, el resto de la estrategia de pruebas no es
implementable.

`create_app` conserva el nombre en ingles porque es la convencion universal de
Flask y la nomenclatura que esperan los runners y el hosting.
"""

from pathlib import Path

from flask import Flask

import db
import routes
from config import Config


def create_app(config_objeto=None):
    """Crea la aplicacion. Recibe una clase de configuracion, o usa `Config`."""
    app = Flask(__name__)
    app.config.from_object(config_objeto or Config)

    # Falla rapido y con un mensaje util. Sin esto, la ausencia de SECRET_KEY
    # reaparece mas tarde como un error opaco al firmar un token (RNF-03).
    if not app.config["TESTING"] and not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "Falta SECRET_KEY en el entorno. Copia .env.example a .env y "
            "completa el valor antes de levantar el servidor."
        )

    # RNF-10 / TP-23: el JSON viaja como UTF-8 real y no escapado (\u00f1), para
    # que la evidencia muestre la enie tal como se envio.
    app.json.ensure_ascii = False

    # SQLite no crea carpetas: sin esto, la primera conexion falla si la base
    # configurada todavia no existe. Solo se toca el disco si la configuracion
    # apunta a un archivo; los tests usan `:memory:`.
    if app.config["DATABASE"] != ":memory:":
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    routes.registrar_rutas(app)

    return app


if __name__ == "__main__":
    # Solo para desarrollo local. En PythonAnywhere levanta la app el WSGI del
    # hosting (D-08), con un solo proceso y threads (RNF-16).
    #
    # `debug` no se activa nunca por defecto: con el modo debug, Flask expone el
    # depurador de Werkzeug, que permite ejecutar codigo en el servidor (TP-16).
    create_app().run()
