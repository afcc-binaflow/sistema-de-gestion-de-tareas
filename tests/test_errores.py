"""Tests del manejo global de errores (Fase 7.5, adelantada a la Fase 5).

Flask responde **HTML** por defecto en 404, 405 y 500. Eso rompe el contrato de
la API —una sola forma de error, siempre JSON— y, en modo debug, expone el
depurador interactivo de Werkzeug, que permite ejecutar codigo en el servidor
(TP-16, TP-22).

El 500 no se puede provocar con una entrada: se fuerza con `monkeypatch`. Lo que
se verifica no es solo el status, sino que el cuerpo **no** filtre el detalle
interno y que la excepcion **si** quede registrada en el log. Un error silencioso
es tan malo como uno que filtra.
"""

import logging

import routes


# ---------------------------------------------------------------------------
# TC-ERR (TP-22): 404 de una URL desconocida
# ---------------------------------------------------------------------------
def test_ruta_inexistente_devuelve_404_json(client):
    respuesta = client.get("/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "Recurso no encontrado"}


# ---------------------------------------------------------------------------
# TC-ERR (TP-22): 405 de un metodo no permitido
# ---------------------------------------------------------------------------
def test_metodo_no_permitido_devuelve_405_json(client):
    respuesta = client.post("/tareas")

    assert respuesta.status_code == 405
    assert respuesta.get_json() == {"error": "Método no permitido"}


def test_metodo_no_permitido_informa_los_metodos_validos(client):
    """RFC 7231 §6.5.5: un 405 lleva `Allow`, y sin el el cliente no sabe que hacer."""
    respuesta = client.get("/login")

    assert respuesta.status_code == 405
    assert "Allow" in respuesta.headers
    assert "POST" in respuesta.headers["Allow"]


# ---------------------------------------------------------------------------
# TC-ERR-01 (TP-16): 500 en JSON, sin traceback y logueado
# ---------------------------------------------------------------------------
def test_error_no_controlado_devuelve_500_json_sin_traceback(client, monkeypatch, caplog):
    def explotar(*args, **kwargs):
        raise RuntimeError("falla interna del dao")

    monkeypatch.setattr(routes, "render_template", explotar)

    with caplog.at_level(logging.ERROR):
        respuesta = client.get("/tareas")

    assert respuesta.status_code == 500
    assert respuesta.get_json() == {"error": "Error interno del servidor"}

    cuerpo = respuesta.get_data(as_text=True)
    assert "falla interna del dao" not in cuerpo
    assert "Traceback" not in cuerpo
    assert "routes.py" not in cuerpo
    assert "instance" not in cuerpo

    # El detalle no se pierde: queda en el log del servidor.
    assert "falla interna del dao" in caplog.text
