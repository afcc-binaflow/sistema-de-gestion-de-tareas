"""Fixtures base de la suite (Fase 2.4).

Esta infraestructura se adelanta al codigo de produccion a proposito. Si llega
al final del proyecto, las fases 3 a 8 se escriben sin red de seguridad, que es
exactamente el defecto que el plan anterior tenia.

Regla dura (RNF-12): los tests **nunca** tocan `instance/pfo2.db`. La app de
cada test se crea con `ConfigTest`, que apunta a una base en memoria.

Fixture de alcance deliberadamente corto
----------------------------------------
El plan de la Fase 2.4 lista cuatro fixtures: `app`, `client`,
`usuario_registrado`/`token_valido` y `db_vacia`. Las dos primeras existen desde
entonces. `usuario_registrado` y `token_valido` se agregaron en la Fase 7, que es
cuando el codigo de produccion las volvio construibles:

- `usuario_registrado` se crea **por el endpoint real** (`POST /registro`) y su id
  se lee de la base. No se inserta con SQL inventado: eso haria que la suite
  midiera la suite en vez de la aplicacion.
- `token_valido` usa `security.crear_token` (Fase 4), no un JWT escrito a mano.

`db_vacia` no se agrega: `app` ya entrega una base en memoria vacia por test, y
una fixture que no agrega nada es codigo muerto.
"""

import pytest

from config import ConfigTest
from db import obtener_conexion
from repository import buscar_usuario_por_nombre
from security import crear_token
from servidor import create_app


@pytest.fixture
def app():
    """Una app nueva por test, con base en memoria (RNF-12, D-18).

    La conexion persistente que abre `init_db` se cierra al terminar el test. Sin
    ese cierre, SQLite la reporta como `ResourceWarning` cuando el recolector la
    encuentra viva: cientos de avisos que tapan el que si importa.
    """
    aplicacion = create_app(ConfigTest)
    yield aplicacion
    aplicacion._db_conexion_persistente.close()


@pytest.fixture
def client(app):
    """Cliente HTTP de Flask para ejercitar los endpoints sin levantar un server."""
    return app.test_client()


@pytest.fixture
def usuario_registrado(client, app):
    """Registra `juan` por el camino real y devuelve `{"usuario", "id"}`."""
    respuesta = client.post("/registro", json={"usuario": "juan", "contraseña": "1234"})
    assert respuesta.status_code == 201

    with app.app_context():
        fila = buscar_usuario_por_nombre(obtener_conexion(), "juan")
    return {"usuario": "juan", "id": fila["id"]}


@pytest.fixture
def token_valido(app, usuario_registrado):
    """Token firmado con la misma clave que usa la app bajo prueba."""
    return crear_token(usuario_registrado["id"], clave=app.config["SECRET_KEY"])


@pytest.fixture
def autorizacion(token_valido):
    """Header listo para `headers=autorizacion`."""
    return {"Authorization": f"Bearer {token_valido}"}
