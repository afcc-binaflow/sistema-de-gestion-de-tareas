"""Tests del CRUD de tareas (Fase 7.3, TC-CRU / TC-AUT, TP-11/12/13).

El test mas importante de este archivo no es el ciclo feliz: es el **IDOR**. Un
test que crea una tarea, la lista y la ve, pasa aunque el aislamiento por dueno no
exista. La autorizacion se prueba intentando exactamente lo que no se debe poder
hacer: que A lea, edite o borre la tarea de B. Por eso esos casos afirman **404**
(D-07: un 403 confirmaria que la tarea existe) y ademas comprueban que el dato
siguio intacto: un 404 con el borrado hecho a escondidas seria peor que un 200.

El limite de 200 caracteres (D-19) se prueba en los dos bordes: 200 entra, 201 no.
"""

import pytest

import repository
import security
from db import obtener_conexion

MENSAJE_TITULO = "El campo 'titulo' es obligatorio y debe ser un texto no vacío"


def _error(respuesta):
    """Afirma la forma unica de error del contrato y devuelve el mensaje."""
    assert respuesta.mimetype == "application/json"
    cuerpo = respuesta.get_json()
    assert isinstance(cuerpo, dict)
    assert set(cuerpo) == {"error"}
    return cuerpo["error"]


def _token_de(app, cliente, usuario):
    """Registra `usuario` por el camino real y devuelve (id, header listo)."""
    respuesta = cliente.post(
        "/registro", json={"usuario": usuario, "contraseña": "1234"}
    )
    assert respuesta.status_code == 201

    with app.app_context():
        fila = repository.buscar_usuario_por_nombre(obtener_conexion(), usuario)
    token = security.crear_token(fila["id"], clave=app.config["SECRET_KEY"])
    return fila["id"], {"Authorization": f"Bearer {token}"}


@pytest.fixture
def otro_usuario(app, client):
    """Un segundo usuario con su propio header: es el que intenta el IDOR."""
    return _token_de(app, client, "ana")


def _crear(client, autorizacion, titulo="Estudiar SQLite", **extra):
    return client.post(
        "/api/tareas", json={"titulo": titulo, **extra}, headers=autorizacion
    )


# ---------------------------------------------------------------------------
# TP-13: crear
# ---------------------------------------------------------------------------
def test_crear_tarea_devuelve_201_con_el_recurso(client, autorizacion):
    respuesta = _crear(client, autorizacion)

    assert respuesta.status_code == 201
    assert respuesta.get_json() == {
        "id": 1,
        "titulo": "Estudiar SQLite",
        "completada": False,
    }


def test_crear_tarea_con_completada_true_la_persiste(client, autorizacion):
    respuesta = _crear(client, autorizacion, completada=True)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["completada"] is True

    listado = client.get("/api/tareas", headers=autorizacion).get_json()
    assert listado[0]["completada"] is True


def test_crear_tarea_recorta_el_titulo(client, autorizacion):
    respuesta = _crear(client, autorizacion, titulo="  Estudiar SQLite  ")

    assert respuesta.status_code == 201
    assert respuesta.get_json()["titulo"] == "Estudiar SQLite"


# ---------------------------------------------------------------------------
# TP-12: validacion del titulo (particiones y valores limite)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"titulo": ""},
        {"titulo": "   "},
        {"titulo": 123},
        {"titulo": None},
        {"titulo": ["a"]},
        {"titulo": "x" * 201},
    ],
    ids=[
        "sin-titulo",
        "vacio",
        "solo-espacios",
        "numerico",
        "nulo",
        "lista",
        "201-caracteres",
    ],
)
def test_crear_tarea_invalida_devuelve_400(client, autorizacion, cuerpo):
    respuesta = client.post("/api/tareas", json=cuerpo, headers=autorizacion)

    assert respuesta.status_code == 400
    _error(respuesta)


def test_crear_tarea_con_200_caracteres_entra(client, autorizacion):
    """D-19: 200 es el limite, y el limite entra."""
    titulo = "x" * 200

    respuesta = _crear(client, autorizacion, titulo=titulo)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["titulo"] == titulo


def test_crear_tarea_con_completada_no_booleana_devuelve_400(client, autorizacion):
    respuesta = _crear(client, autorizacion, completada="si")

    assert respuesta.status_code == 400
    _error(respuesta)


def test_crear_tarea_con_cuerpo_que_no_es_objeto_devuelve_400(client, autorizacion):
    respuesta = client.post("/api/tareas", json=["Estudiar"], headers=autorizacion)

    assert respuesta.status_code == 400
    _error(respuesta)


def test_crear_tarea_con_json_malformado_devuelve_400(client, autorizacion):
    respuesta = client.post(
        "/api/tareas",
        data='{"titulo": ',
        content_type="application/json",
        headers=autorizacion,
    )

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TP-11 / RF-10: el dueno sale del token, NUNCA del cuerpo
# ---------------------------------------------------------------------------
def test_crear_tarea_ignora_el_usuario_id_del_cuerpo(client, autorizacion, otro_usuario):
    otro_id, _ = otro_usuario

    respuesta = client.post(
        "/api/tareas",
        json={"titulo": "de juan", "usuario_id": otro_id},
        headers=autorizacion,
    )

    assert respuesta.status_code == 201
    # Juan sigue viendo lo suyo aunque el cuerpo pidiera lo contrario.
    listado = client.get("/api/tareas", headers=autorizacion).get_json()
    assert [tarea["titulo"] for tarea in listado] == ["de juan"]


def test_la_respuesta_no_expone_el_dueno(client, autorizacion):
    respuesta = _crear(client, autorizacion)

    assert "usuario_id" not in respuesta.get_data(as_text=True)


# ---------------------------------------------------------------------------
# TP-13 / RF-11: listar solo lo propio
# ---------------------------------------------------------------------------
def test_listar_sin_tareas_devuelve_lista_vacia_y_200(client, autorizacion):
    respuesta = client.get("/api/tareas", headers=autorizacion)

    assert respuesta.status_code == 200
    assert respuesta.get_json() == []


def test_listar_devuelve_las_tareas_en_orden_de_id(client, autorizacion):
    _crear(client, autorizacion, titulo="primera")
    _crear(client, autorizacion, titulo="segunda")

    listado = client.get("/api/tareas", headers=autorizacion).get_json()

    assert [tarea["titulo"] for tarea in listado] == ["primera", "segunda"]


def test_listar_no_devuelve_las_tareas_de_otro(client, autorizacion, otro_usuario):
    """TP-11: el aislamiento del listado, que es donde se filtra en silencio."""
    _, autorizacion_ajena = otro_usuario

    _crear(client, autorizacion, titulo="de juan")
    _crear(client, autorizacion_ajena, titulo="de ana")

    listado_juan = client.get("/api/tareas", headers=autorizacion).get_json()
    listado_ana = client.get("/api/tareas", headers=autorizacion_ajena).get_json()

    assert [tarea["titulo"] for tarea in listado_juan] == ["de juan"]
    assert [tarea["titulo"] for tarea in listado_ana] == ["de ana"]


# ---------------------------------------------------------------------------
# TP-13 / D-07: obtener por id
# ---------------------------------------------------------------------------
def test_obtener_la_propia_devuelve_200(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    respuesta = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["id"] == tarea_id


def test_obtener_inexistente_devuelve_404(client, autorizacion):
    respuesta = client.get("/api/tareas/999", headers=autorizacion)

    assert respuesta.status_code == 404
    _error(respuesta)


def test_obtener_un_id_no_numerico_devuelve_404(client, autorizacion):
    respuesta = client.get("/api/tareas/abc", headers=autorizacion)

    assert respuesta.status_code == 404
    _error(respuesta)


# ---------------------------------------------------------------------------
# TP-11 — IDOR en GET: la tarea de B no existe para A
# ---------------------------------------------------------------------------
def test_obtener_la_tarea_de_otro_devuelve_404(client, autorizacion, otro_usuario):
    _, autorizacion_ajena = otro_usuario
    tarea_id = _crear(client, autorizacion_ajena, titulo="de ana").get_json()["id"]

    respuesta = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.status_code == 404
    assert _error(respuesta) == "Recurso no encontrado"


# ---------------------------------------------------------------------------
# TP-13: editar
# ---------------------------------------------------------------------------
def test_editar_la_propia_devuelve_200_con_el_recurso_completo(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    respuesta = client.put(
        f"/api/tareas/{tarea_id}",
        json={"titulo": "Estudiar SQLite a fondo", "completada": True},
        headers=autorizacion,
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "id": tarea_id,
        "titulo": "Estudiar SQLite a fondo",
        "completada": True,
    }


def test_editar_persiste_el_cambio(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]
    client.put(
        f"/api/tareas/{tarea_id}",
        json={"titulo": "otro titulo", "completada": True},
        headers=autorizacion,
    )

    respuesta = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.get_json()["titulo"] == "otro titulo"
    assert respuesta.get_json()["completada"] is True


def test_editar_inexistente_devuelve_404(client, autorizacion):
    respuesta = client.put(
        "/api/tareas/999", json={"titulo": "x", "completada": False}, headers=autorizacion
    )

    assert respuesta.status_code == 404
    _error(respuesta)


def test_editar_con_titulo_invalido_devuelve_400(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    respuesta = client.put(
        f"/api/tareas/{tarea_id}", json={"titulo": "   "}, headers=autorizacion
    )

    assert respuesta.status_code == 400
    _error(respuesta)


# ---------------------------------------------------------------------------
# TP-11 — IDOR en PUT
# ---------------------------------------------------------------------------
def test_editar_la_tarea_de_otro_devuelve_404(client, autorizacion, otro_usuario):
    _, autorizacion_ajena = otro_usuario
    tarea_id = _crear(client, autorizacion_ajena, titulo="de ana").get_json()["id"]

    respuesta = client.put(
        f"/api/tareas/{tarea_id}",
        json={"titulo": "secuestrada", "completada": True},
        headers=autorizacion,
    )

    assert respuesta.status_code == 404
    _error(respuesta)


def test_editar_la_tarea_de_otro_no_la_modifica(client, autorizacion, otro_usuario):
    """El 404 tiene que ser real: un UPDATE a escondidas seria peor que un 403."""
    _, autorizacion_ajena = otro_usuario
    tarea_id = _crear(client, autorizacion_ajena, titulo="de ana").get_json()["id"]

    client.put(
        f"/api/tareas/{tarea_id}",
        json={"titulo": "secuestrada", "completada": True},
        headers=autorizacion,
    )

    de_ana = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion_ajena).get_json()
    assert de_ana["titulo"] == "de ana"
    assert de_ana["completada"] is False


# ---------------------------------------------------------------------------
# D-23: borrar devuelve 204 y sin cuerpo
# ---------------------------------------------------------------------------
def test_borrar_la_propia_devuelve_204_sin_cuerpo(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    respuesta = client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.status_code == 204
    assert respuesta.get_data() == b""
    assert "Content-Type" not in respuesta.headers


def test_borrar_deja_de_existir(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion)
    respuesta = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.status_code == 404


def test_borrar_la_misma_dos_veces_devuelve_404_la_segunda(client, autorizacion):
    tarea_id = _crear(client, autorizacion).get_json()["id"]

    assert client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion).status_code == 204
    assert client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion).status_code == 404


def test_borrar_inexistente_devuelve_404(client, autorizacion):
    respuesta = client.delete("/api/tareas/999", headers=autorizacion)

    assert respuesta.status_code == 404
    _error(respuesta)


# ---------------------------------------------------------------------------
# TP-11 — IDOR en DELETE
# ---------------------------------------------------------------------------
def test_borrar_la_tarea_de_otro_devuelve_404(client, autorizacion, otro_usuario):
    _, autorizacion_ajena = otro_usuario
    tarea_id = _crear(client, autorizacion_ajena, titulo="de ana").get_json()["id"]

    respuesta = client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion)

    assert respuesta.status_code == 404
    _error(respuesta)


def test_borrar_la_tarea_de_otro_no_la_borra(client, autorizacion, otro_usuario):
    _, autorizacion_ajena = otro_usuario
    tarea_id = _crear(client, autorizacion_ajena, titulo="de ana").get_json()["id"]

    client.delete(f"/api/tareas/{tarea_id}", headers=autorizacion)

    respuesta = client.get(f"/api/tareas/{tarea_id}", headers=autorizacion_ajena)
    assert respuesta.status_code == 200
    assert respuesta.get_json()["titulo"] == "de ana"


# ---------------------------------------------------------------------------
# TP-01: el contrato de metodo
# ---------------------------------------------------------------------------
def test_delete_a_la_coleccion_devuelve_405(client, autorizacion):
    respuesta = client.delete("/api/tareas", headers=autorizacion)

    assert respuesta.status_code == 405
    _error(respuesta)


def test_post_a_un_id_devuelve_405(client, autorizacion):
    respuesta = client.post("/api/tareas/1", json={"titulo": "x"}, headers=autorizacion)

    assert respuesta.status_code == 405
    _error(respuesta)


def test_patch_a_un_id_devuelve_405(client, autorizacion):
    """TC-TAR-18: PATCH no es un metodo del contrato, aunque el recurso exista."""
    respuesta = client.patch("/api/tareas/1", json={"completada": True}, headers=autorizacion)

    assert respuesta.status_code == 405
    _error(respuesta)


# ---------------------------------------------------------------------------
# El id que SQLite no puede guardar
# ---------------------------------------------------------------------------
ID_FUERA_DE_RANGO = 2**63  # uno mas que el maximo de un INTEGER de SQLite


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
def test_id_fuera_del_rango_de_sqlite_devuelve_404(client, autorizacion, metodo):
    """`<int:>` acepta enteros de cualquier tamano; SQLite solo guarda 64 bits.

    Sin cota en el converter, el id llega al driver, que revienta con
    `OverflowError`, y el manejador de `Exception` lo convierte en un 500 por una
    entrada que el cliente controla. El contrato (§4.6) pide 404: el recurso no
    existe, y "no existe" incluye "no existe un id asi".
    """
    cuerpo = {"json": {"titulo": "x", "completada": False}} if metodo == "put" else {}
    respuesta = getattr(client, metodo)(
        f"/api/tareas/{ID_FUERA_DE_RANGO}", headers=autorizacion, **cuerpo
    )

    assert respuesta.status_code == 404
    assert _error(respuesta) == "Recurso no encontrado"


# ---------------------------------------------------------------------------
# TP-14: el titulo es un valor, no SQL
# ---------------------------------------------------------------------------
def test_el_titulo_con_sql_se_guarda_como_texto(client, autorizacion):
    inyeccion = "'; DROP TABLE tareas; --"

    respuesta = _crear(client, autorizacion, titulo=inyeccion)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["titulo"] == inyeccion

    listado = client.get("/api/tareas", headers=autorizacion).get_json()
    assert len(listado) == 1
