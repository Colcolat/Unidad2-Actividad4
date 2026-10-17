# Unidad II · Actividad 5: Configurar permisos con GraphQL

Sistema General de Ingresos (FastAPI, Strawberry GraphQL, SQLAlchemy y MySQL con Docker Compose). Continúa la actividad 4 y agrega tres funcionalidades sobre la relación rol-permiso:

1. **Catálogo filtrado** `permissionCatalog(actorCompanyUserId, resource)`: permisos activos, todos o de un recurso.
2. **Previsualización** `previewRolePermissions(input, actorCompanyUserId)`: compara la lista deseada con la activa sin modificar filas.
3. **Actualización completa** `setRolePermissions(input, actorCompanyUserId)`: deja exactamente la lista recibida en una sola transacción; repetirla devuelve `changed: false`.

La autenticación no cambia: `login` y el token siguen como en las actividades anteriores. `actorCompanyUserId` sigue siendo el dato de laboratorio para practicar la autorización con `exigir_permiso`; no autentica a nadie.

## Integrantes y aportaciones

Docente: Gimer Amilcar Cervera Evia · Fundamentos de Arquitectura de Software y Desarrollo Backend. Portada del equipo: [portada_equipo.pdf](portada_equipo.pdf).

| Integrante | Matrícula | Aportación |
|---|---|---|
| Angel Abraham Lugo Saenz | SW2409052 | _por completar_ |
| Juan Jose Zapata Buenfil | SW2509044 | _por completar_ |
| Josue Enmanuel Poot Mateo | SW2509033 | _por completar_ |
| Sergio Origion Huerta Martinez | SW2509012 | _por completar_ |
| Diego Ramirez Magaña | SW2509051 | _por completar_ |

## Qué cambió en el código

| Archivo | Cambio |
|---|---|
| `app/schema.py` | Enum `PermissionResource`, input `SetRolePermissionsInput`, tipos `RolePermissionPlan` y `RolePermissionUpdate`; consultas `permissionCatalog` y `previewRolePermissions`; mutación `setRolePermissions`. `Role` y `Permission` se reutilizan. |
| `app/rbac.py` | `plan_role_permissions` (valida y calcula, solo lee), compartida por la previsualización y la mutación; `apply_role_permission_plan` (escribe y hace `flush`, sin `commit`); `RESOURCE_PREFIXES`; `parse_id`. `seed_rbac` ahora solo carga la matriz si el rol no tiene **ninguna** fila, así una lista vacía aplicada a propósito no se repone al reiniciar. |
| `tests/test_e07_reversion.py` | Prueba E07 con `unittest`. |

No se agregaron tablas ni columnas: `role_permissions` ya tenía la restricción única `uq_role_permission (role_id, permission_id)`, así que no hace falta migración. Se conservan los cuatro roles, los diez permisos y la operación `permissions`.

### Permisos que exigen las operaciones nuevas

| Operación | Tipo | Permiso |
|---|---|---|
| `permissionCatalog` | query | `roles.read` |
| `previewRolePermissions` | query | `roles.read` |
| `setRolePermissions` | mutation | `roles.write` |

### Reglas de previsualizar y aplicar

El rol debe existir y estar activo; no puede ser ADMINISTRADOR (regla del laboratorio). Cada id debe ser válido, existir y ser un permiso activo. Los ids repetidos se rechazan (`"3"` y `3` son el mismo). `[]` es válida y desactiva todas las relaciones activas del rol. Una pareja inactiva se reactiva con el mismo id de relación. Si una regla falla, el campo raíz vuelve `null`, el motivo llega en `errors` y no cambia ninguna relación. Las listas de resultados se ordenan por `Permission.code`.

## Dependencias

Python 3.11 o superior, Docker (MySQL 8.4) y los paquetes de `requirements.txt`: fastapi, uvicorn, strawberry-graphql, sqlalchemy, pymysql, python-dotenv, pydantic, pwdlib[argon2] y pyjwt.

## Arranque de MySQL y de la API

```bash
docker compose up -d
```

Si el contenedor `actividad4_mysql` ya existe de las actividades anteriores: `docker start actividad4_mysql`.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Opcionalmente se crea un `.env` con `DATABASE_URL` y `SECRET_KEY` (sin subirlo al repositorio). Sin `.env` se usan los valores de `docker-compose.yml`.

GraphiQL queda en `http://127.0.0.1:8000/graphql`. Cliente de MySQL:

```bash
docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
```

## Preparar los datos y ejecutar los casos E01 a E10

Con la API activa, en otra terminal:

```bash
python documentacion/probar_actividad5.py
```

Crea una empresa nueva con Ana (ADMINISTRADOR) y María (CAPTURISTA), con una cuenta y un concepto, y ejecuta E01 a E08 con las operaciones de `operaciones.graphql`. Escribe en `variables/` el JSON real de cada operación con los id de **tu** base. Al terminar pide reiniciar la API (E08): se detiene `uvicorn` con Ctrl+C, se vuelve a arrancar y se ejecuta:

```bash
python documentacion/probar_actividad5.py --despues-reinicio
```

que termina E08 y ejecuta E09 y E10. Respuestas en `evidencias/actividad5/json/`, consultas SQL en `evidencias/actividad5/sql/`; `configuracion_final.json` se genera en E09. La explicación de cada caso está en [evidencias.md](evidencias.md).

El script parte de CAPTURISTA en S0 y lo deja otra vez en S0, así que se puede volver a correr.

## Tomar las capturas

Después de correr las dos partes de `probar_actividad5.py`, con la API activa:

```bash
pip install playwright        # solo para las capturas
python -m playwright install chromium
python documentacion/tomar_capturas_actividad5.py principal
# reiniciar uvicorn
python documentacion/tomar_capturas_actividad5.py reinicio
```

Ejecuta cada caso en GraphiQL con las operaciones de `operaciones.graphql` y las variables de `variables/`, y toma la salida real del cliente `mysql` del contenedor `actividad4_mysql`. Las imágenes quedan en `evidencias/actividad5/capturas/`. Si MySQL no corre en Docker, el cliente se indica con `MYSQL_CMD` (ver el encabezado del script).

## Correr la prueba E07

Con MySQL activo (la API no es necesaria):

```bash
python -m unittest -v tests.test_e07_reversion
```

o todas las pruebas con `python -m unittest discover -v`. La prueba crea su propia empresa con una administradora, reemplaza temporalmente con `mock.patch` la función que aplica el plan para que lance una excepción después del `flush` y antes del `commit`, y comprueba desde una sesión nueva que `role_permissions` quedó igual. Al terminar borra la empresa de prueba.

## Operaciones y variables

Todas están en `operaciones.graphql`. En GraphiQL se pega el archivo completo, se pegan las variables en el panel **Variables** y se elige la operación por nombre.

| Caso | Operación | Variables |
|---|---|---|
| E01 | `PuntoDePartida` | — |
| E01, E08 | `ListaDelRol` | `variables/E01_lista_capturista.json` |
| E02 | `ExplorarCatalogo` (alias y fragmento) | `variables/E02_actor.json` |
| E02 | `CatalogoCompleto` | `variables/E02_actor.json` |
| E02 | `CatalogoPorRecurso` | `variables/E02_resource_null.json`, `E02_resource_company_users.json`, `E02_resource_payments.json` (error) |
| Investigación | `CompararPuestos` (alias y fragmento) | `variables/comparar_puestos.json` |
| E03 | `RevisarConfiguracion` | `variables/S1_capturista.json` |
| E04, E05 | `AplicarConfiguracion` | `variables/S1_capturista.json` |
| E05, E09 | `AplicarConfiguracion` | `variables/S0_capturista.json` |
| E06 | `RevisarConfiguracion` y `AplicarConfiguracion` | `variables/E06_*.json` (una por variante) |
| E08 | `AplicarConfiguracion` | `variables/E08_lista_vacia.json` |
| E10 | `CuentasDeLaEmpresa` | `variables/E10_cuentas.json` |
| E10 | `RegistrarMovimiento` (+ encabezado `Authorization: Bearer <token>`) | `variables/E10_movimiento.json` |

Los id de los archivos de `variables/` son los de la base donde se corrió el script; en otra base se regeneran ejecutándolo.

## Archivos de la entrega

```
app/                         código del sistema
tests/test_e07_reversion.py  prueba E07
README.md
portada_equipo.pdf           integrantes y matrículas
investigacion.md             cuatro respuestas con ejemplos y fuentes oficiales
operaciones.graphql          operaciones con nombre
variables/                   JSON de cada operación
configuracion_inicial.json   matriz por códigos antes de programar
configuracion_final.json     matriz por códigos al terminar (E09)
comprobaciones.sql           consultas de verificación y preparación/restauración de E06
evidencias.md                E01 a E10: precondición, operación, esperado, obtenido y regla
evidencias/actividad5/       JSON, SQL, salida de E07 y capturas
documentacion/
  probar_actividad5.py       ejecuta E01 a E10
  tomar_capturas_actividad5.py  toma las capturas de E01 a E10
  probar_actividad4.py, tomar_capturas.py, PRUEBAS_GRAPHQL.md, ANALISIS.md, anteriores/
evidencias/actividad4/       evidencias de la actividad 4
```
