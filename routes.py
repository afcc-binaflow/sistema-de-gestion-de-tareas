"""Capa HTTP: parsea, valida, llama y responde. Nada mas (RNF-11).

Aca no hay SQL ni hashing. Cada vista delega en las capas de abajo y se limita a
traducir entre HTTP y el dominio.

Los manejadores de error viven aca por la misma razon: son traduccion de errores
a HTTP. Sin ellos, Flask responde HTML y el contrato de la API (siempre JSON) se
rompe justo cuando el cliente mas necesita leer el error.
"""

import sqlite3

from flask import current_app, jsonify, render_template, request

import repository
import security
from db import obtener_conexion


def bienvenida():
    """Pagina de bienvenida: publica y sin datos de ningun usuario.

    Es publica a proposito (RF-09, D-04 revisada). Un navegador no puede mandar
    el header de autorizacion al navegar, asi que exigir un token aca haria la
    pagina inalcanzable para una persona. Y no hay nada que proteger: la pagina
    no lleva tareas ni usuarios. Toda la proteccion vive en el CRUD JSON.
    """
    return render_template("bienvenida.html")


def _validar_credenciales(datos):
    """Valida el par (usuario, contraseña) que comparten `/registro` y `/login`.

    Es la MISMA regla en los dos endpoints (docs/api.md §4.1, §4.2 y §6), asi que
    vive en un solo lugar: duplicada, el dia que cambie un mensaje se cambia en
    uno solo y el otro empieza a mentir.

    Devuelve `((usuario_sin_espacios, contrasena), None)` cuando es valido, o
    `(None, mensaje)` cuando no lo es, con el texto exacto de un 400.
    `contraseña` no se recorta nunca (D-21): recortarla en silencio le cambia la
    credencial al usuario. `usuario` si se recorta, porque es un nombre.
    """
    if not isinstance(datos, dict):
        return None, "El cuerpo debe ser un objeto JSON"

    usuario = datos.get("usuario")
    contrasena = datos.get("contraseña")

    if not isinstance(usuario, str) or not usuario.strip():
        return None, "El campo 'usuario' es obligatorio y debe ser un texto no vacío"
    if not isinstance(contrasena, str) or not contrasena:
        return None, "El campo 'contraseña' es obligatorio y debe ser un texto no vacío"

    return (usuario.strip(), contrasena), None


def registrar():
    """Crea una cuenta: valida, hashea y delega el alta en el DAO.

    Cada decision esta en el contrato (docs/api.md §4.1):

    - 400: el cuerpo no es un objeto JSON, un campo falta, no es texto o esta
      vacio. `usuario` se valida **despues** de `strip()` (D-21); `contraseña`
      se usa tal como se escribio, sin recortar: recortar una password en
      silencio le cambia la credencial al usuario.
    - 409: el nombre ya esta tomado. No es 400 porque el cliente puede reaccionar
      distinto ante "mandaste mal los datos" que ante "ese nombre ya existe".
    - 201: creado. El cuerpo lleva solo `usuario`; el hash no sale nunca de la
      capa de datos (RF-04, TP-05).
    """
    datos = request.get_json(silent=True)
    credenciales, error = _validar_credenciales(datos)
    if error:
        return jsonify({"error": error}), 400

    usuario, contrasena = credenciales
    try:
        repository.crear_usuario(
            obtener_conexion(), usuario, security.hashear_password(contrasena)
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": "El usuario ya existe"}), 409

    return jsonify({"usuario": usuario}), 201


def iniciar_sesion():
    """Verifica credenciales y emite el token (docs/api.md §4.2).

    El UNICO camino de error del login es un solo 401 con el mismo cuerpo, tanto
    si el usuario no existe como si la contraseña esta mal (TP-07). Diferenciar
    los mensajes convierte el login en un buscador de usuarios validos: quien
    pregunta "existe juan?" obtiene la respuesta gratis.

    La `SECRET_KEY` se toma de la configuracion de la app y se pasa explicita a
    `security.crear_token`: el modulo de seguridad no conoce Flask ni la config,
    y la capa HTTP es la que sabe de donde sale el secreto. Sin esto, la clave
    configurada por la app se ignoraba y solo valia la del entorno.

    **Limite conocido y aceptado (D-29).** El `or` corta en corto: con el usuario
    inexistente no se ejecuta `verificar_password`, asi que la respuesta llega en
    ~1 ms contra ~336 ms de una password incorrecta. Por el cuerpo las dos causas
    son indistinguibles, por el reloj no. Se mide y se acepta: cerrarlo cuesta
    ~200 ms de CPU en cada login fallido, lo que agrega una palanca de DoS que
    hoy no existe, y este proyecto no tiene rate limiting por YAGNI.
    """
    datos = request.get_json(silent=True)
    credenciales, error = _validar_credenciales(datos)
    if error:
        return jsonify({"error": error}), 400

    usuario, contrasena = credenciales

    guardado = repository.buscar_usuario_por_nombre(obtener_conexion(), usuario)
    if guardado is None or not security.verificar_password(
        guardado["password_hash"], contrasena
    ):
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    token = security.crear_token(
        guardado["id"], clave=current_app.config["SECRET_KEY"]
    )
    return jsonify({"token": token}), 200


def recurso_no_encontrado(error):
    """404 en JSON. Flask responde HTML por defecto (TP-22)."""
    return jsonify({"error": "Recurso no encontrado"}), 404


def metodo_no_permitido(error):
    """405 en JSON, con el header `Allow` que exige la RFC 7231 §6.5.5.

    Flask responde HTML por defecto (TP-22). El `Allow` no es decorativo: sin el,
    el cliente no sabe que metodo **si** funciona y no tiene como corregir la
    llamada salvo leyendo la documentacion. `valid_methods` lo calcula Werkzeug a
    partir de la regla registrada, asi que la lista no se puede desincronizar.
    """
    respuesta = jsonify({"error": "Método no permitido"})
    respuesta.status_code = 405

    metodos = getattr(error, "valid_methods", None)
    if metodos:
        respuesta.headers["Allow"] = ", ".join(metodos)
    return respuesta


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
    app.add_url_rule("/registro", view_func=registrar, methods=["POST"])
    app.add_url_rule("/login", view_func=iniciar_sesion, methods=["POST"])

    # Fase 7.5 adelantada a la Fase 5: sin estos tres manejadores, 404, 405 y
    # 500 rompen el contrato JSON y el 500 expone el traceback.
    app.register_error_handler(404, recurso_no_encontrado)
    app.register_error_handler(405, metodo_no_permitido)
    app.register_error_handler(Exception, error_no_controlado)
