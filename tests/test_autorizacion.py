"""Tests del middleware `@requiere_token` (Fase 7.1, TC-AUT-01..04, TP-08..10).

La autorizacion no se prueba con el camino feliz. Un test que manda un token
valido y recibe 200 pasa aunque el chequeo **no exista**: lo que prueba es que la
ruta funciona, no que este protegida. Por eso el peso esta en lo que NO debe
poder entrar.

El contrato (docs/api.md §1) es explicito: un solo header, un solo esquema, y
**cualquier** otra cosa es un 401 con el mismo cuerpo. El test de identidad byte a
byte esta separado del test de cada causa, porque una implementacion puede dar
401 en todos los casos y aun asi delatar la causa con mensajes distintos.
"""

import jwt
import pytest

import security

ENDPOINTS_PROTEGIDOS = [
    ("get", "/api/tareas"),
    ("post", "/api/tareas"),
    ("get", "/api/tareas/1"),
    ("put", "/api/tareas/1"),
    ("delete", "/api/tareas/1"),
]

MENSAJE_401 = "Token ausente o inválido"


def _error(respuesta):
    """Afirma la forma unica de error del contrato y devuelve el mensaje."""
    assert respuesta.mimetype == "application/json"
    cuerpo = respuesta.get_json()
    assert isinstance(cuerpo, dict)
    assert set(cuerpo) == {"error"}
    return cuerpo["error"]


def _pedir(client, metodo, ruta, cabeceras=None):
    return getattr(client, metodo)(ruta, headers=cabeceras or {})


# ---------------------------------------------------------------------------
# TC-AUT-01 (TP-10): sin token no se entra, en ninguno de los cinco endpoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("metodo, ruta", ENDPOINTS_PROTEGIDOS)
def test_sin_token_todos_los_endpoints_devuelven_401(client, metodo, ruta):
    respuesta = _pedir(client, metodo, ruta)

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


# ---------------------------------------------------------------------------
# TC-AUT-02 (TP-10): el header esta pero el esquema no es Bearer
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "cabecera",
    [
        {"Authorization": ""},
        {"Authorization": "Basic dXN1YXJpbzpjbGF2ZQ=="},
        {"Authorization": "Token abc.def.ghi"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer    "},
    ],
)
def test_esquema_o_token_ausente_devuelve_401(client, cabecera):
    respuesta = client.get("/api/tareas", headers=cabecera)

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


# ---------------------------------------------------------------------------
# TP-08 / TP-09: el token esta, pero no sirve
# ---------------------------------------------------------------------------
def test_token_alterado_devuelve_401(client, token_valido):
    alterado = token_valido[:-2] + ("aa" if token_valido[-2:] != "aa" else "bb")

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {alterado}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_token_expirado_devuelve_401(client, usuario_registrado, app):
    import time

    vencido = security.crear_token(
        usuario_registrado["id"],
        clave=app.config["SECRET_KEY"],
        exp=int(time.time()) - 10,
    )

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {vencido}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_token_firmado_con_otra_clave_devuelve_401(client, usuario_registrado):
    ajeno = security.crear_token(
        usuario_registrado["id"], clave="otra-clave-de-32-bytes-o-mas-para-hs256"
    )

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {ajeno}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_token_sin_claim_sub_devuelve_401(client, app):
    """Un JWT bien firmado pero sin `sub` no identifica a nadie: 401, no 500."""
    sin_sub = jwt.encode({"iat": 1, "exp": 9999999999}, app.config["SECRET_KEY"], algorithm="HS256")

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {sin_sub}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_token_sin_claim_exp_devuelve_401(client, app):
    """D-20 dice que el token vive 8 horas; un token sin `exp` no vence nunca.

    PyJWT valida `exp` **si esta**, y lo ignora si falta: sin exigirlo, un token
    firmado sin vencimiento es eterno y el contrato de §6 es mentira. Solo es
    forjable con la clave, pero una garantia que depende de que nadie la omita no
    es una garantia.
    """
    sin_exp = jwt.encode({"sub": "1", "iat": 1}, app.config["SECRET_KEY"], algorithm="HS256")

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {sin_exp}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_token_con_sub_que_no_es_entero_devuelve_401(client, app):
    """`sub` es un string por contrato, pero un atacante puede firmar lo que sea."""
    raro = jwt.encode({"sub": "abc", "iat": 1, "exp": 9999999999}, app.config["SECRET_KEY"], algorithm="HS256")

    respuesta = client.get("/api/tareas", headers={"Authorization": f"Bearer {raro}"})

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


# ---------------------------------------------------------------------------
# TP-10: las SEIS causas son indistinguibles entre si
# ---------------------------------------------------------------------------
def test_todos_los_401_son_byte_a_byte_identicos(client, token_valido, app):
    sin_header = client.get("/api/tareas")
    malformado = client.get("/api/tareas", headers={"Authorization": "Bearer no-es-un-jwt"})
    esquema_errado = client.get("/api/tareas", headers={"Authorization": "Basic xyz"})
    ajeno = security.crear_token(1, clave="otra-clave-de-32-bytes-o-mas-para-hs256")
    de_otra_clave = client.get("/api/tareas", headers={"Authorization": f"Bearer {ajeno}"})

    respuestas = [sin_header, malformado, esquema_errado, de_otra_clave]

    for respuesta in respuestas:
        assert respuesta.status_code == 401
        assert respuesta.get_data() == sin_header.get_data()
        assert respuesta.mimetype == sin_header.mimetype
    assert sin_header.get_json() == {"error": MENSAJE_401}


# ---------------------------------------------------------------------------
# RF-08 (cobertura extra): el token viaja en el header, no en la URL
# ---------------------------------------------------------------------------
def test_el_token_no_se_acepta_por_query_string(client, token_valido):
    """Un token en la URL termina en logs, historial y proxies: el contrato §1 no lo acepta."""
    respuesta = client.get(f"/api/tareas?token={token_valido}")

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


def test_el_token_no_se_acepta_por_cookie(client, token_valido):
    client.set_cookie("token", token_valido)

    respuesta = client.get("/api/tareas")

    assert respuesta.status_code == 401
    assert _error(respuesta) == MENSAJE_401


# ---------------------------------------------------------------------------
# El contrato de metodo tambien cubre OPTIONS
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ruta", ["/api/tareas", "/api/tareas/1"])
def test_options_devuelve_405_en_json(client, ruta):
    """Flask contesta `OPTIONS` solo, con un 200 HTML: eso rompe el contrato.

    El contrato (§3) dice que la API siempre responde JSON, y §4.4-4.8 que el
    metodo se declara o es un 405. Un `OPTIONS` automatico es una tercera cosa:
    ni lo uno ni lo otro. Y no hace falta: no hay CORS en el alcance.
    """
    respuesta = client.options(ruta)

    assert respuesta.status_code == 405
    assert _error(respuesta) == "Método no permitido"


# ---------------------------------------------------------------------------
# RFC 7235 §2.1: el nombre del esquema es case-insensitive
# ---------------------------------------------------------------------------
def test_el_esquema_bearer_es_case_insensitive(client, token_valido):
    respuesta = client.get("/api/tareas", headers={"Authorization": f"bearer {token_valido}"})

    assert respuesta.status_code == 200


# ---------------------------------------------------------------------------
# TC-AUT-03: el camino feliz, que es el que menos prueba
# ---------------------------------------------------------------------------
def test_token_valido_entra_y_devuelve_la_lista_vacia(client, autorizacion):
    respuesta = client.get("/api/tareas", headers=autorizacion)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == []
