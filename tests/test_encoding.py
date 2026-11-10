"""Tests de encoding (TC-ENC-01, RNF-10/TP-23).

Por que mirar los bytes y no el JSON parseado
---------------------------------------------
`respuesta.get_json()["titulo"] == "contraseña"` pasa igual si el servidor manda
`\\u00f1`: el parseo reconstruye la enie y el test no ve nada. RNF-10 pide que los
**bytes** que viajan sean UTF-8, asi que aca se mira el cuerpo crudo.

El caso se complementa con TC-E2E-09, que prueba la ida y vuelta de una password
con enie a traves del cliente de consola.
"""


def test_los_bytes_de_la_respuesta_son_utf8_y_no_escapes(client, autorizacion):
    client.post("/api/tareas", json={"titulo": "contraseña"}, headers=autorizacion)

    respuesta = client.get("/api/tareas", headers=autorizacion)

    crudo = respuesta.get_data()
    assert respuesta.mimetype == "application/json"
    assert b"\xc3\xb1" in crudo, "la enie tiene que viajar como dos bytes UTF-8"
    assert b"\\u00f1" not in crudo, "y no como el escape de JSON"
