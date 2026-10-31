"""DAO: acceso a datos con consultas parametrizadas (SRP, RNF-11).

Cada funcion recibe la conexion como primer argumento: asi se pueden ejercitar
con una base en memoria sin levantar la aplicacion (seam de db.conectar).

El aislamiento por owner se garantiza en la consulta (WHERE id = ? AND
usuario_id = ?), no filtrando despues en Python: asi es imposible olvidarse
un caso.

Las consultas son siempre parametrizadas con `?`: nunca se arma SQL con
f-strings a partir de entrada del usuario (TP-14).
"""

import sqlite3


def crear_usuario(conexion, usuario, password_hash):
    """Crea un usuario y devuelve su id. Lanza IntegrityError si ya existe."""
    cursor = conexion.execute(
        "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
        (usuario, password_hash),
    )
    conexion.commit()
    return cursor.lastrowid


def buscar_usuario_por_nombre(conexion, usuario):
    """Busca un usuario por nombre (case-insensitive por COLLATE NOCASE)."""
    return conexion.execute(
        "SELECT id, usuario, password_hash FROM usuarios WHERE usuario = ?",
        (usuario,),
    ).fetchone()


def crear_tarea(conexion, titulo, usuario_id):
    """Crea una tarea para un usuario y devuelve su id."""
    cursor = conexion.execute(
        "INSERT INTO tareas (titulo, usuario_id) VALUES (?, ?)",
        (titulo, usuario_id),
    )
    conexion.commit()
    return cursor.lastrowid


def listar_tareas_de(conexion, usuario_id):
    """Lista las tareas de un usuario, ordenadas por id."""
    filas = conexion.execute(
        "SELECT id, titulo, completada FROM tareas WHERE usuario_id = ? ORDER BY id",
        (usuario_id,),
    ).fetchall()
    return [_a_tarea(fila) for fila in filas]


def obtener_tarea_de(conexion, tarea_id, usuario_id):
    """Devuelve una tarea si pertenece al usuario, o None."""
    fila = conexion.execute(
        "SELECT id, titulo, completada FROM tareas WHERE id = ? AND usuario_id = ?",
        (tarea_id, usuario_id),
    ).fetchone()
    return _a_tarea(fila) if fila is not None else None


def actualizar_tarea_de(conexion, tarea_id, usuario_id, titulo=None, completada=None):
    """Actualiza titulo y/o completada. Devuelve True si se modifico una fila."""
    campos = []
    valores = []
    if titulo is not None:
        campos.append("titulo = ?")
        valores.append(titulo)
    if completada is not None:
        campos.append("completada = ?")
        valores.append(1 if completada else 0)
    if not campos:
        return False
    valores.extend([tarea_id, usuario_id])
    cursor = conexion.execute(
        "UPDATE tareas SET " + ", ".join(campos) + " WHERE id = ? AND usuario_id = ?",
        valores,
    )
    conexion.commit()
    return cursor.rowcount > 0


def borrar_tarea_de(conexion, tarea_id, usuario_id):
    """Borra una tarea si pertenece al usuario. Devuelve True si se borro."""
    cursor = conexion.execute(
        "DELETE FROM tareas WHERE id = ? AND usuario_id = ?",
        (tarea_id, usuario_id),
    )
    conexion.commit()
    return cursor.rowcount > 0


def _a_tarea(fila):
    # D-22: SQLite guarda 0/1; el contrato JSON es true/false. La conversion es
    # trabajo de esta capa, no del HTTP.
    return {
        "id": fila["id"],
        "titulo": fila["titulo"],
        "completada": bool(fila["completada"]),
    }
