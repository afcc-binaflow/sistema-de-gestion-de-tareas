"""Capa HTTP: parsea, valida, llama y responde. Nada mas (RNF-11).

Aca no hay SQL ni hashing. Cada vista delega en las capas de abajo y se limita a
traducir entre HTTP y el dominio.
"""

from flask import render_template


def bienvenida():
    """Pagina de bienvenida: publica y sin datos de ningun usuario.

    Es publica a proposito (RF-09, D-04 revisada). Un navegador no puede mandar
    el header de autorizacion al navegar, asi que exigir un token aca haria la
    pagina inalcanzable para una persona. Y no hay nada que proteger: la pagina
    no lleva tareas ni usuarios. Toda la proteccion vive en el CRUD JSON.
    """
    return render_template("bienvenida.html")


def registrar_rutas(app):
    """Conecta las rutas a la app.

    Sin blueprint a proposito: hoy es una abstraccion con una sola
    implementacion, justo lo que AGENTS.md prohibe. Cuando haya un grupo de
    rutas que compartan prefijo, el blueprint se gana su lugar.
    """
    app.add_url_rule("/tareas", view_func=bienvenida, methods=["GET"])
