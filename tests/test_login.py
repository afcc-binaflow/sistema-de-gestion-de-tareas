"""Tests del endpoint POST /login (Fase 6, TC-LOG-01..09).

El caso central no es el login feliz: es TP-07. Distinguir "ese usuario no
existe" de "la contraseña esta mal" le entrega a un atacante un buscador de
usuarios validos (user enumeration). Por eso TC-LOG-04 compara el cuerpo **byte
a byte**: un test que solo afirma `401 == 401` pasa aunque los mensajes digan
cosas distintas, y no protege de nada.

El login emite el token, asi que estas pruebas tambien fijan lo que la Fase 7 va
a consumir: `sub`, `exp` y que el payload no lleve credenciales.

**Lo que estos tests NO cubren, a proposito (D-29).** TP-07 se cumple en lo que
el contrato fija —status, cuerpo y `Content-Type` identicos— pero el *tiempo*
sigue delatando la causa: con el usuario inexistente no se ejecuta
`verificar_password`, asi que la respuesta llega en milisegundos contra cientos
de una password incorrecta. Se midio (336 ms vs 1,1 ms, 296x, sin solapamiento)
y se acepto como riesgo residual. Ningun test de aca puede fingir que ese canal
no existe: lo que se prueba es el contrato, y el contrato no habla de tiempos.
"""

import security
from db import obtener_conexion
from repository import buscar_usuario_por_nombre

CREDENCIALES = {"usuario": "juan", "contraseña": "1234"}
MENSAJE_401 = "Usuario o contraseña incorrectos"


def _error(respuesta):
    """Afirma la forma unica de error del contrato y devuelve el mensaje."""
    assert respuesta.mimetype == "application/json"
    cuerpo = respuesta.get_json()
    assert isinstance(cuerpo, dict)
    assert set(cuerpo) == {"error"}
    assert cuerpo["error"]
    return cuerpo["error"]


def _registrar(client, usuario="juan", contrasena="1234"):
    respuesta = client.post(
        "/registro", json={"usuario": usuario, "contraseña": contrasena}
    )
    assert respuesta.status_code == 201
    return respuesta


# ---------------------------------------------------------------------------
# TC-LOG-01 (TP-06): camino feliz
# ---------------------------------------------------------------------------
def test_login_valido_devuelve_200_con_el_token(client):
    _registrar(client)

    respuesta = client.post("/login", json=CREDENCIALES)

    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert set(cuerpo) == {"token"}
    assert cuerpo["token"]


# ---------------------------------------------------------------------------
# TC-LOG-02 / 03 (TP-07): las dos causas del 401
# ---------------------------------------------------------------------------
def test_login_con_contrasena_incorrecta_devuelve_401(client):
    _registrar(client)

    respuesta = client.post("/login", json={"usuario": "juan", "contraseña": "otra"})

    assert respuesta.status_code == 401
    # El literal, no solo la forma: el contrato fija el mensaje y un test que
    # solo afirma `{"error": ...}` deja pasar un cambio de texto sin ruido.
    assert _error(respuesta) == MENSAJE_401


def test_login_con_usuario_inexistente_devuelve_401(client):
    respuesta = client.post("/login", json={"usuario": "nadie", "contraseña": "1234"})

    assert respuesta.status_code == 401
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-LOG-04 (TP-07): el 401 es identico en las dos causas
# ---------------------------------------------------------------------------
def test_los_dos_401_son_byte_a_byte_identicos(client):
    _registrar(client)

    contrasena_mala = client.post(
        "/login", json={"usuario": "juan", "contraseña": "otra"}
    )
    usuario_inexistente = client.post(
        "/login", json={"usuario": "nadie", "contraseña": "1234"}
    )

    assert contrasena_mala.status_code == usuario_inexistente.status_code
    assert contrasena_mala.status_code == 401
    assert contrasena_mala.get_data() == usuario_inexistente.get_data()
    assert contrasena_mala.mimetype == usuario_inexistente.mimetype
    # Comparar dos respuestas entre si pasa aunque las dos esten mal: el cuerpo
    # esperado se afirma por separado.
    assert contrasena_mala.get_json() == {"error": MENSAJE_401}


# ---------------------------------------------------------------------------
# TC-LOG-06 / 24 (TP-24): el ejemplo del enunciado sirve para entrar
# ---------------------------------------------------------------------------
def test_login_acepta_la_contrasena_1234_del_enunciado(client):
    _registrar(client, contrasena="1234")

    respuesta = client.post("/login", json={"usuario": "juan", "contraseña": "1234"})

    assert respuesta.status_code == 200


# ---------------------------------------------------------------------------
# TC-LOG-07 (TP-02, D-21): la password no se recorta al entrar
# ---------------------------------------------------------------------------
def test_login_no_recorta_la_contrasena(client):
    _registrar(client, contrasena=" 1234 ")

    con_espacios = client.post(
        "/login", json={"usuario": "juan", "contraseña": " 1234 "}
    )
    sin_espacios = client.post("/login", json={"usuario": "juan", "contraseña": "1234"})

    assert con_espacios.status_code == 200
    assert sin_espacios.status_code == 401


# ---------------------------------------------------------------------------
# TC-LOG-05 / 08 (TP-18, TP-02): cuerpo invalido
# ---------------------------------------------------------------------------
def test_login_con_json_malformado_devuelve_400(client):
    respuesta = client.post(
        "/login", data='{"usuario": ', content_type="application/json"
    )

    assert respuesta.status_code == 400
    _error(respuesta)


def test_login_sin_contrasena_devuelve_400(client):
    _registrar(client)

    respuesta = client.post("/login", json={"usuario": "juan"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_login_con_contrasena_vacia_devuelve_400(client):
    _registrar(client)

    respuesta = client.post("/login", json={"usuario": "juan", "contraseña": ""})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_login_con_usuario_vacio_devuelve_400(client):
    respuesta = client.post("/login", json={"usuario": "", "contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_login_con_usuario_no_texto_devuelve_400(client):
    respuesta = client.post("/login", json={"usuario": 123, "contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-LOG-09 (TP-01): el contrato de metodo
# ---------------------------------------------------------------------------
def test_get_login_devuelve_405(client):
    respuesta = client.get("/login")

    assert respuesta.status_code == 405
    _error(respuesta)


# ---------------------------------------------------------------------------
# RF-07 / D-20: contenido del token que la Fase 7 va a consumir
# ---------------------------------------------------------------------------
def test_el_token_lleva_el_id_del_usuario_y_no_lleva_credenciales(client, app):
    _registrar(client)

    respuesta = client.post("/login", json=CREDENCIALES)
    payload = security.decodificar_token(
        respuesta.get_json()["token"], clave=app.config["SECRET_KEY"]
    )

    with app.app_context():
        guardado = buscar_usuario_por_nombre(obtener_conexion(), "juan")

    assert payload["sub"] == str(guardado["id"])
    assert set(payload) == {"sub", "iat", "exp"}
    # Ningun valor del payload es la password ni su hash. Se compara valor por
    # valor y no sobre el diccionario serializado: un `exp` puede contener la
    # secuencia "1234" por casualidad y haria fallar el test sin motivo.
    assert "1234" not in [str(valor) for valor in payload.values()]
    assert "password_hash" not in payload
