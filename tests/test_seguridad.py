"""Tests de la capa de seguridad (Fase 4, TC-SEG + token).

Hashing y JWT. El truco para TP-09 (expiracion) es pasar un `exp` ya pasado
a `crear_token`, sin esperar ni agregar dependencias.
"""

import base64
import json
import time

import jwt
import pytest

from security import (
    HORAS_EXPIRACION_TOKEN,
    crear_token,
    decodificar_token,
    hashear_password,
    verificar_password,
)

CLAVE = "clave-solo-para-tests-de-seguridad-32b"


# ---------------------------------------------------------------------------
# TC-SEG-01 (TP-04): irreversibilidad
# ---------------------------------------------------------------------------
def test_hashear_password_no_es_texto_plano():
    assert hashear_password("1234") != "1234"


# ---------------------------------------------------------------------------
# TC-SEG-02 (TP-04): salt aleatorio
# ---------------------------------------------------------------------------
def test_hashear_password_dos_hashes_distintos():
    assert hashear_password("1234") != hashear_password("1234")


# ---------------------------------------------------------------------------
# TC-SEG-03 (TP-04): verificar correcta / incorrecta
# ---------------------------------------------------------------------------
def test_verificar_password_correcta_e_incorrecta():
    h = hashear_password("1234")
    assert verificar_password(h, "1234") is True
    assert verificar_password(h, "otra") is False


# ---------------------------------------------------------------------------
# TC-SEG-04 (RNF-03): sin SECRET_KEY en el entorno, falla rapido
# ---------------------------------------------------------------------------
def test_firmar_sin_secret_key_falla_rapido(monkeypatch):
    """Sin clave no se firma un token con una clave vacia o adivinable.

    `create_app` ya valida al arrancar, pero `security` se puede importar solo
    (lo hace el cliente de consola). Si la clave faltara aca, `jwt` firmaria con
    `None` y el token saldria valido sin que nadie lo note.
    """
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        crear_token(42)


# ---------------------------------------------------------------------------
# TC-SEG-05 (RNF-03): sin clave explicita, `security` usa la del entorno
# ---------------------------------------------------------------------------
def test_sin_clave_explicita_usa_la_del_entorno(monkeypatch):
    """El modulo de seguridad no conoce Flask: la clave le llega por parametro
    o por el entorno (routes.py §4.2 pasa la de la app; el cliente de consola
    importa `security` solo).

    El test fija esa segunda via: si desapareciera, `crear_token(42)` sin clave
    reventaria en cualquier consumidor que no tenga una app Flask a mano.
    """
    monkeypatch.setenv("SECRET_KEY", CLAVE)

    token = crear_token(42)

    assert decodificar_token(token)["sub"] == "42"


# ---------------------------------------------------------------------------
# Token: propio decodifica y trae el sub correcto
# ---------------------------------------------------------------------------
def test_token_propio_decodifica_y_trae_sub():
    token = crear_token(42, clave=CLAVE)
    payload = decodificar_token(token, clave=CLAVE)
    assert payload["sub"] == "42"


# ---------------------------------------------------------------------------
# Token: firma alterada (1 char) -> error (TP-08)
# ---------------------------------------------------------------------------
def test_token_firma_alterada_falla():
    token = crear_token(42, clave=CLAVE)
    ultimo = token[-1]
    reemplazo = "a" if ultimo != "a" else "b"
    alterado = token[:-1] + reemplazo
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(alterado, clave=CLAVE)


# ---------------------------------------------------------------------------
# Token: firmado con otra clave -> error (TP-08)
# ---------------------------------------------------------------------------
def test_token_otra_clave_falla():
    token = crear_token(42, clave=CLAVE)
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(token, clave="otra-clave-muy-larga-para-evitar-warning")


# ---------------------------------------------------------------------------
# Token: alg:none -> error (TP-08)
# ---------------------------------------------------------------------------
def test_token_alg_none_falla():
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "42", "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    token = f"{header}.{payload}."
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(token, clave=CLAVE)


# ---------------------------------------------------------------------------
# Token: exp en el pasado -> error (TP-09)
# ---------------------------------------------------------------------------
def test_token_expirado_falla():
    token = crear_token(42, clave=CLAVE, exp=int(time.time()) - 10)
    with pytest.raises(jwt.ExpiredSignatureError):
        decodificar_token(token, clave=CLAVE)


# ---------------------------------------------------------------------------
# Token: la expiracion es de 8 horas (TC-TOK-01, D-20)
# ---------------------------------------------------------------------------
def test_el_token_expira_a_las_ocho_horas():
    """D-20 fija 8 h. Se afirma la **diferencia**, no `exp` contra el reloj.

    Un `exp` calculado por `time.time()` no se puede comparar con un valor fijo:
    el test se volveria dependiente del momento en que corre. La resta `exp -
    iat` es la duracion real del token y no envejece.
    """
    token = crear_token(42, clave=CLAVE)
    payload = decodificar_token(token, clave=CLAVE)

    assert payload["exp"] - payload["iat"] == HORAS_EXPIRACION_TOKEN * 3600
    assert payload["exp"] - payload["iat"] == 28800


# ---------------------------------------------------------------------------
# Token: el payload no filtra password ni hash (TP-05, RNF-06)
# ---------------------------------------------------------------------------
def test_payload_no_filtra_password_ni_hash():
    token = crear_token(42, clave=CLAVE)
    payload = decodificar_token(token, clave=CLAVE)
    assert "password" not in payload
    assert "password_hash" not in payload
    assert "contrasena" not in payload
    assert "contraseña" not in payload
