"""Capa HTTP: parsea, valida, llama y responde. Nada mas (RNF-11).

Aca no hay SQL ni hashing. Cada vista delega en las capas de abajo y se limita a
traducir entre HTTP y el dominio.

Los manejadores de error viven aca por la misma razon: son traduccion de errores
a HTTP. Sin ellos, Flask responde HTML y el contrato de la API (siempre JSON) se
rompe justo cuando el cliente mas necesita leer el error.
"""

import functools
import sqlite3

import jwt
from flask import current_app, g, jsonify, render_template, request

import repository
import security
from db import obtener_conexion

LIMITE_TITULO = 200

# SQLite guarda los enteros en 64 bits. `<int:>` de Werkzeug acepta enteros de
# cualquier tamano, asi que un id mayor llega al driver y revienta con
# OverflowError: un 500 por una entrada que el cliente controla.
#
# La cota NO puede vivir en el converter (`<int(max=...)>`): cuando la conversion
# falla en PUT o DELETE, Werkzeug ya acumulo los metodos de las reglas anteriores
# —GET y HEAD— y responde 405 con `Allow: GET, HEAD` en vez del 404 del contrato.
# Por eso se valida en la vista, con `_id_fuera_del_rango`.
ID_MAXIMO = 2**63 - 1


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


def _validar_tarea(datos):
    """Valida el recurso completo de una tarea; `POST` y `PUT` comparten la regla.

    Devuelve `((titulo, completada), None)` o `(None, mensaje)`. `titulo` se
    recorta **antes** de medir el largo (D-21 aplicado a tareas): "  x  " son tres
    caracteres, no cinco, y rechazarlo por largo seria contar espacios que no se
    guardan. `completada` se compara con `bool` y no con *truthy* a proposito:
    `"si"`, `1` y `[]` son `400`, no un `false` silencioso que el cliente no pidio.
    """
    if not isinstance(datos, dict):
        return None, "El cuerpo debe ser un objeto JSON"

    titulo = datos.get("titulo")
    if not isinstance(titulo, str) or not titulo.strip():
        return None, "El campo 'titulo' es obligatorio y debe ser un texto no vacío"

    titulo = titulo.strip()
    if len(titulo) > LIMITE_TITULO:
        return None, "El campo 'titulo' no puede superar los 200 caracteres"

    completada = datos.get("completada", False)
    if not isinstance(completada, bool):
        return None, "El campo 'completada' debe ser un booleano"

    return (titulo, completada), None


def _id_fuera_del_rango(tarea_id):
    """True si el id no cabe en un `INTEGER` de SQLite, o sea si no puede existir.

    Un id fuera de rango no es un error del servidor: es un recurso que no existe,
    y el contrato (§4.6) pide 404. Se comprueba antes de tocar la base porque el
    driver no puede ni recibir el valor.
    """
    return not 1 <= tarea_id <= ID_MAXIMO


def _usuario_del_token():
    """Devuelve el id del usuario del header `Authorization`, o `None`.

    La clave se pasa **explicita** desde la config de la app. Sin eso,
    `security.decodificar_token` cae al `SECRET_KEY` del entorno: si los dos no
    coinciden, la app firma con una clave y valida con otra, y el sintoma es que
    todos los tokens son invalidos sin ninguna pista de por que.
    """
    cabecera = request.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    # RFC 7235 §2.1: el nombre del esquema es case-insensitive.
    if esquema.lower() != "bearer" or not token.strip():
        return None

    try:
        payload = security.decodificar_token(
            token.strip(), clave=current_app.config["SECRET_KEY"]
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def requiere_token(vista):
    """Exige `Authorization: Bearer <token>` y deja el usuario en `g.usuario_id`.

    Es un decorador y no un chequeo repetido por endpoint porque el olvido es el
    bug: una vista nueva sin el decorador es un endpoint abierto, y el decorador
    hace visible en el codigo que esa ruta esta protegida.

    Un solo 401 para las seis causas del contrato (docs/api.md §1): header
    ausente, sin `Bearer`, token vacio, malformado, alterado, expirado o firmado
    con otra clave. Distinguirlas le diria al cliente —y a un atacante— en que
    parte del token acerto.
    """

    @functools.wraps(vista)
    def envoltura(*args, **kwargs):
        usuario_id = _usuario_del_token()
        if usuario_id is None:
            return jsonify({"error": "Token ausente o inválido"}), 401
        g.usuario_id = usuario_id
        return vista(*args, **kwargs)

    return envoltura


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


@requiere_token
def listar_tareas():
    """`GET /api/tareas`: solo las del dueno (RF-11).

    El filtro va en el `WHERE` del SQL (`repository.listar_tareas_de`), no
    filtrando en Python despues de leer todo: filtrar despues significa que
    olvidarse una vez devuelve datos ajenos y nada en el camino feliz lo revela.
    """
    return jsonify(repository.listar_tareas_de(obtener_conexion(), g.usuario_id))


@requiere_token
def crear_tarea():
    """`POST /api/tareas`: el dueno sale del token, nunca del cuerpo (RF-10).

    Aceptar un `usuario_id` del cliente seria un IDOR de escritura: el atacante
    crearia tareas a nombre de cualquiera. El campo no se lee ni para ignorarlo
    explicitamente: simplemente no existe para esta vista.
    """
    datos = request.get_json(silent=True)
    tarea, error = _validar_tarea(datos)
    if error:
        return jsonify({"error": error}), 400

    titulo, completada = tarea
    tarea_id = repository.crear_tarea(
        obtener_conexion(), titulo, g.usuario_id, completada
    )
    return jsonify({"id": tarea_id, "titulo": titulo, "completada": completada}), 201


@requiere_token
def obtener_tarea(tarea_id):
    """`GET /api/tareas/<id>`: 404 si no existe **o si no es tuya** (D-07).

    Un 403 confirmaria que la tarea existe, que es informacion del otro usuario.
    404 no revela nada y es coherente con el login, que tampoco dice si un
    usuario existe.
    """
    if _id_fuera_del_rango(tarea_id):
        return jsonify({"error": "Recurso no encontrado"}), 404

    tarea = repository.obtener_tarea_de(obtener_conexion(), tarea_id, g.usuario_id)
    if tarea is None:
        return jsonify({"error": "Recurso no encontrado"}), 404
    return jsonify(tarea)


@requiere_token
def actualizar_tarea(tarea_id):
    """`PUT /api/tareas/<id>`: reemplaza el recurso completo (D-17).

    Se valida el cuerpo **antes** de buscar la tarea: un cuerpo invalido es 400
    exista o no la tarea, asi que la respuesta no filtra si el id pertenece a
    alguien. El `WHERE` del `UPDATE` filtra por dueno, y que no toque ninguna fila
    es el 404 — un update a la tarea de otro no es ni exito ni no-op silencioso.
    """
    datos = request.get_json(silent=True)
    tarea, error = _validar_tarea(datos)
    if error:
        return jsonify({"error": error}), 400

    titulo, completada = tarea
    if _id_fuera_del_rango(tarea_id):
        return jsonify({"error": "Recurso no encontrado"}), 404
    if not repository.actualizar_tarea_de(
        obtener_conexion(), tarea_id, g.usuario_id, titulo, completada
    ):
        return jsonify({"error": "Recurso no encontrado"}), 404

    actualizada = repository.obtener_tarea_de(
        obtener_conexion(), tarea_id, g.usuario_id
    )
    return jsonify(actualizada)


@requiere_token
def borrar_tarea(tarea_id):
    """`DELETE /api/tareas/<id>`: 204 sin cuerpo (D-23).

    Devolver `{"ok": true}` contradiria el status: 204 significa justamente
    "listo, no hay nada que devolver". Por eso la respuesta no lleva
    `Content-Type`: no hay contenido que tipar.

    `return "", 204` no alcanza: Werkzeug le pone igual
    `text/html; charset=utf-8` a cualquier respuesta vacia. Se construye la
    respuesta y se quita el header a mano, que es lo unico que cumple D-23.
    """
    if _id_fuera_del_rango(tarea_id):
        return jsonify({"error": "Recurso no encontrado"}), 404
    if not repository.borrar_tarea_de(obtener_conexion(), tarea_id, g.usuario_id):
        return jsonify({"error": "Recurso no encontrado"}), 404

    respuesta = current_app.response_class(status=204)
    respuesta.headers.pop("Content-Type", None)
    return respuesta


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

    Sin blueprint incluso con el prefijo `/api` de la Fase 7: cinco reglas de una
    linea no se vuelven mas simples con un objeto de registro aparte, y lo que
    comparten —el error 401, `g.usuario_id`, los manejadores de error— es de la
    app, no del prefijo. El blueprint se gana su lugar cuando haya estado propio
    que el prefijo comparta, no antes.

    `<int:tarea_id>` es `int` a proposito: `/api/tareas/abc` no matchea la ruta y
    cae en el 404 del contrato (docs/api.md §4.6), sin codigo extra. El techo del
    rango va en la vista y no en el converter: ver `ID_MAXIMO`.

    `provide_automatic_options=False` en las cinco reglas de `/api`: Flask
    contesta `OPTIONS` por su cuenta con un 200 en HTML, que es a la vez un
    metodo que el contrato no declara y una respuesta que no es JSON. Un 405 con
    `Allow` dice lo mismo y dice la verdad.
    """
    app.add_url_rule("/tareas", view_func=bienvenida, methods=["GET"])
    app.add_url_rule("/registro", view_func=registrar, methods=["POST"])
    app.add_url_rule("/login", view_func=iniciar_sesion, methods=["POST"])

    # Una sola lista para las cinco reglas de la API: asi ninguna se queda sin
    # `provide_automatic_options=False` por olvido, que es el mismo argumento por
    # el que el chequeo de token es un decorador y no una linea en cada vista.
    for regla, vista, metodos in (
        ("/api/tareas", listar_tareas, ["GET"]),
        ("/api/tareas", crear_tarea, ["POST"]),
        ("/api/tareas/<int:tarea_id>", obtener_tarea, ["GET"]),
        ("/api/tareas/<int:tarea_id>", actualizar_tarea, ["PUT"]),
        ("/api/tareas/<int:tarea_id>", borrar_tarea, ["DELETE"]),
    ):
        app.add_url_rule(
            regla,
            view_func=vista,
            methods=metodos,
            provide_automatic_options=False,
        )

    # Fase 7.5 adelantada a la Fase 5: sin estos tres manejadores, 404, 405 y
    # 500 rompen el contrato JSON y el 500 expone el traceback.
    app.register_error_handler(404, recurso_no_encontrado)
    app.register_error_handler(405, metodo_no_permitido)
    app.register_error_handler(Exception, error_no_controlado)
