"""Capa de seguridad: hashing de passwords y tokens JWT (RNF-01, RNF-03, RNF-06).

`hashear_password` / `verificar_password` centralizan el hashing en un solo
lugar (DRY) y aplican salt aleatorio por password. `crear_token` / `decodificar_token`
firman y validan JWT HS256.

El algoritmo se declara explicitamente al decodificar (`algorithms=["HS256"]`):
sin eso, un atacante puede mandar `alg: none` o cambiar el algoritmo. Es la
vulnerabilidad clasica de las librerias JWT.
"""

import os
import time

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

# D-20: el token vive 8 horas.
HORAS_EXPIRACION_TOKEN = 8


def hashear_password(plano):
    """Hashea una password con salt aleatorio."""
    return generate_password_hash(plano)


def verificar_password(hash_guardado, plano):
    """Verifica una password contra su hash. Devuelve True/False."""
    return check_password_hash(hash_guardado, plano)


def _clave(clave=None):
    if clave is not None:
        return clave
    clave = os.environ.get("SECRET_KEY")
    if not clave:
        raise RuntimeError(
            "Falta SECRET_KEY en el entorno. Copia .env.example a .env y "
            "completa el valor antes de levantar el servidor."
        )
    return clave


def crear_token(usuario_id, clave=None, exp=None):
    """Crea un JWT firmado HS256 con claims sub, iat, exp.

    `exp` se puede pasar para testear expiracion sin esperar (TP-09): si no se
    pasa, se calcula a partir de HORAS_EXPIRACION_TOKEN.
    """
    if exp is None:
        exp = int(time.time()) + HORAS_EXPIRACION_TOKEN * 3600
    payload = {
        "sub": str(usuario_id),
        "iat": int(time.time()),
        "exp": exp,
    }
    return jwt.encode(payload, _clave(clave), algorithm="HS256")


def decodificar_token(token, clave=None):
    """Decodifica y valida un JWT. Lanza jwt.InvalidTokenError si es invalido.

    `require=["exp"]` no es redundante: PyJWT valida el vencimiento **si el claim
    esta** y lo ignora si falta. Sin exigirlo, un token sin `exp` es eterno y D-20
    ("vive 8 horas") deja de ser cierto sin que nada lo delate.
    """
    return jwt.decode(
        token,
        _clave(clave),
        algorithms=["HS256"],
        options={"require": ["exp"]},
    )
