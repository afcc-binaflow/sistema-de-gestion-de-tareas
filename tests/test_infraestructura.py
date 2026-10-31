"""Verificacion de la propia infraestructura de tests (Fase 2.4).

Si esto no pasa, nada de lo que se escriba despues es creible: estariamos
midiendo una suite que no aisla ni responde. Es la primera suite del proyecto y
su unico objetivo es probar que las fixtures hacen lo que dicen.
"""

from pathlib import Path

import pytest

from config import ConfigTest
from servidor import create_app

RUTA_BASE_REAL = Path(__file__).resolve().parent.parent / "instance" / "pfo2.db"


def _huella(ruta):
    """Estado observable de un archivo: existencia, tamano y mtime."""
    if not ruta.exists():
        return None
    info = ruta.stat()
    return (info.st_size, info.st_mtime_ns)


def test_el_cliente_responde(client):
    """La fixture mas basica: hay app y hay cliente HTTP."""
    respuesta = client.get("/tareas")
    assert respuesta.status_code == 200


def test_la_base_de_los_tests_esta_en_memoria(app):
    """RNF-12: la app de cada test no apunta a un archivo."""
    assert app.config["DATABASE"] == ":memory:"
    assert app.config["TESTING"] is True


def test_la_suite_no_toca_la_base_real(client):
    """RNF-12: una peticion no puede crear ni modificar `instance/pfo2.db`.

    Hoy el alcance es una lectura, porque la unica ruta existente no escribe. La
    asercion se vuelve mas fuerte sola cuando las fases 5 a 7 agreguen escrituras
    al CRUD: cualquier test que se equivoque de configuracion hace fallar este.
    """
    antes = _huella(RUTA_BASE_REAL)
    client.get("/tareas")
    assert _huella(RUTA_BASE_REAL) == antes


def test_dos_apps_no_comparten_configuracion():
    """D-18: la fabrica permite dos apps con configuraciones distintas a la vez.

    Es la prueba de que el seam existe de verdad. Si la configuracion fuera
    estado global del modulo, la segunda app pisaria a la primera y toda la
    estrategia de testing con base en memoria dejaria de funcionar.
    """

    class ConfigTestAlternativa(ConfigTest):
        HORAS_EXPIRACION_TOKEN = 1

    una = create_app(ConfigTest)
    otra = create_app(ConfigTestAlternativa)

    assert una.config["HORAS_EXPIRACION_TOKEN"] == 8
    assert otra.config["HORAS_EXPIRACION_TOKEN"] == 1


def test_la_app_falla_sin_secret_key(monkeypatch):
    """RNF-03: sin `SECRET_KEY` la app no arranca, y lo dice.

    Se prueba el modo de produccion (`TESTING = False`). El mensaje importa: sin
    la comprobacion temprana, la falta de `SECRET_KEY` reaparece mas tarde como
    un error opaco al firmar el primer token.
    """
    monkeypatch.setattr(ConfigTest, "TESTING", False)
    monkeypatch.setattr(ConfigTest, "SECRET_KEY", None)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(ConfigTest)
