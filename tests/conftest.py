"""Fixtures base de la suite (Fase 2.4).

Esta infraestructura se adelanta al codigo de produccion a proposito. Si llega
al final del proyecto, las fases 3 a 8 se escriben sin red de seguridad, que es
exactamente el defecto que el plan anterior tenia.

Regla dura (RNF-12): los tests **nunca** tocan `instance/pfo2.db`. La app de
cada test se crea con `ConfigTest`, que apunta a una base en memoria.

Fixture de alcance deliberadamente corto
----------------------------------------
El plan de la Fase 2.4 lista cuatro fixtures: `app`, `client`,
`usuario_registrado`/`token_valido` y `db_vacia`. Hoy solo existen las dos
primeras, y no es un olvido:

- `usuario_registrado` necesita hashing (`security.py`, Fase 4) o escribir el
  hash a mano en el test, que seria duplicar la logica de seguridad en la suite.
- `token_valido` necesita `crear_token` (Fase 4).
- `db_vacia` necesita `init_db()` y un esquema que crear (Fase 3). En 1.1 ya se
  documento por que `init_db()` no existe todavia: no hay DDL que ejecutar.

Una fixture que crea estado que ninguna capa sabe crear solo puede construir ese
estado con SQL inventado. AGENTS.md lo prohibe, y ademas haria que la suite
midiera la suite en vez de la aplicacion. Las tres se agregan en la fase que las
vuelve posibles.
"""

import pytest

from config import ConfigTest
from servidor import create_app


@pytest.fixture
def app():
    """Una app nueva por test, con base en memoria (RNF-12, D-18)."""
    return create_app(ConfigTest)


@pytest.fixture
def client(app):
    """Cliente HTTP de Flask para ejercitar los endpoints sin levantar un server."""
    return app.test_client()
