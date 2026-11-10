"""Capa HTTP: parsea, valida, llama y responde. Nada mas (RNF-11).

Aca no hay SQL ni hashing. Cada vista delega en las capas de abajo y se limita a
traducir entre HTTP y el dominio.

Los manejadores de error viven aca por la misma razon: son traduccion de errores
a HTTP. Sin ellos, Flask responde HTML y el contrato de la API (siempre JSON) se
rompe justo cuando el cliente mas necesita leer el error.
"""

from flask import current_app, jsonify, render_template


def bienvenida():
    """Pagina de bienvenida: publica y sin datos de ningun usuario.

    Es publica a proposito (RF-09, D-04 revisada). Un navegador no puede mandar
    el header de autorizacion al navegar, asi que exigir un token aca haria la
    pagina inalcanzable para una persona. Y no hay nada que proteger: la pagina
    no lleva tareas ni usuarios. Toda la proteccion vive en el CRUD JSON.
    """
    return render_template("bienvenida.html")


def recurso_no_encontrado(error):
    """404 en JSON. Flask responde HTML por defecto (TP-22)."""
    return jsonify({"error": "Recurso no encontrado"}), 404


def metodo_no_permitido(error):
    """405 en JSON. Flask responde HTML por defecto (TP-22)."""
    return jsonify({"error": "Metodo no permitido"}), 405


def error_no_controlado(error):
    """500 en JSON, con el detalle solo en el log del servidor (TP-16).

    Nunca se devuelve el traceback: en produccion un stack trace revela rutas
    internas, versiones de librerias y estructura del codigo. El detalle queda
    en el log, que es el lugar donde sirve para depurar. Silenciar la excepcion
    en los dos lados seria peor que filtrarla.
    """
    current_app.logger.exception("Error no controlado")
    return jsonify({"error": "Error interno del servidor"}), 500


def registrar_rutas(app):
    """Conecta las rutas a la app.

    Sin blueprint a proposito: hoy es una abstraccion con una sola
    implementacion, justo lo que AGENTS.md prohibe. Cuando haya un grupo de
    rutas que compartan prefijo, el blueprint se gana su lugar.
    """
    app.add_url_rule("/tareas", view_func=bienvenida, methods=["GET"])

    # Fase 7.5 adelantada a la Fase 5: sin estos tres manejadores, 404, 405 y
    # 500 rompen el contrato JSON y el 500 expone el traceback.
    app.register_error_handler(404, recurso_no_encontrado)
    app.register_error_handler(405, metodo_no_permitido)
    app.register_error_handler(Exception, error_no_controlado)
