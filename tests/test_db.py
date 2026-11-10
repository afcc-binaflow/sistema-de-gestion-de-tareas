"""Tests de la capa de persistencia (Fase 3, TC-DB).

Se ejercitan contra una conexion, no a traves de HTTP: estas propiedades son
invisibles desde arriba. La base es en memoria y se inicializa por test.

TC-DB-09 es la excepcion y a proposito: la rama de base en archivo solo existe
en el ciclo de vida de la app (`init_db`), asi que ese caso levanta la app real
apuntando a un archivo temporal. Sin el, la mitad de `db.py` que corre en
produccion queda sin ejecutar en la suite.
"""

import sqlite3
import threading
from pathlib import Path

import pytest

from config import ConfigTest
from db import conectar, inicializar
from repository import (
    borrar_tarea_de,
    buscar_usuario_por_nombre,
    crear_tarea,
    crear_usuario,
    listar_tareas_de,
    obtener_tarea_de,
)
from servidor import create_app


@pytest.fixture
def conexion():
    c = conectar(":memory:")
    inicializar(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# TC-DB-01 (TP-20): FK activa
# ---------------------------------------------------------------------------
def test_tarea_con_usuario_inexistente_falla_por_fk(conexion):
    with pytest.raises(sqlite3.IntegrityError):
        crear_tarea(conexion, "tarea", 9999)


# ---------------------------------------------------------------------------
# TC-DB-02 (TP-20): cascade
# ---------------------------------------------------------------------------
def test_borrar_usuario_cascada_a_sus_tareas(conexion):
    uid = crear_usuario(conexion, "juan", "hash")
    crear_tarea(conexion, "tarea de juan", uid)
    conexion.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
    conexion.commit()
    restantes = conexion.execute("SELECT COUNT(*) FROM tareas").fetchone()[0]
    assert restantes == 0


# ---------------------------------------------------------------------------
# TC-DB-03 (TP-03): unique
# ---------------------------------------------------------------------------
def test_usuario_duplicado_falla_por_unique(conexion):
    crear_usuario(conexion, "juan", "hash1")
    with pytest.raises(sqlite3.IntegrityError):
        crear_usuario(conexion, "juan", "hash2")


# ---------------------------------------------------------------------------
# TC-DB-04 (TP-19): collation nocase
# ---------------------------------------------------------------------------
def test_usuario_duplicado_case_insensitive(conexion):
    crear_usuario(conexion, "Juan", "hash1")
    with pytest.raises(sqlite3.IntegrityError):
        crear_usuario(conexion, "juan", "hash2")


# ---------------------------------------------------------------------------
# TC-DB-05 (TP-14): inyeccion SQL
# ---------------------------------------------------------------------------
def test_inyeccion_sql_se_almacena_literal(conexion):
    crear_usuario(conexion, "victima", "hash1")
    crear_usuario(conexion, "' OR 1=1 --", "hash2")

    fila = buscar_usuario_por_nombre(conexion, "' OR 1=1 --")
    assert fila is not None
    assert fila["usuario"] == "' OR 1=1 --"

    # La otra fila sigue intacta y nada se borro.
    assert buscar_usuario_por_nombre(conexion, "victima") is not None
    total = conexion.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    assert total == 2


# ---------------------------------------------------------------------------
# TC-DB-07 (TP-11): aislamiento por owner en el query
# ---------------------------------------------------------------------------
def test_listar_tareas_aislado_por_usuario(conexion):
    uid_a = crear_usuario(conexion, "a", "h")
    uid_b = crear_usuario(conexion, "b", "h")
    crear_tarea(conexion, "tarea de A", uid_a)
    crear_tarea(conexion, "tarea de B", uid_b)

    tareas_a = listar_tareas_de(conexion, uid_a)
    assert len(tareas_a) == 1
    assert tareas_a[0]["titulo"] == "tarea de A"

    tareas_b = listar_tareas_de(conexion, uid_b)
    assert len(tareas_b) == 1
    assert tareas_b[0]["titulo"] == "tarea de B"

    # obtener_tarea_de tambien respeta el owner.
    tarea_de_a = tareas_a[0]
    assert obtener_tarea_de(conexion, tarea_de_a["id"], uid_b) is None


# ---------------------------------------------------------------------------
# TC-DB-08 (TP-15): concurrencia
# ---------------------------------------------------------------------------
def test_concurrencia_sin_corrupcion(tmp_path):
    import os

    ruta = str(tmp_path / "concurrencia.db")
    c = conectar(ruta)
    inicializar(c)
    c.close()

    cantidad = 8

    def worker(indice):
        conn = conectar(ruta)
        try:
            crear_usuario(conn, f"user{indice}", f"hash{indice}")
        finally:
            conn.close()

    hilos = [threading.Thread(target=worker, args=(i,)) for i in range(cantidad)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    conn = conectar(ruta)
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    conn.close()
    assert total == cantidad


# ---------------------------------------------------------------------------
# TC-DB-09 (TP-20): la base en archivo se crea, persiste y sobrevive requests
# ---------------------------------------------------------------------------
def test_la_base_en_archivo_se_crea_y_persiste_entre_peticiones(tmp_path):
    """La configuracion de produccion usa un archivo, no `:memory:` (D-18).

    El test cubre las tres piezas que solo se ejecutan en ese modo: la carpeta
    que SQLite no crea (`servidor.create_app`), el esquema inicializado sobre la
    conexion de una peticion y el cierre por `teardown` (`db.init_db`). Que el
    login funcione en una **segunda** peticion es lo que prueba que los datos
    quedaron en disco y no en una conexion que ya se cerro.
    """

    class ConfigArchivo(ConfigTest):
        DATABASE = str(tmp_path / "datos" / "pfo2.db")

    assert not Path(ConfigArchivo.DATABASE).exists()

    app = create_app(ConfigArchivo)

    assert Path(ConfigArchivo.DATABASE).exists()

    with app.test_client() as cliente:
        creado = cliente.post(
            "/registro", json={"usuario": "juan", "contraseña": "1234"}
        )
        assert creado.status_code == 201

        login = cliente.post("/login", json={"usuario": "juan", "contraseña": "1234"})
        assert login.status_code == 200
