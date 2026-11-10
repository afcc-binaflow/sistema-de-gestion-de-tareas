# Traceability matrix — Phase 9.2

**Purpose.** Demonstrate, in both directions, that nothing is missing: every requirement reaches
at least one executed test, and every test names the requirement it serves.

- **Forward** — `RF/RNF → TP → TC → test → result`. A requirement with no test is an unverified
  requirement, which is an open risk dressed as a finished feature.
- **Reverse** — `test → TC → requirement`. A test with no requirement is an orphan: either it
  should not exist, or the requirement it protects was never written down.

**Scope of this pass.** The software as it stands at commit `8c9a4f3` (2026-11-10), branch `main`.
The assignment deliverables `DEL-03 … DEL-08` belong to Phases 10 and 11; they appear in §4 as
**PENDING**, which is a schedule fact, not a defect. Nothing in this document invents a requirement
that `docs/requisitos.md` does not already contain.

---

## 1. Evidence

Both commands run from the repository root, in the project virtualenv, on 2026-11-10.

```
.\venv\Scripts\python.exe -m pytest -q
156 passed in 49.49s
```

```
.\venv\Scripts\python.exe -m pytest -q --cov=cliente --cov=config --cov=db ^
  --cov=repository --cov=routes --cov=security --cov=servidor --cov-report=term-missing
```

| Module | Stmts | Miss | Cover | Missing |
|---|---|---|---|---|
| `cliente.py` | 177 | 1 | 99% | 376 |
| `config.py` | 12 | 0 | 100% | — |
| `db.py` | 33 | 0 | 100% | — |
| `repository.py` | 27 | 0 | 100% | — |
| `routes.py` | 140 | 0 | 100% | — |
| `security.py` | 23 | 0 | 100% | — |
| `servidor.py` | 19 | 1 | 95% | 57 |
| **TOTAL** | **431** | **2** | **99%** | |

The two misses are the same construct in two files: the `if __name__ == "__main__":` line of
`cliente.py` (376) and of `servidor.py` (57). They start a process and hand control to `principal()`
and to `app.run()`; the behaviour behind them is covered through `principal()` and `create_app()`.
Covering them would mean launching a server inside the suite to assert that Python's import
machinery works — cost with no information.

**What coverage does and does not say.** It says which lines the suite never executes. It says
nothing about whether an executed line is *asserted*: a test can run a function and check nothing.
That gap is why this document traces requirements to cases and cases to tests instead of stopping at
a percentage.

### 1.1 Shape of the suite

`156` collected tests from `138` test functions. The difference is 18 extra cases from five
parametrized tests: the five protected routes with no header (5), six malformed `Authorization`
headers (6), the two `OPTIONS` routes (2), seven invalid task bodies (7), and three methods against an
id SQLite cannot store (3).

| Layer | Module | Collected | Why it sits there |
|---|---|---|---|
| Unit | `test_seguridad.py` | 12 | Hashing and JWT with no app and no HTTP |
| Unit (DAO) | `test_db.py` | 8 | SQL against a connection; invisible from above |
| Integration | `test_registro.py` | 22 | Flask `test_client`, in-memory DB |
| Integration | `test_login.py` | 13 | Same |
| Integration | `test_autorizacion.py` | 24 | Same, parametrized over the five CRUD routes |
| Integration | `test_tareas.py` | 42 | Same |
| Integration | `test_errores.py` | 4 | Same, plus `monkeypatch` for the forced 500 |
| Integration | `test_bienvenida.py` | 3 | Same |
| Integration | `test_encoding.py` | 1 | Same |
| E2E (in-process) | `test_cliente.py` | 22 | The real client against the real app, no port opened |
| Infrastructure | `test_infraestructura.py` | 5 | Verifies the fixtures themselves |

The shape is a pyramid, not an inverted one: **20 unit · 109 integration · 22 end-to-end**. The
E2E layer is the smallest and the slowest, and it exercises the one component that has no other way
of being tested — the console client, whose exit codes and single-line error output are the
deliverable.

---

## 2. Forward matrix

`Where` names the module; the reverse matrix in §3 names the exact test function for each case.
`Result` is the suite result at `8c9a4f3`: every row is `PASS`.

### 2.1 Functional requirements

| Req | TP | Cases | Where | Result |
|---|---|---|---|---|
| RF-01 | TP-02 | TC-REG-01 … 06, 10, 11, 16 | `test_registro.py` | PASS |
| RF-02 | TP-04 | TC-DB-06 | `test_registro.py` | PASS |
| RF-03 | TP-03, TP-19 | TC-REG-09, TC-REG-12, TC-DB-03, TC-DB-04 | `test_registro.py`, `test_db.py` | PASS |
| RF-04 | TP-05 | TC-REG-13, TC-TOK-06 | `test_registro.py`, `test_seguridad.py` | PASS |
| RF-05 | TP-06 | TC-LOG-01 | `test_login.py` | PASS |
| RF-06 | TP-07 | TC-LOG-02, TC-LOG-03, TC-LOG-04 | `test_login.py` | PASS |
| RF-07 | TP-08, TP-09 | TC-TOK-01, TC-TOK-02, TC-TOK-06 | `test_seguridad.py`, `test_login.py` | PASS |
| RF-08 | TP-08, TP-09, TP-10 | TC-AUT-01 … 06, TC-TOK-02 … 05 | `test_autorizacion.py`, `test_seguridad.py` | PASS |
| RF-09 | TP-21 | TC-HTML-01, TC-HTML-02 | `test_bienvenida.py` | PASS |
| RF-10 | TP-13, TP-17, TP-21 | TC-TAR-01 … 04, TC-TAR-19, TC-E2E-01 | `test_tareas.py`, `test_cliente.py` | PASS |
| RF-11 | TP-11 | TC-TAR-16, TC-DB-07 | `test_tareas.py`, `test_db.py` | PASS |
| RF-12 | TP-11 | TC-TAR-13, TC-TAR-14, TC-TAR-15 | `test_tareas.py` | PASS |
| RF-13 | TP-12 | TC-TAR-05 … 12 | `test_tareas.py` | PASS |
| RF-14 | TP-01, TP-16, TP-22 | TC-ERR-01 … 05, TC-REG-15, TC-LOG-09, TC-AUT-06, TC-TAR-18 | `test_errores.py`, `test_registro.py`, `test_login.py`, `test_autorizacion.py`, `test_tareas.py` | PASS |
| RF-15 | TP-18 | TC-REG-07, TC-REG-14, TC-LOG-05 | `test_registro.py`, `test_login.py` | PASS |
| RF-16 | TP-17, TP-25 | TC-E2E-01, TC-CLI-01 | `test_cliente.py` | PASS |
| RF-17 | TP-17 | TC-E2E-02, TC-E2E-03, TC-E2E-07, TC-E2E-08, TC-E2E-10 | `test_cliente.py` | PASS |

### 2.2 Non-functional requirements

| Req | TP | Cases and evidence | Where | Result |
|---|---|---|---|---|
| RNF-01 | TP-04, TP-05 | TC-SEG-01 … 03, TC-REG-13, TC-DB-06, TC-TOK-06 | `test_seguridad.py`, `test_registro.py` | PASS |
| RNF-02 | TP-15 | TC-DB-01 … 09, plus a review of `requirements.txt` and `db.py` (no DB server anywhere) | `test_db.py` | PASS |
| RNF-03 | — | TC-SEG-04, TC-SEG-05, `test_la_app_falla_sin_secret_key`, and the history scan in §6 | `test_seguridad.py`, `test_infraestructura.py` | PASS |
| RNF-04 | TP-01, TP-22 | TC-ERR-02 … 04, TC-REG-15, TC-LOG-09, TC-AUT-06, TC-TAR-04 | see §3 | PASS |
| RNF-05 | TP-14 | TC-DB-05, `test_registro_no_interpreta_sql_del_usuario`, `test_el_titulo_con_sql_se_guarda_como_texto`, plus a review of every statement | `test_db.py`, `test_registro.py`, `test_tareas.py` | PASS |
| RNF-06 | TP-16 | TC-ERR-01, TC-REG-13, TC-TOK-06, TC-LOG-04, all-401-identical | `test_errores.py`, `test_registro.py`, `test_seguridad.py`, `test_login.py`, `test_autorizacion.py` | PASS |
| RNF-07 | TP-20 | TC-DB-01, TC-DB-02, TC-DB-09 | `test_db.py` | PASS |
| RNF-08 | TP-08 | TC-TOK-03, TC-TOK-04 | `test_seguridad.py` | PASS |
| RNF-09 | TP-09 | TC-TOK-05, TC-AUT-05, `test_token_expirado_devuelve_401` | `test_seguridad.py`, `test_autorizacion.py` | PASS |
| RNF-10 | TP-23 | TC-ENC-01, TC-E2E-09 | `test_encoding.py`, `test_cliente.py` | PASS |
| RNF-11 | — | Module review against the SRP mapping; no test can assert a layering decision | §4 | PASS (review) |
| RNF-12 | — | `test_la_base_de_los_tests_esta_en_memoria`, `test_la_suite_no_toca_la_base_real` | `test_infraestructura.py` | PASS |
| RNF-13 | — | Clean-clone walkthrough | Phase 10.3 | **PENDING** |
| RNF-14 | — | Artifact review: docs in English, code and tests in Spanish | §4 | PASS (review) |
| RNF-15 | — | Review of `requirements.txt`, one line per dependency with its reason | §4 | PASS (review) |
| RNF-16 | TP-15 | Review of the deployed run command (single worker, threads) | Phase 11 | **PENDING** |

### 2.3 Every test point is reached

The 25 test points from `docs/casos-de-prueba.md` §2, with the cases that reach them and where they
run:

| TP | Cases | Layer |
|---|---|---|
| TP-01 | TC-REG-15, TC-LOG-09, TC-AUT-06, TC-ERR-04, TC-HTML-03, TC-TAR-18 | HTTP |
| TP-02 | TC-REG-01 … 06, 10, 11, 16, TC-LOG-07, TC-LOG-08 | HTTP |
| TP-03 | TC-REG-12, TC-DB-03 | HTTP + DAO |
| TP-04 | TC-SEG-01 … 05, TC-DB-06 | unit + DAO |
| TP-05 | TC-REG-13, TC-TOK-06 | HTTP + unit |
| TP-06 | TC-LOG-01 | HTTP |
| TP-07 | TC-LOG-02 … 04 | HTTP |
| TP-08 | TC-TOK-01 … 04, TC-AUT-05 | unit + HTTP |
| TP-09 | TC-TOK-05, TC-AUT-05 | unit + HTTP |
| TP-10 | TC-AUT-01 … 03 | HTTP |
| TP-11 | TC-TAR-13 … 17, TC-DB-07 | HTTP + DAO |
| TP-12 | TC-TAR-05 … 12 | HTTP |
| TP-13 | TC-TAR-01 … 04, TC-TAR-19 | HTTP |
| TP-14 | TC-DB-05, TC-ERR-05 | DAO + HTTP |
| TP-15 | TC-DB-08 | DAO (deployment half: Phase 11) |
| TP-16 | TC-ERR-01 | HTTP |
| TP-17 | TC-E2E-01 … 05, 07, 08, 10, 11, 12 | E2E |
| TP-18 | TC-REG-07, TC-REG-14, TC-LOG-05 | HTTP |
| TP-19 | TC-REG-09, TC-DB-04 | HTTP + DAO |
| TP-20 | TC-DB-01, TC-DB-02, TC-DB-09 | DAO |
| TP-21 | TC-HTML-01, TC-HTML-02, TC-AUT-04 | HTTP |
| TP-22 | TC-ERR-02 … 04 | HTTP |
| TP-23 | TC-ENC-01, TC-E2E-09 | E2E |
| TP-24 | TC-REG-08, TC-LOG-06 | HTTP |
| TP-25 | TC-E2E-06, TC-CLI-01 | E2E |

---

## 3. Reverse matrix

Every executed test function, the case it implements and the requirement behind it. Test names are
quoted exactly as `pytest` reports them.

### 3.1 `tests/test_registro.py` — 22 tests

| Test | Case | Req |
|---|---|---|
| `test_registro_valido_devuelve_201_y_el_usuario` | TC-REG-01 | RF-01 |
| `test_registro_sin_contrasena_devuelve_400` | TC-REG-02 | RF-01 |
| `test_registro_sin_usuario_devuelve_400` | TC-REG-03 | RF-01 |
| `test_registro_con_usuario_no_texto_devuelve_400` | TC-REG-04 | RF-01 |
| `test_registro_con_contrasena_nula_devuelve_400` | TC-REG-05 | RF-01 |
| `test_registro_con_usuario_vacio_devuelve_400` | TC-REG-06 | RF-01 revisada |
| `test_registro_con_usuario_de_solo_espacios_devuelve_400` | TC-REG-11 | RF-01 revisada, D-21 |
| `test_registro_con_contrasena_vacia_devuelve_400` | TC-REG-16 | D-14, TP-24 |
| `test_registro_recorta_espacios_del_usuario` | TC-REG-10 | RF-01, D-21 |
| `test_registro_no_recorta_la_contrasena` | TC-REG-10 (counterpart) | D-21 |
| `test_registro_con_content_type_erroneo_devuelve_400` | TC-REG-07 | RF-15 |
| `test_registro_sin_content_type_devuelve_400` | TC-REG-07 | RF-15 |
| `test_registro_con_json_truncado_devuelve_400` | TC-REG-14 | RF-15 |
| `test_registro_con_json_que_no_es_objeto_devuelve_400` | — (extra) | RF-15 |
| `test_registro_acepta_la_contrasena_1234_del_enunciado` | TC-REG-08 | TP-24 |
| `test_registro_duplicado_devuelve_409` | TC-REG-12 | RF-03 |
| `test_registro_duplicado_con_otra_capitalizacion_devuelve_409` | TC-REG-09 | RF-03, TP-19 |
| `test_registro_no_devuelve_el_hash_ni_la_contrasena` | TC-REG-13 | RF-04, RNF-06 |
| `test_registro_guarda_la_contrasena_hasheada` | TC-DB-06 | RF-02, RNF-01 |
| `test_registro_no_interpreta_sql_del_usuario` | — (extra) | RNF-05 |
| `test_get_registro_devuelve_405` | TC-REG-15 | TP-01, RF-14 |
| `test_put_registro_devuelve_405` | TC-REG-15 | TP-01, RF-14 |

### 3.2 `tests/test_login.py` — 13 tests

| Test | Case | Req |
|---|---|---|
| `test_login_valido_devuelve_200_con_el_token` | TC-LOG-01 | RF-05 |
| `test_login_con_contrasena_incorrecta_devuelve_401` | TC-LOG-02 | RF-06 |
| `test_login_con_usuario_inexistente_devuelve_401` | TC-LOG-03 | RF-06 |
| `test_los_dos_401_son_byte_a_byte_identicos` | TC-LOG-04 | RF-06, D-29 |
| `test_login_acepta_la_contrasena_1234_del_enunciado` | TC-LOG-06 | TP-24 |
| `test_login_no_recorta_la_contrasena` | TC-LOG-07 | D-21 |
| `test_login_con_json_malformado_devuelve_400` | TC-LOG-05 | RF-15 |
| `test_login_sin_contrasena_devuelve_400` | TC-LOG-08 | RF-01 (login side) |
| `test_login_con_contrasena_vacia_devuelve_400` | — (extra) | RF-01, D-14 |
| `test_login_con_usuario_vacio_devuelve_400` | — (extra) | RF-01 revisada |
| `test_login_con_usuario_no_texto_devuelve_400` | — (extra) | RF-01 |
| `test_get_login_devuelve_405` | TC-LOG-09 | TP-01 |
| `test_el_token_lleva_el_id_del_usuario_y_no_lleva_credenciales` | TC-TOK-01, TC-TOK-06 | RF-07, RNF-01 |

### 3.3 `tests/test_seguridad.py` — 12 tests

| Test | Case | Req |
|---|---|---|
| `test_hashear_password_no_es_texto_plano` | TC-SEG-01 | RF-02, RNF-01 |
| `test_hashear_password_dos_hashes_distintos` | TC-SEG-02 | RNF-01 |
| `test_verificar_password_correcta_e_incorrecta` | TC-SEG-03 | RNF-01 |
| `test_firmar_sin_secret_key_falla_rapido` | TC-SEG-04 | RNF-03 |
| `test_sin_clave_explicita_usa_la_del_entorno` | TC-SEG-05 | RNF-03 |
| `test_token_propio_decodifica_y_trae_sub` | TC-TOK-01 | RF-07 |
| `test_token_firma_alterada_falla` | TC-TOK-02 | RF-08 |
| `test_token_otra_clave_falla` | TC-TOK-03 | RF-08, RNF-08 |
| `test_token_alg_none_falla` | TC-TOK-04 | RNF-08 |
| `test_token_expirado_falla` | TC-TOK-05 | RNF-09 |
| `test_el_token_expira_a_las_ocho_horas` | TC-TOK-01 | RF-07, D-20 |
| `test_payload_no_filtra_password_ni_hash` | TC-TOK-06 | RF-04, RNF-06 |

### 3.4 `tests/test_autorizacion.py` — 24 tests (14 functions)

| Test | Case | Req |
|---|---|---|
| `test_sin_token_todos_los_endpoints_devuelven_401` | TC-AUT-01, TC-AUT-02 | RF-08, TP-10 |
| `test_esquema_o_token_ausente_devuelve_401` | TC-AUT-03 | RF-08 |
| `test_token_alterado_devuelve_401` | TC-TOK-02 | RF-08 |
| `test_token_expirado_devuelve_401` | TC-TOK-05 | RF-08, RNF-09 |
| `test_token_firmado_con_otra_clave_devuelve_401` | TC-TOK-03 | RF-08 |
| `test_token_sin_claim_sub_devuelve_401` | — (extra) | RF-08 |
| `test_token_sin_claim_exp_devuelve_401` | TC-AUT-05 | RF-08, RNF-09, D-20 |
| `test_token_con_sub_que_no_es_entero_devuelve_401` | — (extra) | RF-08 |
| `test_todos_los_401_son_byte_a_byte_identicos` | — (extra) | RF-14, RNF-06 |
| `test_el_token_no_se_acepta_por_query_string` | — (extra) | RF-08 |
| `test_el_token_no_se_acepta_por_cookie` | — (extra) | RF-08 |
| `test_options_devuelve_405_en_json` | TC-AUT-06 | TP-01, RF-14 |
| `test_el_esquema_bearer_es_case_insensitive` | TC-AUT-03 | RF-08 |
| `test_token_valido_entra_y_devuelve_la_lista_vacia` | TC-AUT-03 (happy path) | RF-08, RF-10 |

### 3.5 `tests/test_tareas.py` — 42 tests (34 functions)

| Test | Case | Req |
|---|---|---|
| `test_crear_tarea_devuelve_201_con_el_recurso` | TC-TAR-01 | RF-10 |
| `test_crear_tarea_con_completada_true_la_persiste` | TC-TAR-01 | RF-10 |
| `test_crear_tarea_recorta_el_titulo` | TC-TAR-12 | RF-13 revisada |
| `test_crear_tarea_invalida_devuelve_400` | TC-TAR-05, TC-TAR-06, TC-TAR-07, TC-TAR-08, TC-TAR-10 | RF-13 |
| `test_crear_tarea_con_200_caracteres_entra` | TC-TAR-09 | RF-13, D-19 |
| `test_crear_tarea_con_completada_no_booleana_devuelve_400` | TC-TAR-11 | RF-13 |
| `test_crear_tarea_con_cuerpo_que_no_es_objeto_devuelve_400` | — (extra) | RF-15 |
| `test_crear_tarea_con_json_malformado_devuelve_400` | — (extra) | RF-15 |
| `test_crear_tarea_ignora_el_usuario_id_del_cuerpo` | TC-TAR-17 | RF-10, RF-11 |
| `test_la_respuesta_no_expone_el_dueno` | TC-TAR-01 | RF-10 |
| `test_listar_sin_tareas_devuelve_lista_vacia_y_200` | TC-TAR-03 | RF-10 |
| `test_listar_devuelve_las_tareas_en_orden_de_id` | — (extra) | RF-10 |
| `test_listar_no_devuelve_las_tareas_de_otro` | TC-TAR-16 | RF-11 |
| `test_obtener_la_propia_devuelve_200` | TC-TAR-02 | RF-10 |
| `test_obtener_inexistente_devuelve_404` | TC-ERR-02 | RF-14 |
| `test_obtener_un_id_no_numerico_devuelve_404` | — (extra) | RF-14 |
| `test_obtener_la_tarea_de_otro_devuelve_404` | TC-TAR-13 | RF-12 |
| `test_editar_la_propia_devuelve_200_con_el_recurso_completo` | TC-TAR-02 | RF-10 |
| `test_editar_persiste_el_cambio` | TC-TAR-02 | RF-10 |
| `test_editar_inexistente_devuelve_404` | TC-ERR-02 | RF-14 |
| `test_editar_con_titulo_invalido_devuelve_400` | TC-TAR-05, TC-TAR-06, TC-TAR-07, TC-TAR-08, TC-TAR-09, TC-TAR-10, TC-TAR-11 (PUT) | RF-13 |
| `test_editar_la_tarea_de_otro_devuelve_404` | TC-TAR-14 | RF-12 |
| `test_editar_la_tarea_de_otro_no_la_modifica` | TC-TAR-14 | RF-12 |
| `test_borrar_la_propia_devuelve_204_sin_cuerpo` | TC-TAR-04 | RF-10, D-23 |
| `test_borrar_deja_de_existir` | TC-TAR-02 | RF-10 |
| `test_borrar_la_misma_dos_veces_devuelve_404_la_segunda` | TC-ERR-02 | RF-14 |
| `test_borrar_inexistente_devuelve_404` | TC-ERR-02 | RF-14 |
| `test_borrar_la_tarea_de_otro_devuelve_404` | TC-TAR-15 | RF-12 |
| `test_borrar_la_tarea_de_otro_no_la_borra` | TC-TAR-15 | RF-12 |
| `test_delete_a_la_coleccion_devuelve_405` | — (extra) | TP-01, RF-14 |
| `test_post_a_un_id_devuelve_405` | — (extra) | TP-01, RF-14 |
| `test_patch_a_un_id_devuelve_405` | TC-TAR-18 | TP-01, RF-14 |
| `test_id_fuera_del_rango_de_sqlite_devuelve_404` | TC-TAR-19 | RF-14 |
| `test_el_titulo_con_sql_se_guarda_como_texto` | — (extra) | RNF-05 |

### 3.6 `tests/test_errores.py` — 4 tests

| Test | Case | Req |
|---|---|---|
| `test_ruta_inexistente_devuelve_404_json` | TC-ERR-03 | RF-14, TP-22 |
| `test_metodo_no_permitido_devuelve_405_json` | TC-ERR-04 | RF-14, TP-22 |
| `test_metodo_no_permitido_informa_los_metodos_validos` | TC-ERR-04 | RF-14 |
| `test_error_no_controlado_devuelve_500_json_sin_traceback` | TC-ERR-01 | RF-14, RNF-06 |

`TC-ERR-05` is not a test of its own: it is the `_error()` helper each module uses to assert that
the body has exactly one key, `error`, and that the content type is JSON. It is reused by
`test_registro.py`, `test_login.py`, `test_tareas.py` and `test_autorizacion.py` — one error shape,
checked everywhere it is produced.

### 3.7 `tests/test_db.py` — 8 tests

| Test | Case | Req |
|---|---|---|
| `test_tarea_con_usuario_inexistente_falla_por_fk` | TC-DB-01 | RNF-07 |
| `test_borrar_usuario_cascada_a_sus_tareas` | TC-DB-02 | RNF-07 |
| `test_usuario_duplicado_falla_por_unique` | TC-DB-03 | RF-03 |
| `test_usuario_duplicado_case_insensitive` | TC-DB-04 | RF-03, TP-19 |
| `test_inyeccion_sql_se_almacena_literal` | TC-DB-05 | RNF-05 |
| `test_listar_tareas_aislado_por_usuario` | TC-DB-07 | RF-11 |
| `test_concurrencia_sin_corrupcion` | TC-DB-08 | TP-15 |
| `test_la_base_en_archivo_se_crea_y_persiste_entre_peticiones` | TC-DB-09 | RNF-07, D-18 |

`TC-DB-06` is the one persistence case that lives in another module: the only way to read
`password_hash` is to register through the API and then look at the table, so it is
`test_registro_guarda_la_contrasena_hasheada` in §3.1.

### 3.8 `tests/test_bienvenida.py` — 3 tests

| Test | Case | Req |
|---|---|---|
| `test_la_bienvenida_es_publica_y_responde_html` | TC-HTML-01, TC-AUT-04 | RF-09 |
| `test_la_bienvenida_no_cambia_cuando_la_base_tiene_datos` | TC-HTML-02 | RF-09 |
| `test_post_sobre_la_bienvenida_da_405` | TC-HTML-03 | TP-01 |

### 3.9 `tests/test_encoding.py` — 1 test

| Test | Case | Req |
|---|---|---|
| `test_los_bytes_de_la_respuesta_son_utf8_y_no_escapes` | TC-ENC-01 | RNF-10 |

### 3.10 `tests/test_cliente.py` — 22 tests

| Test | Case | Req |
|---|---|---|
| `test_ciclo_completo_de_registro_login_crud_por_el_cliente` | TC-E2E-01 | RF-16 |
| `test_el_cliente_manda_los_nombres_de_campo_del_contrato` | TC-E2E-04 | RF-16 |
| `test_el_login_lee_el_token_y_lo_usa_como_bearer` | TC-E2E-04 | RF-07, RF-16 |
| `test_todas_las_llamadas_llevan_timeout_explicito` | TC-E2E-05 | RF-17 |
| `test_api_caida_se_traduce_en_un_error_de_red` | TC-E2E-02 | RF-17 |
| `test_api_caida_imprime_una_linea_y_sale_con_codigo_distinto_de_cero` | TC-E2E-02 | RF-17 |
| `test_un_error_sin_cuerpo_json_da_un_mensaje_honesto` | TC-E2E-10 | RF-17 |
| `test_un_json_sin_campo_error_no_se_inventa_un_mensaje` | TC-E2E-10 | RF-17 |
| `test_400_y_401_dan_una_linea_con_el_status_y_el_error_de_la_api` | TC-E2E-03 | RF-17 |
| `test_un_401_en_el_menu_imprime_el_status_y_el_error` | TC-E2E-03 | RF-17 |
| `test_401_con_token_vencido_borra_el_token_local_y_pide_reingresar` | TC-E2E-06 | RF-17, TP-25 |
| `test_un_login_fallido_no_borra_el_token_de_la_sesion_vigente` | TC-E2E-06 (counterpart) | RF-17 |
| `test_cerrar_sesion_no_revoca_el_token_en_el_servidor` | TC-CLI-01 | TP-25, D-17 |
| `test_la_contrasena_con_enie_sobrevive_el_viaje_de_ida_y_vuelta` | TC-E2E-09 | RNF-10 |
| `test_principal_fuerza_utf8_en_la_salida` | TC-E2E-09 | RNF-10 |
| `test_principal_usa_la_url_del_entorno` | TC-E2E-11 | RF-17 |
| `test_el_menu_recorre_el_ciclo_completo_y_sale_con_cero` | TC-E2E-01, TC-E2E-07 | RF-16 |
| `test_una_operacion_de_tareas_sin_sesion_avisa_y_no_llama_a_la_api` | TC-E2E-12 | RF-16 |
| `test_crear_editar_y_borrar_sin_sesion_tampoco_llaman_a_la_api` | TC-E2E-12 | RF-16 |
| `test_un_id_que_no_es_numero_avisa_sin_traceback` | TC-E2E-08 | RF-17 |
| `test_una_opcion_fuera_del_menu_no_termina_la_sesion` | TC-E2E-08 | RF-17 |
| `test_una_completada_que_no_es_s_ni_n_avisa_sin_traceback` | TC-E2E-08 | RF-17 |

### 3.11 `tests/test_infraestructura.py` — 5 tests

| Test | Case | Req |
|---|---|---|
| `test_el_cliente_responde` | — (infrastructure) | RNF-12 |
| `test_la_base_de_los_tests_esta_en_memoria` | — (infrastructure) | RNF-12 |
| `test_la_suite_no_toca_la_base_real` | — (infrastructure) | RNF-12 |
| `test_dos_apps_no_comparten_configuracion` | — (infrastructure) | RNF-12 |
| `test_la_app_falla_sin_secret_key` | — (infrastructure) | RNF-03 |

---

## 4. Requirements verified outside the automated suite

These are not gaps in the matrix: they are properties no unit test can observe, each with a named
verification that is part of the delivery.

| Req | Why it is not a test | Where it is verified | Status |
|---|---|---|---|
| RNF-02 | "No external DB server" is the absence of a dependency and a service, not a behaviour | `requirements.txt` + `db.py` review | PASS (review) |
| RNF-03 | A secret leak is a property of the **history**, not of a running program | §6 of this document | PASS |
| RNF-11 | A layering rule is a property of the source, not of a running request | Module review: one responsibility per module, no function mixes HTTP with SQL or hashing | PASS (review) |
| RNF-13 | Reproducibility is a property of a clean clone | Phase 10.3 walkthrough, with `README.md` | **PENDING (Phase 10)** |
| RNF-14 | Language convention | Artifact review: docs English, code/tests Spanish | PASS (review) |
| RNF-15 | Every dependency justified | `requirements.txt` review, one line per entry | PASS (review) |
| RNF-16 | Single worker with threads is a property of the deployed command | Phase 11 deployment evidence | **PENDING (Phase 11)** |

Deliverables, for completeness — they are hand-in items, not system behaviour:

| DEL | Status |
|---|---|
| DEL-01 `servidor.py` runnable entry point | PASS |
| DEL-02 console client | PASS |
| DEL-03 `README.md` | **PENDING (Phase 10.1)** |
| DEL-04 screenshots E-01 … E-08 | **PENDING (Phase 10)** |
| DEL-05 repository published on GitHub | **PENDING (Phase 10.4)** — the remote exists but is 34 commits behind `HEAD` |
| DEL-06 GitHub Pages site | **PENDING (Phase 10)** |
| DEL-07 written conceptual answers | **PENDING (Phase 10)** |
| DEL-08 working API on a public Python runtime | **PENDING (Phase 11)** |

---

## 5. What the catalogue and the suite did not line up

A matrix compares two lists that were built at different times, so it finds differences in both
directions: tests the catalogue never enumerated, and cases the suite never implemented. Both are
recorded here, because "the suite is green" answers neither question.

### 5.1 Tests that go beyond the catalogue

The reverse matrix flagged tests marked `(extra)`: they assert a rule that a requirement already
states, but the catalogue never enumerated them as cases. None of them is an orphan, and none
demands a new requirement — they are assertions that cost three lines once the fixture exists and
that pin behaviour a reader would otherwise have to take on trust.

| Test | Rule it pins |
|---|---|
| `test_registro_con_json_que_no_es_objeto_devuelve_400` | A JSON array or scalar body is not a valid registration body (RF-15) |
| `test_registro_no_interpreta_sql_del_usuario` | The injection case at the HTTP layer, not only at the DAO (RNF-05) |
| `test_el_titulo_con_sql_se_guarda_como_texto` | Same, for `titulo` (RNF-05) |
| `test_login_con_*_devuelve_400` | The login endpoint applies the same presence/type rules as registration (RF-01) |
| `test_token_sin_claim_sub_devuelve_401`, `test_token_con_sub_que_no_es_entero_devuelve_401` | A token without a usable `sub` is not a session (RF-08) |
| `test_todos_los_401_son_byte_a_byte_identicos` | One error shape at the authentication boundary (RF-14) |
| `test_el_token_no_se_acepta_por_query_string`, `test_el_token_no_se_acepta_por_cookie` | The token travels in the header only (RF-08) |
| `test_obtener_un_id_no_numerico_devuelve_404` | A path segment that is not an id cannot name a resource (RF-14) |
| `test_delete_a_la_coleccion_devuelve_405`, `test_post_a_un_id_devuelve_405` | The method table is closed (TP-01) |
| `test_listar_devuelve_las_tareas_en_orden_de_id` | Stable ordering, so the client's list is not arbitrary (RF-10) |
| `test_metodo_no_permitido_informa_los_metodos_validos` | RFC 7231 §6.5.5: a `405` carries `Allow` (RF-14) |
| `test_un_login_fallido_no_borra_el_token_de_la_sesion_vigente` | A `401` from `/login` is about credentials, not about the token (RF-17) |
| `test_dos_apps_no_comparten_configuracion`, `test_el_cliente_responde` | The fixtures isolate state; every later test depends on it (RNF-12) |

### 5.2 Defects this matrix found that the suite could not

A green suite says the tests that exist pass. It says nothing about the tests that are missing, the
comments that lie, or the cases that were catalogued and never written. Building the two matrices
surfaced four problems, none of which a coverage report or a green bar would have shown:

1. **`tests/test_bienvenida.py` did not exist.** The catalogue had assigned `TC-HTML-01 … 03` to it
   since Phase 1.6, and `RF-09` had no executable evidence at all. Fixed in Phase 9.1.
2. **`TC-TAR-18` had no test.** The catalogue specifies `PATCH /api/tareas/1 → 405`, and §2.3 claimed
   `TP-01` was fully reached, which was false. The test was written in this phase
   (`test_patch_a_un_id_devuelve_405`). It passed on the first run, without touching production code:
   the behaviour was already correct, so what was missing was the assertion, not the implementation.
   **There was no RED step here, and claiming one would be a lie** — the gap was in the suite, not in
   the code. The suite went from 155 to 156.
3. **The comment above `test_el_token_no_se_acepta_por_query_string` cited `TC-AUT-04`**, but the
   catalogue assigns `TC-AUT-04` to the public welcome route. The test is extra coverage for `RF-08`
   and the comment now says so. The same case was missing from the reverse matrix and is now
   attached to `test_la_bienvenida_es_publica_y_responde_html`, which is the test that actually
   reaches it.
4. **`TC-AUT-02` was collapsed into `TC-AUT-01`.** They are two cases — one route with no header, and
   the five-route sweep — covered by the same parametrized test. Both are now named on it.

The lesson is the one this document exists for: **traceability catches what coverage cannot.**

---

## 6. RNF-03 / Phase 9.4 — secret scan of the whole history

**Why the history and not just the working tree.** A committed secret stays recoverable forever: a
clone, a `git log -p` or a GitHub search reaches it even after the next commit deletes the file.
Scanning the tree only proves the tree is clean today.

**Method.** The 34 revisions reachable from any ref at `8c9a4f3` were dumped once
(`git log -p --all --unified=0`, 412 KB) and searched with .NET regexes through `Select-String`.
`git grep` was tried first and abandoned: on this Git for Windows build it silently misses some
multi-alternative patterns, so a "no matches" result from it was not evidence of anything.

| Pattern | Matches |
|---|---|
| `ghp_[A-Za-z0-9]{20,}` (classic GitHub token) | 0 |
| `github_pat_[A-Za-z0-9_]{20,}` (fine-grained token) | 0 |
| `AKIA[0-9A-Z]{16}` (AWS key id) | 0 |
| `BEGIN (RSA \| EC \| OPENSSH )?PRIVATE KEY` | 0 |
| `SECRET_KEY\s*=\s*"[^"$]{6,}` | 5 — see below |
| `SECRET_KEY\s*=\s*[A-Za-z0-9_\-]{16,}` | 1 — the `.env.example` placeholder |
| `password\s*=\s*"[^"]{6,}"` | 0 |
| `eyJhbGciOi` (JWT header) | 2 — truncated examples in `docs/api.md` |

Every match, with its verdict:

| Match | Verdict |
|---|---|
| `SECRET_KEY = "clave-solo-para-tests"` and its successor `…-de-32-bytes-o-mas` in `config.py` | Intentional: the test configuration's key. It protects nothing — it signs tokens inside a test process |
| `SECRET_KEY = "otra-clave-de-tests-distinta-…"` in `tests/test_infraestructura.py` | Intentional: proves two apps do not share configuration |
| `#   $env:SECRET_KEY = "a long random value"` in `.env.example` | A comment showing how to set the variable |
| `SECRET_KEY=replace-me-with-a-generated-value` in `.env.example` | A placeholder, not a value |
| `eyJhbGciOiJIUzI1NiIs…` in `docs/api.md` | Two truncated JWT examples in the endpoint documentation; the signature is cut off, nothing decodes |

**Positive control.** The scan was re-run with the test key as the pattern and returned the expected
lines. A scan that reports zero without a control cannot distinguish "clean history" from "broken
pattern", and the `git grep` behaviour above is exactly how that failure looks.

**File-level check.** `git log --all --diff-filter=A --name-only` over every added path: `.env`,
`*.db` and `*.sqlite` never entered the repository. The only `.env` file ever added is
`.env.example`. No blob in the history exceeds 50 KB, so there is no accidentally committed
database or binary in it.

**Residual note, stated honestly.** The published default branch (`origin/main`, `ec11e10`)
predates the last 34 commits and still contains files that `HEAD` no longer tracks. The history was
deliberately **not** rewritten: rewriting a published branch is a destructive operation with a
collaboration cost, and the decision was to correct the tree going forward rather than to erase the
past. So the property "the repository contains only the deliverable" holds for `HEAD` and for every
commit after `ec11e10` — not retroactively.

---

## 7. Residual risk

Carried forward from `docs/matriz-de-riesgo.md` §5 and `docs/decisiones.md`, with the ones this
phase makes concrete.

| Risk | Impact | Why it is accepted | Where it is recorded |
|---|---|---|---|
| Login timing oracle | An attacker who can time `/login` learns whether a username exists | Closing it requires a decoy hash, which turns every failed login into ~200 ms of scrypt work with no rate limiting in scope. Measured: ~296× ratio, no overlap. Documented, not hidden | D-29 |
| No server-side token revocation | A stolen token stays valid until it expires (8 h) | Declared non-goal (D-17). Logout is client-side by design and the limitation is pinned by TC-CLI-01 | D-17, TP-25 |
| No rate limiting | Credential brute force is only bounded by password entropy (which D-14 leaves at "non-empty") | Out of scope per `AGENTS.md` YAGNI; adding it would be scope expansion not demanded by a requirement | D-14, D-17 |
| SQLite on a free host | If the hosting filesystem is ephemeral, the database resets on redeploy | Handled in Phase 11 (D-08): the deployment is chosen and its persistence is verified, not assumed | D-08 |
| Single worker is a deployment rule | Running two processes against one SQLite file reintroduces `database is locked` | RNF-16 is enforced by the run command, not by the code. Phase 11 must show the command | RNF-16 |
| No password policy | `1234` is a valid password | Deliberate: the brief's own example must keep working (TP-24) | D-14 |

---

## 8. Release verdict — Phase 9.3

**Scope of the verdict: the software at commit `8c9a4f3`, not the assignment submission.** The two
are different objects, and conflating them is how a green suite gets mistaken for a finished
deliverable.

### PASS on what this phase set out to close

| Claim | Evidence |
|---|---|
| Every functional requirement reaches at least one executed test | §2.1 — 17 of 17 |
| Every test point is reached | §2.3 — 25 of 25 |
| Every test names the requirement it serves | §3 — 138 functions, no orphan |
| The suite is green | 156 passed |
| The uncovered lines are justified, not forgotten | 2 of 431, both `__main__` entry points |
| No secret was ever committed | §6 — 34 revisions, 0 real findings |
| The 92 catalogued cases exist and run | `docs/casos-de-prueba.md` §3 vs. §3 of this document |

### CONDITIONAL on the deliverables

The verdict is **CONDITIONAL**, not PASS, because a requirement verified in code is not a
requirement delivered. Three items have no evidence yet, and none of them is blocked by a defect:

1. **RNF-13 and DEL-03** — there is no `README.md` and therefore no clean-clone walkthrough. A
   project that only its author can run is not reproducible.
2. **RNF-16 and DEL-08** — the deployment does not exist yet, so "single worker with threads" and
   "persistent SQLite on the host" are design intentions.
3. **DEL-04 … DEL-07** — screenshots, the published repository state, the Pages site and the
   written conceptual answers.

It is not FAIL: nothing in the code is known to be broken, every requirement is verified or has a
named pending verification, and the residual risks in §7 are deliberate and documented.

**Conditions to close:** Phase 10 (documentation, evidence, publication) and Phase 11 (deployment
with its smoke test and the single-worker evidence). The two `PENDING` requirement rows in §2.2 are
the gate.

### Superseded by Phase 11

This verdict covers the software before deployment. **Phase 11 re-issues it** with the deployment
evidence in place: it either confirms PASS, or returns CONDITIONAL with a named blocker. Until
then, this is the `CONDITIONAL` recorded at the end of Phase 9.

---

## 9. Revisions

### 2026-11-10 — created (Phase 9.2)

- **Sources:** `docs/requisitos.md` (33 requirement rows + two revisions), `docs/casos-de-prueba.md`
  (92 cases, 25 test points), `docs/matriz-de-riesgo.md` (§2–§5), `docs/decisiones.md`
  (D-17, D-19 … D-23, D-29, D-30), and the suite itself at `8c9a4f3`.
- **No requirement was added and no case was invented.** Every row cites an ID that already existed
  in the repository.
- **Four defects found by building it, not by running the suite** (detail in §5.2):
  `tests/test_bienvenida.py` was named by the catalogue since Phase 1.6 and did not exist (fixed in
  Phase 9.1, TP-21); `TC-TAR-18` had no test at all (written in this phase, 155 → 156); one test
  comment cited `TC-AUT-04` for a case the catalogue assigns elsewhere (fixed in this phase); and
  `TC-AUT-02` was collapsed into `TC-AUT-01` in the reverse map. None of the four would have
  surfaced from a coverage report.
- **Final counts at close:** 156 collected tests from 138 functions, 92 catalogued cases, 2 uncovered
  lines of 431. The verdict is CONDITIONAL, and the reason is delivery, not code.
