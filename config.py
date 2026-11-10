"""Configuracion de la aplicacion.

Se lee del entorno y nunca se hardcodea un secreto (RNF-03, D-13). Este modulo
no importa Flask a proposito: es configuracion pura y se puede ejercitar sin
levantar la aplicacion.

`ConfigTest` es el seam que habilita toda la estrategia de testing: apunta a una
base en memoria, asi que los tests instancian la app sin tocar el codigo de
produccion ni el archivo de la base real (D-18).
"""

import os
from pathlib import Path

DIRECTORIO_BASE = Path(__file__).resolve().parent

# El directorio `instance/` es el que Flask reserva para datos locales. La base
# esta ignorada por `*.db` en .gitignore, asi que no puede filtrarse al repo.
RUTA_BASE_POR_DEFECTO = DIRECTORIO_BASE / "instance" / "pfo2.db"


class Config:
    """Configuracion de desarrollo y de produccion."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE = os.environ.get("DATABASE_PATH", str(RUTA_BASE_POR_DEFECTO))

    # D-20: el token vive 8 horas.
    HORAS_EXPIRACION_TOKEN = 8

    TESTING = False


class ConfigTest(Config):
    """Configuracion de los tests: base en memoria, sin tocar archivos.

    La `SECRET_KEY` de los tests es fija y publica a proposito: no protege nada
    real y tenerla escrita hace que los tokens de prueba sean reproducibles.
    Mide 32 bytes o mas porque HS256 recomienda ese minimo para HMAC-SHA256
    (RFC 7518 §3.2): con una clave corta `PyJWT` advierte y la firma es mas
    debil. Una clave de test corta esconde ese aviso en la suite, que es donde
    mas barato se ve.
    """

    TESTING = True
    DATABASE = ":memory:"
    SECRET_KEY = "clave-solo-para-tests-de-32-bytes-o-mas"
