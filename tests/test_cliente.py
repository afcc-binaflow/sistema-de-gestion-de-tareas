"""Tests del cliente de consola (Fase 8, TC-E2E-01..04, TC-CLI-01, TP-17/TP-23).

Como se testea un cliente de consola
------------------------------------
La logica que importa (armar el request, mandar el token, traducir el error) no
vive en el menu: vive en `ApiDeTareas`. Por eso el cliente recibe la sesion HTTP
por parametro y estos tests le pasan `SesionDePrueba`, un adaptador sobre el
`test_client` de Flask. Se ejercita el cliente de verdad contra la app de verdad,
sin abrir un puerto.

Esa inyeccion no es un lujo de testing: es la segunda implementacion que pide la
regla YAGNI <-> SOLID de AGENTS.md. En produccion el default es
`requests.Session()`; en tests, el `test_client`.

Lo que se prueba y lo que no
----------------------------
- Se prueba el transporte completo (URL, header, timeout, errores) y el menu con
  un lector inyectado, que es lo unico que puede demostrar el codigo de salida de
  TC-E2E-02/03 y la ausencia de traceback.
- No se prueba el efecto en la consola real (colores, UTF-8 del terminal de
  Windows): eso queda como evidencia manual, porque depende de la terminal.
"""

import io
import json
import time

import pytest
import requests

import cliente
import security

URL_BASE = "http://api.test"

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"


class RespuestaAdaptada:
    """Una respuesta de Flask con la forma que el cliente espera de `requests`.

    `requests.Response.json()` es un metodo; `flask.Response.json` es una
    propiedad. El adaptador normaliza eso y nada mas: el cuerpo lo sigue
    parseando el JSON de verdad, asi que un 204 o un HTML siguen fallando igual
    que en produccion.
    """

    def __init__(self, respuesta):
        self.status_code = respuesta.status_code
        self._respuesta = respuesta

    def json(self):
        return json.loads(self._respuesta.get_data())


class SesionDePrueba:
    """Adapta el `test_client` de Flask al protocolo minimo que usa el cliente.

    Registra lo que el cliente *mando* (metodo, ruta, cuerpo, timeout) y lo que
    *recibio* (status), que es lo que permiten afirmar TC-E2E-04 sin leer el
    codigo de `cliente.py`: si el cliente cambia `token` por `access_token`, el
    test lo ve en el cuerpo registrado.
    """

    def __init__(self, client, url_base=URL_BASE):
        self._client = client
        self._url_base = url_base
        self.envios = []
        self.estados = []

    def post(self, url, json=None, headers=None, timeout=None):
        return self._enviar("post", url, json, headers, timeout)

    def get(self, url, json=None, headers=None, timeout=None):
        return self._enviar("get", url, json, headers, timeout)

    def put(self, url, json=None, headers=None, timeout=None):
        return self._enviar("put", url, json, headers, timeout)

    def delete(self, url, json=None, headers=None, timeout=None):
        return self._enviar("delete", url, json, headers, timeout)

    def _enviar(self, metodo, url, cuerpo, cabeceras, tiempo):
        assert url.startswith(self._url_base), f"URL fuera de la base: {url}"
        self.envios.append(
            {
                "metodo": metodo,
                "ruta": url[len(self._url_base) :],
                "cuerpo": cuerpo,
                "cabeceras": cabeceras,
                "timeout": tiempo,
            }
        )
        respuesta = getattr(self._client, metodo)(
            url[len(self._url_base) :], json=cuerpo, headers=cabeceras
        )
        self.estados.append(respuesta.status_code)
        return RespuestaAdaptada(respuesta)


class SesionCaida:
    """La API no existe: es el escenario de TC-E2E-02, sin abrir un puerto."""

    def post(self, url, **kwargs):
        raise requests.exceptions.ConnectionError("Connection refused")

    get = post
    put = post
    delete = post


class RespuestaQueNoEsJson:
    """Un 502 de un proxy: status de error y cuerpo HTML."""

    status_code = 502

    def json(self):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


class RespuestaJsonSinCampoError:
    """Un JSON valido que no sigue el contrato: no trae `error`."""

    status_code = 500

    def json(self):
        return {"mensaje": "boom"}


class SesionQueDevuelve:
    """Siempre la misma respuesta de error, para fijar como se traduce."""

    def __init__(self, respuesta):
        self._respuesta = respuesta

    def post(self, url, **kwargs):
        return self._respuesta

    get = post
    put = post
    delete = post


class FlujoFalso:
    """Un stdout de mentira: solo registra como se lo reconfiguro."""

    def __init__(self):
        self.encoding = None

    def reconfigure(self, encoding=None):
        self.encoding = encoding

    def write(self, texto):
        pass

    def flush(self):
        pass


def _con_sesion_de_prueba(client):
    """Devuelve (api, sesion) para poder afirmar sobre lo enviado y lo recibido."""
    sesion = SesionDePrueba(client)
    return cliente.ApiDeTareas(URL_BASE, sesion=sesion), sesion


def _menu(api, lineas):
    """Corre el menu con una entrada guionada y devuelve (codigo, salida)."""
    salida = io.StringIO()
    entrada = iter(lineas)
    codigo = cliente.menu(
        api,
        leer=lambda _mensaje: next(entrada),
        escribir=salida.write,
    )
    return codigo, salida.getvalue()


# ---------------------------------------------------------------------------
# TC-E2E-01: el ciclo completo, por las funciones de transporte del cliente
# ---------------------------------------------------------------------------
def test_ciclo_completo_de_registro_login_crud_por_el_cliente(client):
    api, sesion = _con_sesion_de_prueba(client)

    api.registrar("juan", "contraseña")
    api.iniciar_sesion("juan", "contraseña")

    creada = api.crear_tarea("Estudiar SQLite")
    assert creada == {"id": 1, "titulo": "Estudiar SQLite", "completada": False}
    assert api.listar_tareas() == [creada]

    actualizada = api.actualizar_tarea(1, "Estudiar SQLite a fondo", True)
    assert actualizada == {
        "id": 1,
        "titulo": "Estudiar SQLite a fondo",
        "completada": True,
    }
    assert api.listar_tareas() == [actualizada]

    assert api.borrar_tarea(1) is None
    assert api.listar_tareas() == []

    # TC-E2E-04: los status que el cliente asume son los del contrato.
    assert sesion.estados == [201, 200, 201, 200, 200, 200, 204, 200]


# ---------------------------------------------------------------------------
# TC-E2E-04: nombres de campo del contrato, no los que a uno le gustarian
# ---------------------------------------------------------------------------
def test_el_cliente_manda_los_nombres_de_campo_del_contrato(client):
    api, sesion = _con_sesion_de_prueba(client)

    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")
    api.crear_tarea("Estudiar SQLite")
    api.actualizar_tarea(1, "Estudiar SQLite", True)

    assert sesion.envios[0]["cuerpo"] == {"usuario": "juan", "contraseña": "1234"}
    assert sesion.envios[1]["cuerpo"] == {"usuario": "juan", "contraseña": "1234"}
    assert sesion.envios[2]["cuerpo"] == {"titulo": "Estudiar SQLite"}
    # PUT reemplaza el recurso completo (D-17): si el cliente mandara solo el
    # titulo, la tarea volveria a `completada: false` sin que nadie lo pidiera.
    assert sesion.envios[3]["cuerpo"] == {
        "titulo": "Estudiar SQLite",
        "completada": True,
    }


def test_el_login_lee_el_token_y_lo_usa_como_bearer(client):
    api, sesion = _con_sesion_de_prueba(client)

    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")
    api.listar_tareas()

    token = api.token
    assert token
    assert sesion.envios[2]["cabeceras"] == {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# `timeout` explicito: sin el, el cliente se cuelga para siempre
# ---------------------------------------------------------------------------
def test_todas_las_llamadas_llevan_timeout_explicito(client):
    api, sesion = _con_sesion_de_prueba(client)

    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")
    api.listar_tareas()
    api.crear_tarea("Estudiar SQLite")
    api.actualizar_tarea(1, "Estudiar SQLite", True)
    api.borrar_tarea(1)

    assert len(sesion.envios) == 6
    for envio in sesion.envios:
        assert envio["timeout"] == cliente.TIEMPO_ESPERA
        assert envio["timeout"] > 0


# ---------------------------------------------------------------------------
# TC-E2E-02: API caida
# ---------------------------------------------------------------------------
def test_api_caida_se_traduce_en_un_error_de_red():
    api = cliente.ApiDeTareas(URL_BASE, sesion=SesionCaida())

    with pytest.raises(cliente.ErrorDeRed) as capturado:
        api.registrar("juan", "1234")

    linea = cliente.formatear_error(capturado.value)
    assert "\n" not in linea
    assert "No se pudo conectar" in linea
    assert "Connection refused" in linea


def test_api_caida_imprime_una_linea_y_sale_con_codigo_distinto_de_cero():
    api = cliente.ApiDeTareas(URL_BASE, sesion=SesionCaida())

    # Opcion 2 = iniciar sesion. Despues la entrada se termina: el cliente tiene
    # que salir solo, no explotar con StopIteration.
    codigo, salida = _menu(api, ["2", "juan", "1234"])

    assert codigo == 1
    assert salida.count("No se pudo conectar") == 1
    assert "Traceback" not in salida


# ---------------------------------------------------------------------------
# Un error con cuerpo HTML: el cliente no revienta con un JSONDecodeError
# ---------------------------------------------------------------------------
def test_un_error_sin_cuerpo_json_da_un_mensaje_honesto():
    """`_mensaje_de_error` cubre el 502/504 HTML de un proxy por delante.

    Sin este caso, el camino que traduce un cuerpo no parseable queda sin
    ejecutar y la primera vez que corra sera en produccion, con un traceback en
    la cara del usuario.
    """
    api = cliente.ApiDeTareas(
        URL_BASE, sesion=SesionQueDevuelve(RespuestaQueNoEsJson())
    )

    with pytest.raises(cliente.ErrorDeApi) as capturado:
        api.registrar("juan", "1234")

    assert capturado.value.codigo == 502
    assert capturado.value.mensaje == "la respuesta no es JSON"
    assert "\n" not in cliente.formatear_error(capturado.value)


def test_un_json_sin_campo_error_no_se_inventa_un_mensaje():
    """Un JSON valido con otra forma tampoco es un `error` del contrato.

    El cliente no adivina: si no hay `error` string, lo dice. Inventar un texto
    a partir de otra clave mostraria algo que la API nunca quiso decir.
    """
    api = cliente.ApiDeTareas(
        URL_BASE, sesion=SesionQueDevuelve(RespuestaJsonSinCampoError())
    )

    with pytest.raises(cliente.ErrorDeApi) as capturado:
        api.registrar("juan", "1234")

    assert capturado.value.codigo == 500
    assert capturado.value.mensaje == "la respuesta no trae el campo 'error'"
    assert "\n" not in cliente.formatear_error(capturado.value)


# ---------------------------------------------------------------------------
# TC-E2E-03: la API responde 400 y 401
# ---------------------------------------------------------------------------
def test_400_y_401_dan_una_linea_con_el_status_y_el_error_de_la_api(client):
    api, _ = _con_sesion_de_prueba(client)
    api.registrar("juan", "1234")

    with pytest.raises(cliente.ErrorDeApi) as cuatrocientos:
        api.registrar("", "1234")
    assert cuatrocientos.value.codigo == 400
    assert cliente.formatear_error(cuatrocientos.value) == (
        "Error 400: El campo 'usuario' es obligatorio y debe ser un texto no vacío"
    )

    with pytest.raises(cliente.ErrorDeApi) as cuatrocientos_uno:
        api.iniciar_sesion("juan", "mala")
    assert cuatrocientos_uno.value.codigo == 401
    assert cuatrocientos_uno.value.mensaje == MENSAJE_CREDENCIALES


def test_un_401_en_el_menu_imprime_el_status_y_el_error(client):
    api, _ = _con_sesion_de_prueba(client)
    api.registrar("juan", "1234")

    codigo, salida = _menu(api, ["2", "juan", "mala"])

    assert codigo == 1
    assert "401" in salida
    assert MENSAJE_CREDENCIALES in salida
    assert "Traceback" not in salida


# ---------------------------------------------------------------------------
# Token vencido: el cliente no adivina, borra el token muerto y avisa
# ---------------------------------------------------------------------------
def test_401_con_token_vencido_borra_el_token_local_y_pide_reingresar(
    client, app, usuario_registrado
):
    api, _ = _con_sesion_de_prueba(client)
    # La unica forma de tener un token vencido sin esperar 8 horas es forjarlo,
    # y se forja con la misma clave con la que la app valida.
    api.token = security.crear_token(
        usuario_registrado["id"],
        clave=app.config["SECRET_KEY"],
        exp=int(time.time()) - 60,
    )

    with pytest.raises(cliente.ErrorDeApi) as capturado:
        api.listar_tareas()

    assert capturado.value.codigo == 401
    assert api.token is None
    linea = cliente.formatear_error(capturado.value)
    assert "iniciar sesión" in linea


# ---------------------------------------------------------------------------
# Un login fallido no cierra la sesion que ya estaba abierta
# ---------------------------------------------------------------------------
def test_un_login_fallido_no_borra_el_token_de_la_sesion_vigente(client, usuario_registrado):
    api, _ = _con_sesion_de_prueba(client)
    api.iniciar_sesion("juan", "1234")
    token = api.token

    with pytest.raises(cliente.ErrorDeApi) as capturado:
        api.iniciar_sesion("juan", "mala")

    assert capturado.value.codigo == 401
    assert api.token == token
    # El 401 de un login es de las credenciales, no del token: pedir "volve a
    # iniciar sesion" a alguien que justamente estaba intentando entrar no
    # informa nada.
    assert "iniciar sesión" not in cliente.formatear_error(capturado.value)
    assert api.listar_tareas() == []


# ---------------------------------------------------------------------------
# TC-CLI-01: cerrar sesion es local, el token sigue vivo (D-17)
# ---------------------------------------------------------------------------
def test_cerrar_sesion_no_revoca_el_token_en_el_servidor(client):
    api, _ = _con_sesion_de_prueba(client)
    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")
    token = api.token

    api.cerrar_sesion()
    assert api.token is None

    # El caso existe para fijar la limitacion, no para celebrarla: no hay
    # blacklist en el servidor, asi que el token sigue siendo valido hasta que
    # venza (D-17). El README tiene que decirlo.
    respuesta = client.get(
        "/api/tareas", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 200


# ---------------------------------------------------------------------------
# UTF-8 (RNF-10, TP-23)
# ---------------------------------------------------------------------------
def test_la_contrasena_con_enie_sobrevive_el_viaje_de_ida_y_vuelta(client):
    api, _ = _con_sesion_de_prueba(client)

    api.registrar("juan", "contraseña")
    api.iniciar_sesion("juan", "contraseña")

    assert api.token


def test_principal_fuerza_utf8_en_la_salida(monkeypatch):
    flujo = FlujoFalso()
    monkeypatch.setattr(cliente.sys, "stdout", flujo)

    cliente._configurar_utf8()

    assert flujo.encoding == "utf-8"


def test_principal_usa_la_url_del_entorno(monkeypatch):
    """`PFO2_API_URL` se lee al arrancar y el default solo aplica si falta.

    `principal` es la funcion que corre `python cliente.py`: el argumento del
    menu es una `ApiDeTareas` ya armada con esa URL. Se intercepta `menu` para no
    tocar stdin ni la red.
    """
    vistas = []

    def menu_falso(api):
        vistas.append(api.url_base)
        return 0

    monkeypatch.setattr(cliente, "menu", menu_falso)
    monkeypatch.setattr(cliente.sys, "stdout", FlujoFalso())
    monkeypatch.setenv("PFO2_API_URL", "http://otra-api.test")

    assert cliente.principal() == 0
    assert vistas == ["http://otra-api.test"]


# ---------------------------------------------------------------------------
# El menu: que las opciones hagan lo que dicen
# ---------------------------------------------------------------------------
def test_el_menu_recorre_el_ciclo_completo_y_sale_con_cero(client):
    api, _ = _con_sesion_de_prueba(client)

    codigo, salida = _menu(
        api,
        [
            "1", "juan", "contraseña",   # registrarse
            "2", "juan", "contraseña",   # iniciar sesion
            "4", "Estudiar SQLite",      # crear
            "3",                        # listar
            "5", "1", "Estudiar SQLite", "s",  # editar
            "3",                        # listar de nuevo
            "5", "1", "Estudiar SQLite", "n",  # desmarcar
            "3",                        # listar de nuevo
            "6", "1",                   # borrar
            "3",                        # listar vacio
            "7",                        # salir
        ],
    )

    assert codigo == 0
    assert "Estudiar SQLite" in salida
    assert "[x] Estudiar SQLite" in salida
    assert "[ ] Estudiar SQLite" in salida
    assert "No tenés tareas" in salida
    assert "Traceback" not in salida


def test_una_operacion_de_tareas_sin_sesion_avisa_y_no_llama_a_la_api(client):
    api, sesion = _con_sesion_de_prueba(client)

    codigo, salida = _menu(api, ["3", "7"])

    assert codigo == 0
    assert "iniciá sesión" in salida
    assert sesion.envios == []


def test_crear_editar_y_borrar_sin_sesion_tampoco_llaman_a_la_api(client):
    """Las tres acciones que escriben tienen el mismo guard que listar.

    Es el mismo `_hay_sesion`, pero cada accion lo invoca por su cuenta: si una
    se lo olvidara, el usuario veria "primero iniciá sesión" y la llamada saldria
    igual, con un 401 encima.
    """
    api, sesion = _con_sesion_de_prueba(client)

    codigo, salida = _menu(api, ["4", "5", "6", "7"])

    assert codigo == 0
    assert salida.count("Primero iniciá sesión") == 3
    assert sesion.envios == []


def test_un_id_que_no_es_numero_avisa_sin_traceback(client):
    api, _ = _con_sesion_de_prueba(client)
    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")

    codigo, salida = _menu(api, ["6", "abc", "7"])

    assert codigo == 1
    assert "número" in salida
    assert "Traceback" not in salida


def test_una_opcion_fuera_del_menu_no_termina_la_sesion(client):
    api, _ = _con_sesion_de_prueba(client)

    codigo, salida = _menu(api, ["99", "7"])

    assert codigo == 0
    assert "Opción inválida" in salida


def test_una_completada_que_no_es_s_ni_n_avisa_sin_traceback(client):
    api, _ = _con_sesion_de_prueba(client)
    api.registrar("juan", "1234")
    api.iniciar_sesion("juan", "1234")
    api.crear_tarea("Estudiar SQLite")

    codigo, salida = _menu(api, ["5", "1", "Estudiar SQLite", "tal vez", "7"])

    assert codigo == 1
    assert "s o n" in salida
    assert "Traceback" not in salida
