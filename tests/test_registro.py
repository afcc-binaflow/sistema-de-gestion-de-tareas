"""Tests del endpoint POST /registro (Fase 5, TC-REG-01..16).

Se diseña con tecnicas formales, no por intuicion: particiones de equivalencia
(datos validos vs. invalidos), analisis de valores limite (usuario vacio, solo
espacios, la password `1234` del propio enunciado) y casos negativos (duplicado,
JSON malformado, Content-Type erroneo).

Todas las respuestas de error se afirman contra la regla del contrato: un solo
cuerpo posible, `{"error": "<mensaje>"}` (docs/api.md §3).
"""

import json

import repository
from db import obtener_conexion
from security import verificar_password

CREDENCIALES = {"usuario": "juan", "contraseña": "1234"}


def _error(respuesta):
    """Afirma la forma unica de error del contrato y devuelve el mensaje.

    Incluye el `Content-Type`: el contrato pide JSON en **toda** respuesta de
    error (TC-ERR-05). Un cuerpo JSON servido como `text/html` rompe al cliente
    igual que un cuerpo HTML.
    """
    assert respuesta.mimetype == "application/json"
    cuerpo = respuesta.get_json()
    assert isinstance(cuerpo, dict)
    assert set(cuerpo) == {"error"}
    assert cuerpo["error"]
    return cuerpo["error"]


def _usuario_guardado(app, usuario):
    """Lee la fila directo de la base: la inspeccion no pasa por la API."""
    with app.app_context():
        return repository.buscar_usuario_por_nombre(obtener_conexion(), usuario)


# ---------------------------------------------------------------------------
# TC-REG-01 (TP-02): camino feliz
# ---------------------------------------------------------------------------
def test_registro_valido_devuelve_201_y_el_usuario(client):
    respuesta = client.post("/registro", json=CREDENCIALES)

    assert respuesta.status_code == 201
    assert respuesta.get_json() == {"usuario": "juan"}


# ---------------------------------------------------------------------------
# TC-REG-02 / 03 (TP-02): campo faltante
# ---------------------------------------------------------------------------
def test_registro_sin_contrasena_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": "juan"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_sin_usuario_devuelve_400(client):
    respuesta = client.post("/registro", json={"contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-REG-04 / 05 (TP-02): tipo equivocado
# ---------------------------------------------------------------------------
def test_registro_con_usuario_no_texto_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": 123, "contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_con_contrasena_nula_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": "juan", "contraseña": None})

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-REG-06 / 11 / 16 (TP-02, D-14, D-21): valores limite
# ---------------------------------------------------------------------------
def test_registro_con_usuario_vacio_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": "", "contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_con_usuario_de_solo_espacios_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": "   ", "contraseña": "1234"})

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_con_contrasena_vacia_devuelve_400(client):
    respuesta = client.post("/registro", json={"usuario": "juan", "contraseña": ""})

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-REG-10 (TP-02, D-21): el usuario se normaliza, la password no
# ---------------------------------------------------------------------------
def test_registro_recorta_espacios_del_usuario(client):
    respuesta = client.post("/registro", json={"usuario": "  juan  ", "contraseña": "1234"})

    assert respuesta.status_code == 201
    assert respuesta.get_json() == {"usuario": "juan"}


def test_registro_no_recorta_la_contrasena(client, app):
    client.post("/registro", json={"usuario": "juan", "contraseña": " 1234 "})

    guardado = _usuario_guardado(app, "juan")
    assert verificar_password(guardado["password_hash"], " 1234 ")
    assert not verificar_password(guardado["password_hash"], "1234")


# ---------------------------------------------------------------------------
# TC-REG-07 / 14 (TP-18): cuerpo que no es JSON
# ---------------------------------------------------------------------------
def test_registro_con_content_type_erroneo_devuelve_400(client):
    respuesta = client.post(
        "/registro",
        data=json.dumps(CREDENCIALES),
        content_type="text/plain",
    )

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_sin_content_type_devuelve_400(client):
    respuesta = client.post("/registro", data=json.dumps(CREDENCIALES))

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_con_json_truncado_devuelve_400(client):
    respuesta = client.post(
        "/registro",
        data='{"usuario": ',
        content_type="application/json",
    )

    assert respuesta.status_code == 400
    _error(respuesta)


def test_registro_con_json_que_no_es_objeto_devuelve_400(client):
    respuesta = client.post("/registro", json=["juan", "1234"])

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-REG-08 / 24 (TP-24): el ejemplo del enunciado se acepta
# ---------------------------------------------------------------------------
def test_registro_acepta_la_contrasena_1234_del_enunciado(client):
    respuesta = client.post("/registro", json={"usuario": "juan", "contraseña": "1234"})

    assert respuesta.status_code == 201


# ---------------------------------------------------------------------------
# TC-REG-09 / 12 (TP-03, TP-19): duplicado exacto y case-insensitive
# ---------------------------------------------------------------------------
def test_registro_duplicado_devuelve_409(client):
    client.post("/registro", json=CREDENCIALES)

    respuesta = client.post("/registro", json=CREDENCIALES)

    assert respuesta.status_code == 409
    _error(respuesta)


def test_registro_duplicado_con_otra_capitalizacion_devuelve_409(client):
    client.post("/registro", json={"usuario": "Juan", "contraseña": "1234"})

    respuesta = client.post("/registro", json={"usuario": "juan", "contraseña": "otra"})

    assert respuesta.status_code == 409
    _error(respuesta)


# ---------------------------------------------------------------------------
# TC-REG-13 (TP-05, RF-04): la respuesta nunca filtra el secreto
# ---------------------------------------------------------------------------
def test_registro_no_devuelve_el_hash_ni_la_contrasena(client):
    respuesta = client.post("/registro", json=CREDENCIALES)

    assert respuesta.status_code == 201
    cuerpo = respuesta.get_data(as_text=True)
    assert "password_hash" not in cuerpo
    assert "1234" not in cuerpo
    assert "contraseña" not in cuerpo

    # El contrato dice "en ninguna clave ni header" (TC-REG-13).
    cabeceras = " ".join(f"{clave}: {valor}" for clave, valor in respuesta.headers.items())
    assert "password_hash" not in cabeceras
    assert "1234" not in cabeceras


# ---------------------------------------------------------------------------
# TP-04: la password queda hasheada en la base, no en texto plano
# ---------------------------------------------------------------------------
def test_registro_guarda_la_contrasena_hasheada(client, app):
    client.post("/registro", json=CREDENCIALES)

    guardado = _usuario_guardado(app, "juan")

    assert guardado["password_hash"] != "1234"
    assert verificar_password(guardado["password_hash"], "1234")


# ---------------------------------------------------------------------------
# TP-14: un nombre con SQL no se interpreta como SQL
# ---------------------------------------------------------------------------
def test_registro_no_interpreta_sql_del_usuario(client, app):
    inyeccion = "' OR 1=1 --"

    respuesta = client.post("/registro", json={"usuario": inyeccion, "contraseña": "1234"})

    assert respuesta.status_code == 201
    assert _usuario_guardado(app, inyeccion) is not None

    with app.app_context():
        total = obtener_conexion().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    assert total == 1


# ---------------------------------------------------------------------------
# TC-REG-15 (TP-01): el contrato de metodo
# ---------------------------------------------------------------------------
def test_get_registro_devuelve_405(client):
    respuesta = client.get("/registro")

    assert respuesta.status_code == 405
    _error(respuesta)


def test_put_registro_devuelve_405(client):
    respuesta = client.put("/registro", json=CREDENCIALES)

    assert respuesta.status_code == 405
    _error(respuesta)
