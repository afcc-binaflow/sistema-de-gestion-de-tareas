# Respuestas conceptuales — PFO 2

Respuestas a las dos preguntas del enunciado. Cada afirmación está anclada en el
código de este repositorio, no en abstracto (Paso 12.2 del plan).

---

## 1. ¿Por qué hashear contraseñas?

Porque **guardar la contraseña en texto plano convierte cualquier filtración de la base en
una filtración de credenciales**. Con la contraseña hasheada, el atacante que obtiene la tabla
no obtiene contraseñas usables.

Tres propiedades del hashing que hacen que esto sea verdad en este proyecto:

1. **Irreversibilidad.** Un hash no se "desencripta": no existe la operación inversa que
   recupere la contraseña a partir del hash. `security.py` usa `generate_password_hash` /
   `check_password_hash` de Werkzeug (scrypt por defecto). Por eso `test_hashear_password_no_es_texto_plano`
   (TC-SEG-01) puede afirmar que el hash no es la contraseña, y por eso `TC-DB-06`
   (`test_registro_guarda_la_contrasena_hasheada`) verifica que la columna `password_hash` no
   contenga la contraseña original.

2. **Salt aleatorio.** Dos hashes de la misma contraseña son distintos, porque cada llamada
   genera un salt nuevo. `test_hashear_password_dos_hashes_distintos` (TC-SEG-02) lo verifica:
   si dos usuarios eligen la misma contraseña, sus hashes no coinciden, y un atacante no puede
   detectar contraseñas repetidas ni usar tablas precalculadas (rainbow tables). Eso es lo que
   diferencia un hash con salt de un hash "seco".

3. **Por qué no cifrado reversible.** Cifrar la contraseña con una clave reversible (AES, por
   ejemplo) requeriría guardar esa clave en el servidor. Si alguien filtra el servidor, filtra
   la clave y, con ella, todas las contraseñas. El hashing no tiene clave que filtrar: solo
   hay una función unidireccional. Por eso el enunciado pide "hashear", no "cifrar".

**Qué pasa si se filtra la tabla.** El atacante obtiene hashes, no contraseñas. Para recuperar
una contraseña tiene que probar candidatas una por una (ataque de diccionario o fuerza bruta
sobre el hash), lo cual es costoso por diseño con scrypt. Mientras tanto, las contraseñas de
los usuarios siguen siendo secretas y, como el token JWT no lleva la contraseña ni su hash
(TC-TOK-06, RNF-06), comprometer la base no compromete las sesiones activas.

---

## 2. Ventajas de usar SQLite en este proyecto

1. **Cero configuración.** SQLite viene en la biblioteca estándar de Python; no hay servidor
   que instalar, arrancar ni administrar. `db.py` abre la conexión con `sqlite3.connect(...)` y
   listo. Eso es lo que hace que el proyecto se pueda levantar con `python servidor.py` sin
   preparar nada.

2. **Todo en un archivo.** La base es un solo archivo (`instance/pfo2.db`, configurable con
   `DATABASE_PATH`). Se puede copiar, respaldar o borrar con un `rm`. No hay un servicio
   corriendo en segundo plano ni un puerto que abrir.

3. **Transaccional y ACID.** SQLite garantiza atomicidad, consistencia, aislamiento y
   durabilidad en cada transacción. `repository.py` aprovecha eso para que una escritura parcial
   no deje la base inconsistente, y `TC-DB-02` verifica que borrar un usuario borre en cascada
   sus tareas (integridad referencial, FK con `ON DELETE CASCADE`).

4. **Ideal para desarrollo, prototipos y baja concurrencia.** Es el motor correcto para este
   tamaño: un solo proceso, un solo archivo, sin infraestructura. Los tests usan `:memory:`
   (RNF-12) y corren en milisegundos sin tocar disco.

**La limitación, que también hay que conocer:**

- **Escrituras concurrentes.** Varios procesos escribiendo al mismo archivo producen
  `database is locked`. Por eso el deploy usa un solo worker con threads
  (`--workers 1 --threads 4`, RNF-16): no es un capricho, es un requisito de SQLite.
- **Filesystem efímero en el hosting.** En la mayoría de los hosts gratuitos el contenedor se
  recrea en cada deploy y el archivo SQLite se borra. La "persistencia en SQLite" deja de ser
  persistencia. PythonAnywhere conserva el filesystem en el plan gratuito; Render y Railway no.
  Documentarlo como limitación honesta es parte del entendimiento del motor (D-08).
