# Unidad II, Actividad 4: pruebas en GraphiQL

Guía para tomar las capturas de la comprobación en `http://127.0.0.1:8000/graphql`. Cada bloque se pega en GraphiQL tal cual. Junto a cada captura va la frase que aparece en **Regla que demuestra**.

Los textos `ID_ANA`, `ID_CAPTURISTA`, `ID_ACCOUNTS_WRITE`, etc. son los id de tu base. No hace falta buscarlos a mano:

```bash
python documentacion/probar_actividad4.py --preparar
```

Si prefieres que las capturas se tomen solas, `documentacion/tomar_capturas.py` recorre esta misma guía con Chrome y guarda los PNG.

El comando `--preparar` crea una empresa con Ana (ADMINISTRADOR), Luis (CONTADOR), María y José (CAPTURISTA) y Pedro (CONSULTA), una cuenta "Caja general" y el concepto "Ventas" asignado a esa cuenta. Después escribe `evidencias/actividad4/guia_capturas.md`, que es esta misma guía con los id ya puestos. Sigue esa copia en orden, de arriba hacia abajo, y guarda cada captura en `evidencias/actividad4/capturas/` con el nombre que aparece en `evidencias/actividad4/Informacion_evidencias.md`.

Las consultas de MySQL se ejecutan con:

```bash
docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
```

---

## Parte 1. La configuración inicial

### Captura 00: roles y permisos del catálogo

```graphql
query {
  roles { id code name isActive }
  permissions { id code name isActive }
}
```

**Regla que demuestra:** el catálogo tiene los cuatro roles (ADMINISTRADOR, CONTADOR, CAPTURISTA, CONSULTA) y los diez permisos. Ningún permiso es propio de una persona.

### Captura 01: la lista del capturista antes del cambio

```graphql
query {
  rolePermissions(roleId: "ID_CAPTURISTA") {
    role { code }
    permission { code }
    isActive
  }
}
```

Resultado esperado: `accounts.read`, `concepts.read`, `transactions.read`, `transactions.write`. No aparece `accounts.write`.

**Regla que demuestra:** el capturista registra movimientos (`transactions.write`) pero su rol no tiene `accounts.write`, así que no puede crear cuentas.

Para completar la Parte 1 se repite la consulta con `ID_CONSULTA` (solo permisos `.read`) y con `ID_CONTADOR` (incluye `accounts.write`, no incluye `roles.write`).

---

## Parte 2. Un permiso nuevo en el rol, dos personas

### Captura 02: createAccount rechazado para María y para José

Se ejecuta primero la de María y después la de José, cada una en su propia captura (02a y 02b). En GraphiQL se pueden dejar las dos en la misma pestaña y elegir cuál correr con el botón ▶.

```graphql
mutation CuentaMaria {
  createAccount(
    actorCompanyUserId: "ID_MARIA"
    input: { companyId: "ID_EMPRESA", accountType: CASH, name: "Cuenta de Maria" }
  ) { id name }
}

mutation CuentaJose {
  createAccount(
    actorCompanyUserId: "ID_JOSE"
    input: { companyId: "ID_EMPRESA", accountType: CASH, name: "Cuenta de Jose" }
  ) { id name }
}
```

Resultado esperado en las dos: `"El rol no tiene el permiso accounts.write."` y `data: null`.

**Regla que demuestra:** María y José tienen el rol CAPTURISTA, y como ese rol no tiene `accounts.write`, `exigir_permiso` rechaza la operación antes del commit y no se guarda la cuenta.

### Captura 03: Ana agrega accounts.write al rol CAPTURISTA

```graphql
mutation {
  assignPermissionToRole(
    input: { roleId: "ID_CAPTURISTA", permissionId: "ID_ACCOUNTS_WRITE" }
    actorCompanyUserId: "ID_ANA"
  ) {
    id
    role { code }
    permission { code }
    isActive
  }
}
```

**Regla que demuestra:** el cambio se hace una sola vez en el rol. Ana tiene `roles.write` y agrega la acción a la lista de CAPTURISTA, sin editar a María ni a José.

### Captura 04: createAccount aceptado para María y para José

Se vuelven a ejecutar `CuentaMaria` y `CuentaJose` de la captura 02 (04a y 04b). Ahora las dos devuelven `id` y `name`.

**Regla que demuestra:** María y José pueden crear cuentas porque los dos tienen el rol CAPTURISTA y ese rol ya tiene `accounts.write`. A José no se le editó nada.

### Captura 05: la pareja desactivada, no borrada, y el rechazo de los dos

Ana quita el permiso:

```graphql
mutation {
  removePermissionFromRole(
    roleId: "ID_CAPTURISTA"
    permissionId: "ID_ACCOUNTS_WRITE"
    actorCompanyUserId: "ID_ANA"
  )
}
```

En MySQL (captura 05a):

```sql
SELECT rp.id, r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA' AND p.code = 'accounts.write';
```

Resultado esperado: una fila con `is_active = 0`.

Después se ejecutan otra vez en GraphiQL (captura 05b y 05c), con nombres nuevos porque los anteriores ya existen:

```graphql
mutation CuentaMaria2 {
  createAccount(
    actorCompanyUserId: "ID_MARIA"
    input: { companyId: "ID_EMPRESA", accountType: CASH, name: "Segunda de Maria" }
  ) { id name }
}

mutation CuentaJose2 {
  createAccount(
    actorCompanyUserId: "ID_JOSE"
    input: { companyId: "ID_EMPRESA", accountType: CASH, name: "Segunda de Jose" }
  ) { id name }
}
```

**Regla que demuestra:** quitar el permiso desactiva la pareja en `role_permissions` (la fila queda con `is_active = 0`, el historial no se borra) y María y José vuelven a quedar fuera.

---

## Parte 3. Cambiar el puesto de una persona

### Captura 06: Pedro rechazado como consulta y aceptado después de assignRole

`createTransaction` también pide el token de quien registra. Primero se hace login con Pedro:

```graphql
mutation {
  login(input: { email: "CORREO_PEDRO", password: "CLAVE_DEMO" }) { token }
}
```

Se copia el token y se pone en la pestaña **Headers** de GraphiQL:

```json
{ "Authorization": "Bearer PEGA_AQUI_EL_TOKEN" }
```

Movimiento de Pedro (captura 06a, rechazado):

```graphql
mutation MovimientoPedro {
  createTransaction(
    actorCompanyUserId: "ID_PEDRO"
    input: { accountId: "ID_CUENTA", conceptId: "ID_CONCEPTO", transactionType: INCOME, amount: "250.00", shortDescription: "Venta de mostrador" }
  ) { id amount transactionType }
}
```

Resultado esperado: `"El rol no tiene el permiso transactions.write."`.

Ana le asigna el rol CAPTURISTA (captura 06b):

```graphql
mutation {
  assignRole(
    actorCompanyUserId: "ID_ANA"
    input: { companyUserId: "ID_PEDRO", roleId: "ID_CAPTURISTA" }
  ) {
    id
    role { code }
    isActive
    companyUser { id user { name } }
  }
}
```

Se vuelve a ejecutar `MovimientoPedro` con el mismo token (captura 06c). Ahora devuelve el movimiento.

En MySQL (captura 06d):

```sql
SELECT cur.company_user_id, r.code AS rol, cur.is_active
FROM company_user_roles cur
JOIN roles r ON r.id = cur.role_id
WHERE cur.company_user_id = ID_PEDRO;

SELECT COUNT(*) AS movimientos FROM transactions WHERE account_id = ID_CUENTA;
```

Resultado esperado: CONSULTA con `is_active = 0`, CAPTURISTA con `is_active = 1`, y un solo movimiento (el aceptado; el rechazado no dejó fila).

**Regla que demuestra:** el cambio de puesto de una persona se hace con `assignRole`. Pedro deja un solo rol activo y recibe la lista del capturista. El intento rechazado no guardó ningún movimiento.

### Captura 07: la lista del contador, igual antes y después del cambio de Pedro

Se ejecuta antes de la captura 06 (07a) y después (07b):

```graphql
query {
  contador: rolePermissions(roleId: "ID_CONTADOR") { permission { code } isActive }
  consulta: rolePermissions(roleId: "ID_CONSULTA") { permission { code } isActive }
}
```

Y Luis crea una cuenta (07c):

```graphql
mutation {
  createAccount(
    actorCompanyUserId: "ID_LUIS"
    input: { companyId: "ID_EMPRESA", accountType: DEBIT, name: "Bancos de Luis" }
  ) { id name accountType }
}
```

**Regla que demuestra:** cambiar el puesto de Pedro no toca la lista de ningún rol. El contador conserva sus ocho permisos y Luis sigue creando cuentas; consulta sigue sin permisos `.write`, aunque Pedro ya no la use.

---

## Parte 4. Quién puede cambiar la lista

### Captura 08: el intento de José rechazado y el de Ana aceptado

José intenta agregar `concepts.write` al rol CONSULTA (08a):

```graphql
mutation {
  assignPermissionToRole(
    input: { roleId: "ID_CONSULTA", permissionId: "ID_CONCEPTS_WRITE" }
    actorCompanyUserId: "ID_JOSE"
  ) { id role { code } permission { code } isActive }
}
```

Resultado esperado: `"El rol no tiene el permiso roles.write."`.

En MySQL, la lista activa de consulta no cambió (08b):

```sql
SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CONSULTA'
ORDER BY p.code;
```

La misma mutación con `actorCompanyUserId: "ID_ANA"` sí agrega el permiso (08c). Después Ana lo quita (08d):

```graphql
mutation {
  removePermissionFromRole(
    roleId: "ID_CONSULTA"
    permissionId: "ID_CONCEPTS_WRITE"
    actorCompanyUserId: "ID_ANA"
  )
}
```

**Regla que demuestra:** cambiar la lista de un rol pide `roles.write`, que solo tiene el ADMINISTRADOR. A José se le rechaza sin tocar la tabla; Ana sí puede, y al quitarlo consulta vuelve a quedar solo con lectura.

---

## Cierre

### Captura 09: el SELECT de role_permissions coincide con la tabla del documento

```sql
SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;
```

Resultado esperado: 26 filas activas (ADMINISTRADOR 10, CONTADOR 8, CAPTURISTA 4, CONSULTA 4) y dos filas inactivas, `CAPTURISTA accounts.write` y `CONSULTA concepts.write`, que son el historial de los cambios de las partes 2 y 4.

**Regla que demuestra:** al cerrar la actividad, la lista activa de los cuatro roles vuelve a coincidir con la tabla del documento, y los permisos quitados quedan como filas inactivas.

### Captura 10: reinicio sin duplicados

Se detiene el servidor (Ctrl+C), se vuelve a arrancar, se repite en GraphiQL la consulta de la captura 00 (10a) y en MySQL (10b):

```sql
SELECT
  (SELECT COUNT(*) FROM roles) AS roles,
  (SELECT COUNT(*) FROM permissions) AS permisos,
  (SELECT COUNT(*) FROM role_permissions WHERE is_active = 1) AS parejas_activas;
```

Resultado esperado: `4`, `10`, `26`.

**Regla que demuestra:** la carga inicial no duplica roles ni permisos al reiniciar, y tampoco reactiva los permisos que se quitaron.

---

## Si algo sale distinto

- `"El permiso ya está asignado a ese rol."`: la pareja ya estaba activa. Se quita con `removePermissionFromRole` y se repite.
- `"Ya existe una cuenta con ese nombre en la empresa."`: la cuenta se guardó en un intento anterior. Se cambia el `name`.
- `"El token no corresponde a la membresía que actúa."`: el token de Headers no es el de Pedro, o ya expiró (dura 60 minutos). Se repite el login.
- Si la Parte 1 falla porque CAPTURISTA ya tiene `accounts.write` (por ejemplo, una prueba quedó a la mitad), Ana lo quita con `removePermissionFromRole` y se empieza de nuevo.
