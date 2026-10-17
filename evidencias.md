# Evidencias · Unidad II, Actividad 5: configurar permisos con GraphQL

Las respuestas y consultas de esta página salen de `documentacion/probar_actividad5.py`, que ejecuta las operaciones con nombre de `operaciones.graphql` con los JSON de `variables/` y revisa MySQL con una conexión nueva después de cada paso. Cada caso guarda:

- la respuesta GraphQL en `evidencias/actividad5/json/<caso>.json` (incluye qué operación y qué archivo de variables se usó);
- la consulta SQL y su resultado en `evidencias/actividad5/sql/<caso>.txt`;
- las capturas de GraphiQL y del cliente `mysql` en `evidencias/actividad5/capturas/` con el mismo número de caso.

Ids de esta corrida (cambian de una base a otra; están en `evidencias/actividad5/json/identificadores.json`): membresía de Ana **14** (ADMINISTRADOR), membresía de María **15** (CAPTURISTA), rol CAPTURISTA **3**, permisos `accounts.read` 3, `accounts.write` 4, `concepts.read` 5, `transactions.read` 7, `transactions.write` 8.

- **S0**: `accounts.read`, `concepts.read`, `transactions.read`, `transactions.write` → `variables/S0_capturista.json`
- **S1**: S0 + `accounts.write` → `variables/S1_capturista.json`

Usuarios y empresa ficticios. No se muestran contraseñas, tokens ni hashes: en los JSON el token de `login` aparece como `OCULTO`.

---

## E01. Punto de partida

| | |
|---|---|
| Precondición | Servidor arrancado sobre la base de la actividad 4. Empresa de prueba con Ana (ADMINISTRADOR) y María (CAPTURISTA). |
| Operación y variables | `PuntoDePartida` (sin variables); `ListaDelRol` con `variables/E01_lista_capturista.json` |
| Resultado esperado | Cuatro roles, diez permisos y CAPTURISTA en S0. |
| Resultado obtenido | 4 roles y 10 permisos. Las cuatro listas activas coinciden con `configuracion_inicial.json` (10, 8, 4 y 4). CAPTURISTA tiene activas las relaciones 19, 20, 21 y 22. |
| Regla demostrada | La configuración de partida es la matriz de la actividad 4, por códigos. |
| Archivos | `json/E01_punto_de_partida.json`, `json/E01_lista_capturista.json`, `sql/E01_capturista.txt`, `sql/E01_relaciones.txt`, `sql/E01_conteos.txt`, `configuracion_inicial.json` |

## E02. Catálogo

| | |
|---|---|
| Precondición | E01. |
| Operación y variables | `ExplorarCatalogo` y `CatalogoCompleto` con `variables/E02_actor.json`; `CatalogoPorRecurso` con `E02_resource_null.json`, `E02_resource_company_users.json` y `E02_resource_payments.json`; además el literal `permissionCatalog(resource: PAYMENTS, ...)`. |
| Resultado esperado | Dos permisos por grupo; diez sin filtro; error de validación para PAYMENTS. |
| Resultado obtenido | `cuentas`: accounts.read, accounts.write. `movimientos`: transactions.read, transactions.write. Sin filtro y con `resource: null`: 10 permisos ordenados por código. Con variable: `Variable '$resource' has invalid value: Value 'PAYMENTS' does not exist in 'PermissionResource' enum.` Con literal: `Value 'PAYMENTS' does not exist in 'PermissionResource' enum.` y sin `data`. |
| Regla demostrada | El filtro se resuelve en MySQL por prefijo; los alias separan dos llamadas al mismo campo; el fragmento `DatosPermiso` evita repetir `id code name`; el enum se valida antes del resolver. |
| Archivos | `json/E02_explorar_catalogo.json`, `json/E02_catalogo_completo.json`, `json/E02_catalogo_resource_null.json`, `json/E02_catalogo_company_users.json`, `json/E02_enum_inexistente_variable.json`, `json/E02_enum_inexistente_literal.json` |

## E03. Previsualización

| | |
|---|---|
| Precondición | CAPTURISTA guardado en S0. |
| Operación y variables | `RevisarConfiguracion` con `variables/S1_capturista.json` |
| Resultado esperado | Uno por activar, cero por desactivar, cuatro sin cambio, total cinco. |
| Resultado obtenido | `current` = S0, `toActivate` = [accounts.write], `toDeactivate` = [], `unchanged` = S0, `finalCount` = 5. |
| SQL antes / después | Idénticos: relaciones 19, 20, 21, 22 activas y 27 (`accounts.write`, inactiva desde la actividad 4) sin cambio. |
| Regla demostrada | La previsualización es una `query`: solo lee y calcula. |
| Archivos | `json/E03_revisar_S1.json`, `sql/E03_antes.txt`, `sql/E03_despues.txt` |

## E04. Aplicación

| | |
|---|---|
| Precondición | E03 (CAPTURISTA en S0). |
| Operación y variables | `AplicarConfiguracion` con `variables/S1_capturista.json`, dos veces. |
| Resultado esperado | Primera: `changed: true`. Segunda: `changed: false`, cero altas/bajas, total cinco. |
| Resultado obtenido | Primera: `activated` = [accounts.write], `changed: true`, `finalCount: 5`. Segunda: `activated` = [], `deactivated` = [], `finalCount: 5`, `changed: false`. |
| SQL | Tras la primera, la relación 27 pasa a `relacion_activa = 1`; tras la segunda, las cinco filas son iguales. La consulta de duplicados devuelve `Empty set`. |
| Regla demostrada | Idempotencia: repetir la misma lista no inserta filas ni cambia estados. |
| Archivos | `json/E04_aplicar_S1_primera.json`, `json/E04_aplicar_S1_segunda.json`, `sql/E04_despues_primera.txt`, `sql/E04_despues_segunda.txt`, `sql/E04_duplicados.txt` |

## E05. Desactivar y reactivar

| | |
|---|---|
| Precondición | E04 (CAPTURISTA en S1). |
| Operación y variables | `AplicarConfiguracion` con `variables/S0_capturista.json` y luego con `variables/S1_capturista.json`. |
| Resultado esperado | `accounts.write` pasa a inactivo y después vuelve a activo. |
| Resultado obtenido | S0: `deactivated` = [accounts.write], `finalCount: 4`. S1: `activated` = [accounts.write], `finalCount: 5`. |
| SQL (tres momentos) | Relación **27**: activa (tras E04) → inactiva (tras S0) → activa (tras S1). `permiso_activo = 1` en los tres momentos. La relación de CONTADOR con `accounts.write` sigue activa. |
| Regla demostrada | Desactivar la relación no borra la fila ni apaga el permiso del catálogo; reactivar reutiliza el mismo id. |
| Archivos | `json/E05_aplicar_S0.json`, `json/E05_aplicar_S1.json`, `sql/E04_despues_primera.txt`, `sql/E05_tras_S0.txt`, `sql/E05_tras_S1.txt`, `sql/E05_relacion_accounts_write_contador.txt` |

## E06. Entradas inválidas

Precondición: CAPTURISTA en S1. Cada variante se ejecutó con `RevisarConfiguracion` y con `AplicarConfiguracion` usando el mismo archivo de variables. En todas, el campo raíz vuelve `null`, el motivo llega en `errors` y `SELECT` de todas las relaciones es idéntico antes y después (`sql/E06_<variante>_antes.txt` y `_despues.txt`).

| Variante | Variables | Preparación SQL (`comprobaciones.sql`) | Mensaje recibido |
|---|---|---|---|
| Rol inexistente | `E06_rol_inexistente.json` (`roleId: "999999"`) | — | El rol 999999 no existe. |
| Rol inactivo | `E06_rol_inactivo.json` (CONSULTA) | `UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA'`; se restablece al terminar | El rol CONSULTA está inactivo. |
| Propuesta sobre ADMINISTRADOR | `E06_administrador.json` | — | La lista del rol ADMINISTRADOR no se configura con esta operación. |
| Permiso inexistente mezclado con válidos | `E06_permiso_inexistente.json` (S0 + `"999999"`) | — | Los permisos 999999 no existen. |
| Permiso inactivo | `E06_permiso_inactivo.json` (S0 + `concepts.write`) | `UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write'`; se restablece al terminar | Los permisos concepts.write están inactivos en el catálogo. |
| Permiso repetido | `E06_permiso_repetido.json` (S0 + `"3"`) | — | El permiso 3 viene repetido en la lista. Cada permiso se envía una sola vez. |
| Mismo id como texto y como número | `E06_mismo_id_texto_y_numero.json` (S0 + `3`) | — | El permiso 3 viene repetido en la lista. Cada permiso se envía una sola vez. |
| Actor sin permiso (María, CAPTURISTA) | `E06_actor_sin_roles_write.json` | — | Revisar: El rol no tiene el permiso roles.read. Aplicar: El rol no tiene el permiso roles.write. |

Al final, `sql/E06_estados_restablecidos.txt` muestra CONSULTA y `concepts.write` otra vez con `is_active = 1`. Resumen en `json/E06_resumen.json`.

Regla demostrada: las reglas viven en Python (`plan_role_permissions`) y se revisan antes de escribir; si una falla no cambia ninguna relación. No se eliminan duplicados en silencio.

## E07. Reversión de un fallo

| | |
|---|---|
| Precondición | CAPTURISTA en S1. |
| Operación | `python -m unittest -v tests.test_e07_reversion` |
| Cómo provoca el fallo | Dentro del test, `mock.patch` reemplaza temporalmente `apply_role_permission_plan` en `app.schema` por una función que llama a la real (que hace `flush`), comprueba en la misma sesión que la activación y la desactivación ya se enviaron a la base, y lanza una excepción antes del `commit`. No hay parámetro público para provocar fallos. |
| Resultado esperado | Se revierte todo; la base conserva la lista previa. |
| Resultado obtenido | `Ran 1 test ... OK`. La mutación devuelve `setRolePermissions: null` con el error. Desde una sesión nueva, las filas de CAPTURISTA (id, permiso y estado) son idénticas a las de antes. |
| Regla demostrada | Atomicidad: una actualización completa usa una sola transacción; el `rollback` revierte las escrituras pendientes aunque ya se hayan enviado con `flush`. |
| Archivos | `E07_unittest.txt`, `sql/E07_antes.txt`, `sql/E07_despues_sesion_nueva.txt`, `tests/test_e07_reversion.py` |

## E08. Lista vacía y reinicio

| | |
|---|---|
| Precondición | CAPTURISTA en S1. |
| Operación y variables | `AplicarConfiguracion` con `variables/E08_lista_vacia.json` (`permissionIds: []`); detener y volver a arrancar `uvicorn`; `ListaDelRol` con `variables/E01_lista_capturista.json`. |
| Resultado esperado | Cero relaciones activas antes y después del arranque; filas conservadas. |
| Resultado obtenido | `deactivated` = las cinco de S1, `finalCount: 0`, `changed: true`. Antes y después del reinicio, las filas 19, 20, 21, 22 y 27 existen con `relacion_activa = 0`. Tras el reinicio `rolePermissions` devuelve `[]`; hay 4 roles y 10 permisos y la consulta de duplicados devuelve `Empty set`. |
| Regla demostrada | `seed_rbac` solo carga la matriz si el rol no tiene ninguna fila; un rol con filas inactivas ya fue configurado y su lista vacía se respeta. |
| Archivos | `json/E08_aplicar_vacia.json`, `json/E08_lista_capturista_tras_reinicio.json`, `sql/E08_antes_reinicio.txt`, `sql/E08_despues_reinicio.txt`, `sql/E08_conteos_tras_reinicio.txt`, `sql/E08_duplicados_tras_reinicio.txt` |

## E09. Restauración

| | |
|---|---|
| Precondición | E08 (CAPTURISTA sin permisos activos). |
| Operación y variables | `AplicarConfiguracion` con `variables/S0_capturista.json`; `ListaDelRol` para los cuatro roles. |
| Resultado esperado | Matriz activa igual a la configuración inicial. |
| Resultado obtenido | `activated` = S0, `finalCount: 4`. `configuracion_final.json` es igual a `configuracion_inicial.json`: ADMINISTRADOR 10, CONTADOR 8, CAPTURISTA 4, CONSULTA 4. Sin parejas duplicadas. |
| Regla demostrada | La configuración se puede devolver a su estado original por códigos; las filas inactivas adicionales son historial de las pruebas. |
| Archivos | `json/E09_aplicar_S0.json`, `configuracion_final.json`, `sql/E09_listas_por_rol.txt`, `sql/E09_relaciones_final.txt`, `sql/E09_duplicados.txt` |

## E10. Continuidad del proyecto

| | |
|---|---|
| Precondición | E09 (CAPTURISTA en S0). María inicia sesión con `login`. |
| Operación y variables | `CuentasDeLaEmpresa` con `variables/E10_cuentas.json`; `RegistrarMovimiento` con `variables/E10_movimiento.json` y el encabezado `Authorization: Bearer <token de María>`. |
| Resultado esperado | Las operaciones anteriores siguen funcionando. |
| Resultado obtenido | María (CAPTURISTA, con `accounts.read`) ve la cuenta «Caja general». Registra un ingreso de 350.00 con el concepto «Ventas de mostrador». En MySQL el movimiento aparece con su empresa, cuenta, concepto, monto y quien lo capturó. |
| Regla demostrada | Las funciones de las actividades anteriores (`accounts`, `login`, `createTransaction`, `exigir_permiso`) siguen operando con la configuración restaurada. |
| Archivos | `json/E10_cuentas.json`, `json/E10_registrar_movimiento.json`, `sql/E10_movimiento.txt` |

---

## Capturas que se agregan en `evidencias/actividad5/capturas/`

| Archivo | Qué se ve |
|---|---|
| `E01_punto_de_partida.png`, `E01_mysql.png` | `PuntoDePartida` en GraphiQL y relaciones activas de CAPTURISTA en MySQL |
| `E02_explorar_catalogo.png`, `E02_sin_filtro.png`, `E02_payments.png` | Operación con alias y fragmento, panel de variables, catálogo completo y error del enum |
| `E03_revisar.png`, `E03_mysql_antes_despues.png` | Respuesta de la previsualización y SQL idéntico antes y después |
| `E04_primera.png`, `E04_segunda.png`, `E04_mysql.png` | `changed: true`, `changed: false`, filas y duplicados |
| `E05_s0.png`, `E05_s1.png`, `E05_mysql.png` | Relación de `accounts.write` con el mismo id en los tres momentos |
| `E06_<variante>.png` | Variables y mensaje de cada variante; SQL antes y después |
| `E07_unittest.png` | Salida de la prueba y consulta posterior |
| `E08_vacia.png`, `E08_mysql_reinicio.png` | Lista vacía aplicada y filas inactivas después de reiniciar |
| `E09_restauracion.png`, `E09_mysql.png` | Restauración de S0 y listas por rol |
| `E10_cuentas.png`, `E10_movimiento.png`, `E10_mysql.png` | Consulta de cuentas, movimiento registrado y fila en MySQL |
