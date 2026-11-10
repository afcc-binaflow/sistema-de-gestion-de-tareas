"""Cliente de consola del gestor de tareas (Fase 8, RF-16/RF-17, RNF-10).

Dos capas, y la separacion no es decorativa (RNF-11):

- `ApiDeTareas` es **transporte**: arma la URL, manda el token, pone el `timeout`
  y traduce la respuesta a datos o a excepcion. No imprime nada.
- `menu` es **presentacion**: lee opciones, llama al transporte e imprime. No sabe
  que existe HTTP.

Gracias a eso el cliente se puede testear con el `test_client` de Flask (ver
`tests/test_cliente.py`) sin levantar un puerto ni automatizar el teclado, y el
dia que haya que reemplazar la consola por una interfaz grafica, la capa de red
se reusa tal cual.

Decisiones que se ven en este archivo:

- **El token vive en memoria** (`self.token`), nunca en disco (RF-16): escribirlo
  en un archivo en texto plano es exactamente lo que el hashing busca evitar.
- **No hay logout del lado del servidor** (D-17): `cerrar_sesion` solo borra el
  token local. Un JWT es stateless y revocarlo exigiria una blacklist.
- **Un solo `_enviar`** centraliza lo que no se puede olvidar en ninguna llamada:
  URL, header `Authorization`, `timeout` explicito y traduccion de errores. Siete
  metodos copiando esas cuatro lineas es como se cuela la llamada sin timeout.
- **Nunca se imprime un traceback**: el usuario ve una linea con el status y el
  mensaje de la API, o el motivo del fallo de red.
"""

import os
import sys

import requests

URL_BASE_POR_DEFECTO = "http://127.0.0.1:5000"

# Segundos. Sin `timeout`, si la API no responde el cliente se cuelga para
# siempre y el usuario no sabe si fallo o si esta esperando.
TIEMPO_ESPERA = 5

_SALIR = "7"


class ErrorDeApi(Exception):
    """La API respondio un status de error. Lleva el `error` del contrato.

    `sesion_cerrada` distingue el 401 de una llamada autenticada — el token que
    mandamos ya no sirve — del 401 de un login con credenciales equivocadas. El
    mensaje para una persona no es el mismo, y el cliente no deberia adivinarlo
    mirando el codigo.
    """

    def __init__(self, codigo, mensaje, sesion_cerrada=False):
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje
        self.sesion_cerrada = sesion_cerrada


class ErrorDeRed(Exception):
    """No hubo respuesta: API caida, DNS, timeout de conexion."""

    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


class ErrorDeUso(Exception):
    """Lo que escribio el usuario no se puede interpretar (id, s/n)."""


class _FinDeEntrada(Exception):
    """La entrada se termino (Ctrl+Z, pipe cerrado): se sale sin traceback."""


class ApiDeTareas:
    """Transporte contra la API. Recibe la sesion HTTP por parametro.

    El default es `requests.Session()`; los tests pasan un adaptador sobre el
    `test_client` de Flask. Es el unico punto de costura entre red y codigo, y
    existe porque hay una segunda implementacion real, no "por si acaso".
    """

    def __init__(
        self,
        url_base=URL_BASE_POR_DEFECTO,
        sesion=None,
        tiempo_espera=TIEMPO_ESPERA,
    ):
        self.url_base = url_base.rstrip("/")
        self.tiempo_espera = tiempo_espera
        self.token = None
        self._sesion = sesion if sesion is not None else requests.Session()

    # -- autenticacion -----------------------------------------------------
    def registrar(self, usuario, contrasena):
        """`POST /registro`. No devuelve token: el registro no inicia sesion."""
        return self._enviar(
            "post",
            "/registro",
            {"usuario": usuario, "contraseña": contrasena},
            autenticada=False,
        )

    def iniciar_sesion(self, usuario, contrasena):
        """`POST /login` y guarda el token en memoria."""
        datos = self._enviar(
            "post",
            "/login",
            {"usuario": usuario, "contraseña": contrasena},
            autenticada=False,
        )
        self.token = datos["token"]
        return datos

    def cerrar_sesion(self):
        """Borra el token local. En el servidor el token sigue siendo valido."""
        self.token = None

    # -- tareas ------------------------------------------------------------
    def listar_tareas(self):
        """`GET /api/tareas` de la persona con sesion iniciada."""
        return self._enviar("get", "/api/tareas")

    def crear_tarea(self, titulo):
        """`POST /api/tareas`. `completada` arranca en `false` (lo pone la API)."""
        return self._enviar("post", "/api/tareas", {"titulo": titulo})

    def actualizar_tarea(self, tarea_id, titulo, completada):
        """`PUT /api/tareas/<id>`: reemplaza el recurso **completo** (D-17).

        Mandar solo el titulo devolveria la tarea a `completada: false`: el
        cliente pide los dos campos aunque el usuario solo quiera cambiar uno.
        """
        return self._enviar(
            "put",
            f"/api/tareas/{tarea_id}",
            {"titulo": titulo, "completada": completada},
        )

    def borrar_tarea(self, tarea_id):
        """`DELETE /api/tareas/<id>`. La API responde 204 sin cuerpo (D-23)."""
        return self._enviar("delete", f"/api/tareas/{tarea_id}")

    # -- una sola puerta hacia la red --------------------------------------
    def _enviar(self, metodo, ruta, cuerpo=None, autenticada=True):
        """Hace la llamada y traduce: datos, `ErrorDeApi` o `ErrorDeRed`.

        `autenticada` es `False` para `/registro` y `/login`: esas dos rutas no
        leen el header, y mandarselo igual filtraria el token a un log ajeno sin
        ninguna ganancia. Ademas deja limpio el otro uso del flag: un 401 de una
        llamada autenticada es un token muerto, y uno de `/login` es una
        credencial equivocada.
        """
        con_token = autenticada and bool(self.token)
        try:
            respuesta = getattr(self._sesion, metodo)(
                self.url_base + ruta,
                json=cuerpo,
                headers=self._cabeceras(con_token),
                timeout=self.tiempo_espera,
            )
        except requests.RequestException as error:
            raise ErrorDeRed(str(error)) from None

        if respuesta.status_code >= 400:
            sesion_cerrada = respuesta.status_code == 401 and con_token
            if sesion_cerrada:
                # El token que mandamos no sirve mas (vencido, alterado, otra
                # clave). Seguir usandolo solo repite el 401: se borra.
                self.token = None
            raise ErrorDeApi(
                respuesta.status_code,
                self._mensaje_de_error(respuesta),
                sesion_cerrada,
            )

        if respuesta.status_code == 204:
            return None
        return respuesta.json()

    def _cabeceras(self, con_token):
        if not con_token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @staticmethod
    def _mensaje_de_error(respuesta):
        """Saca el `error` del contrato, o un texto honesto si no es JSON.

        Un proxy por delante de la API puede devolver HTML (502, 504). Reventar
        con un `JSONDecodeError` ahi seria cambiar un mensaje util por un
        traceback del cliente.
        """
        try:
            datos = respuesta.json()
        except ValueError:
            return "la respuesta no es JSON"
        if isinstance(datos, dict) and isinstance(datos.get("error"), str):
            return datos["error"]
        return "la respuesta no trae el campo 'error'"


def formatear_error(error):
    """Una sola linea, sin traceback, para mostrarle a una persona."""
    if isinstance(error, ErrorDeApi):
        linea = f"Error {error.codigo}: {error.mensaje}"
        if error.sesion_cerrada:
            linea += ". Volvé a iniciar sesión (opción 2)"
        return linea
    if isinstance(error, ErrorDeRed):
        return f"No se pudo conectar con la API: {error.motivo}"
    return str(error)


# ---------------------------------------------------------------------------
# Presentacion
# ---------------------------------------------------------------------------
def menu(api, leer=input, escribir=print):
    """Bucle del menu. Devuelve el codigo de salida del proceso.

    `leer` y `escribir` se inyectan para poder guionar una sesion desde pytest:
    el codigo de salida y la ausencia de traceback (TC-E2E-02/03) viven aca, no
    en el transporte.

    El codigo es 1 si alguna operacion fallo durante la sesion, 0 si salio todo
    bien. Que una operacion falle no cierra el programa: el usuario corrige y
    sigue.
    """

    def pedir(mensaje):
        try:
            return leer(mensaje)
        except (EOFError, StopIteration):
            raise _FinDeEntrada from None

    codigo = 0
    while True:
        _mostrar_menu(api, escribir)
        try:
            opcion = pedir("Opción: ").strip()
            if opcion == _SALIR:
                escribir("Hasta luego.")
                return codigo
            entrada = _ACCIONES.get(opcion)
            if entrada is None:
                escribir("Opción inválida. Elegí un número del 1 al 7.")
                continue
            _, accion = entrada
            accion(api, pedir, escribir)
        except _FinDeEntrada:
            return codigo
        except (ErrorDeApi, ErrorDeRed, ErrorDeUso) as error:
            escribir(formatear_error(error))
            codigo = 1


def _mostrar_menu(api, escribir):
    escribir("")
    escribir("=== Gestor de tareas ===")
    escribir("Sesión iniciada." if api.token else "Sin sesión iniciada.")
    for clave, (etiqueta, _) in _ACCIONES.items():
        escribir(f"{clave}. {etiqueta}")
    escribir(f"{_SALIR}. Salir")


def _hay_sesion(api, escribir):
    """Sin token no se llama a la API: el 401 lo dice igual, pero de mas."""
    if api.token:
        return True
    escribir("Primero iniciá sesión (opción 2).")
    return False


def _registrarse(api, pedir, escribir):
    usuario = pedir("Usuario: ").strip()
    contrasena = pedir("Contraseña: ")
    datos = api.registrar(usuario, contrasena)
    escribir(f"Usuario '{datos['usuario']}' creado. Ahora iniciá sesión (opción 2).")


def _iniciar_sesion(api, pedir, escribir):
    usuario = pedir("Usuario: ").strip()
    contrasena = pedir("Contraseña: ")
    api.iniciar_sesion(usuario, contrasena)
    escribir(f"Sesión iniciada como '{usuario}'.")


def _listar(api, pedir, escribir):
    if not _hay_sesion(api, escribir):
        return
    tareas = api.listar_tareas()
    if not tareas:
        escribir("No tenés tareas todavía.")
        return
    for tarea in tareas:
        marca = "[x]" if tarea["completada"] else "[ ]"
        escribir(f"{tarea['id']} {marca} {tarea['titulo']}")


def _crear(api, pedir, escribir):
    if not _hay_sesion(api, escribir):
        return
    titulo = pedir("Título: ")
    tarea = api.crear_tarea(titulo)
    escribir(f"Tarea {tarea['id']} creada.")


def _editar(api, pedir, escribir):
    if not _hay_sesion(api, escribir):
        return
    tarea_id = _pedir_id(pedir)
    titulo = pedir("Título: ")
    completada = _pedir_completada(pedir)
    tarea = api.actualizar_tarea(tarea_id, titulo, completada)
    escribir(f"Tarea {tarea['id']} actualizada.")


def _borrar(api, pedir, escribir):
    if not _hay_sesion(api, escribir):
        return
    tarea_id = _pedir_id(pedir)
    api.borrar_tarea(tarea_id)
    escribir(f"Tarea {tarea_id} borrada.")


def _pedir_id(pedir):
    texto = pedir("Id de la tarea: ").strip()
    try:
        return int(texto)
    except ValueError:
        raise ErrorDeUso("El id tiene que ser un número entero") from None


def _pedir_completada(pedir):
    """`s`/`n` explicitos: cualquier otra cosa se rechaza, no se adivina."""
    texto = pedir("¿Completada? (s/n): ").strip().lower()
    if texto == "s":
        return True
    if texto == "n":
        return False
    raise ErrorDeUso("Respondé s o n")


# Las seis acciones comparten firma `(api, pedir, escribir)` para que el
# despacho sea una sola linea. `_listar` no usa `pedir`: es la firma del
# protocolo, no un parametro olvidado.
_ACCIONES = {
    "1": ("Registrarse", _registrarse),
    "2": ("Iniciar sesión", _iniciar_sesion),
    "3": ("Listar tareas", _listar),
    "4": ("Crear tarea", _crear),
    "5": ("Editar tarea", _editar),
    "6": ("Borrar tarea", _borrar),
}


def _configurar_utf8():
    """Fuerza UTF-8 en la consola (RNF-10, TP-23).

    La consola de Windows arranca en `cp1252` y rompe con `contraseña`. Se
    reconfigura solo si el flujo lo permite: cuando la salida esta redirigida a
    un archivo o a un pipe, no hay nada que reconfigurar.
    """
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")


def principal():
    """Punto de entrada: UTF-8, URL de `PFO2_API_URL` y menu."""
    _configurar_utf8()
    url = os.environ.get("PFO2_API_URL", URL_BASE_POR_DEFECTO)
    return menu(ApiDeTareas(url))


if __name__ == "__main__":
    sys.exit(principal())
