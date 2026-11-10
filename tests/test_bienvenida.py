"""Tests de la pagina de bienvenida (Fase 1.1, ampliada en la Fase 9).

La pagina es publica a proposito (RF-09, D-04 revisada): un navegador no puede
mandar el header de autorizacion al navegar. Eso la deja sin proteccion de
token, asi que lo que hay que demostrar es lo otro: que no muestra **nada** de
ningun usuario. Un 200 no alcanza; el test tiene que mirar el cuerpo.

Por eso TC-HTML-02 se escribe con datos reales cargados: con la base vacia, "el
HTML no filtra datos" se cumple solo porque no hay datos que filtrar.
"""

# ---------------------------------------------------------------------------
# TC-HTML-01 (TP-21): publica y servida como HTML
# ---------------------------------------------------------------------------
def test_la_bienvenida_es_publica_y_responde_html(client):
    respuesta = client.get("/tareas")

    assert respuesta.status_code == 200
    assert respuesta.headers["Content-Type"] == "text/html; charset=utf-8"


# ---------------------------------------------------------------------------
# TC-HTML-02 (TP-21): no filtra datos de ningun usuario
# ---------------------------------------------------------------------------
def test_la_bienvenida_no_cambia_cuando_la_base_tiene_datos(
    client, usuario_registrado, autorizacion
):
    """El cuerpo es identico con y sin tareas.

    Comparar los dos cuerpos es la asercion que de verdad prueba "no filtra": un
    barrido de strings se rompe con cualquier digito decorativo del template
    (`initial-scale=1`) y no ve un dato nuevo. Si la pagina cambiara de tamano al
    cargar datos, este test lo delata.
    """
    antes = client.get("/tareas").get_data()

    respuesta = client.post(
        "/api/tareas", json={"titulo": "tarea privada de juan"}, headers=autorizacion
    )
    assert respuesta.status_code == 201

    despues = client.get("/tareas").get_data()

    assert despues == antes
    cuerpo = despues.decode("utf-8")
    assert "juan" not in cuerpo
    assert "tarea privada de juan" not in cuerpo


# ---------------------------------------------------------------------------
# TC-HTML-03 (TP-01): la ruta HTML no es un endpoint de escritura
# ---------------------------------------------------------------------------
def test_post_sobre_la_bienvenida_da_405(client):
    respuesta = client.post("/tareas", json={"titulo": "x"})

    assert respuesta.status_code == 405
