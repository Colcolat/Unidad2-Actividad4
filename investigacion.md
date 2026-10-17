# Investigación breve · Unidad II, Actividad 5

Sistema General de Ingresos. Las respuestas usan los roles y permisos que ya tiene el proyecto: ADMINISTRADOR, CONTADOR, CAPTURISTA y CONSULTA, y los diez permisos de la actividad 4.

## 1. Autenticación, autorización y configuración de permisos

Son tres preguntas distintas. **Autenticar** responde «¿quién eres?»: en `login` el servidor vuelve a calcular el hash de la contraseña que escribió la persona y lo compara con `users.password_hash`; si coincide, entrega un token firmado. **Configurar permisos** responde «¿qué incluye este puesto?»: es la lista de `role_permissions`. Cuando Ana manda la lista S1 para CAPTURISTA con `setRolePermissions`, cambia lo que pueden hacer María y José, pero esa operación no dice quién está llamando. **Autorizar** responde «¿puedes hacer esto ahora?»: `exigir_permiso` busca el rol activo de la membresía que llama y revisa si su lista tiene, por ejemplo, `roles.write`. La guía de GraphQL insiste en que esta decisión vive en la capa de negocio y no en el esquema: GraphQL solo describe la operación. Por eso la revisión está en Python, dentro de cada resolver, y no en GraphiQL ni en un botón oculto.

`actorCompanyUserId` no comprueba identidad porque es un número que escribe el cliente. Si en GraphiQL pongo el id de la membresía de Ana, el servidor la trata como Ana aunque quien escribe sea María; nada demuestra que la persona conozca la contraseña de Ana. En el laboratorio sirve para practicar la autorización, pero la identidad real debe salir de un token que el servidor validó, tema que se verá en el tema 2.

**Fuente:** GraphQL Foundation, «Authorization», https://graphql.org/learn/authorization/ (consultado el 17 de octubre de 2026).

## 2. Variables, alias y fragmentos para pruebas repetibles

Las **variables** separan los datos del texto de la operación. `AplicarConfiguracion` se escribe una sola vez en `operaciones.graphql` y cada caso cambia solo el JSON: `variables/S0_capturista.json` y `variables/S1_capturista.json` usan la misma mutación. Así la prueba E04 se repite exactamente igual, y los id reales de cada base se cambian sin tocar la operación. Los **alias** renombran la clave de la respuesta; permiten pedir dos veces el mismo campo con argumentos distintos y distinguir los resultados. Los **fragmentos** reutilizan una selección de campos para no repetir `id`, `code` y `name` en cada lista; si mañana se agrega un campo, se cambia en un solo lugar.

Operación propia, incluida en `operaciones.graphql` con sus variables en `variables/comparar_puestos.json`:

```graphql
query CompararPuestos($capturista: ID!, $contador: ID!) {
  capturista: rolePermissions(roleId: $capturista) { permission { ...DatosPermiso } }
  contador: rolePermissions(roleId: $contador) { permission { ...DatosPermiso } }
}
```

En una sola petición se ven las cuatro acciones del capturista junto a las ocho del contador, cada lista con su nombre. Un fragmento no aplica reglas de seguridad: solo ahorra texto.

**Fuente:** GraphQL Foundation, «Queries», https://graphql.org/learn/queries/ (consultado el 17 de octubre de 2026).

## 3. Qué valida un enum o un input y qué sigue en Python

El **enum** `PermissionResource` limita los valores aceptados a COMPANY_USERS, ACCOUNTS, CONCEPTS, TRANSACTIONS y ROLES. Si alguien envía `PAYMENTS`, GraphQL rechaza el documento antes de llamar al resolver (caso E02). El resolver solo traduce cada valor a un prefijo existente; el enum no crea permisos. El **input** `SetRolePermissionsInput` valida la forma: que llegue `roleId`, que `permissionIds` sea una lista y que ningún elemento sea `null`.

Lo que el esquema no puede saber se sigue validando en Python, en `plan_role_permissions`: que el rol exista y esté activo, que no sea ADMINISTRADOR, que cada id exista y sea un permiso activo y que no haya repetidos. El tipo `ID` no sabe que `"3"` y `3` son el mismo permiso; GraphQL convierte los dos a texto y Python los compara como número, por eso `["3", 3]` también se rechaza.

`[ID!]!` acepta `[]` porque los dos signos hablan de cosas distintas: el de afuera exige que la lista exista y el de adentro exige que cada elemento no sea nulo. Una lista vacía existe y no tiene elementos nulos. En el proyecto `[]` tiene sentido: deja a un rol sin acciones activas (E08).

**Fuentes:** Strawberry, «Enums», https://strawberry.rocks/docs/types/enums ; Strawberry, «Input types», https://strawberry.rocks/docs/types/input-types (consultadas el 17 de octubre de 2026).

## 4. Atomicidad e idempotencia

**Atomicidad** es que toda la actualización se confirma o se revierte como una unidad. Pasar de S0 a otra lista puede activar una relación y desactivar otra; si se confirma una y falla la otra, el capturista queda con un puesto que nadie decidió. Por eso `setRolePermissions` valida, calcula y aplica con la misma sesión de SQLAlchemy, hace `flush` y un solo `commit` al final; si algo falla, `rollback` deja la lista anterior. La prueba E07 provoca el fallo después del `flush` y revisa desde una sesión nueva que todo siguió igual.

**Idempotencia** es que repetir la misma petición deja el mismo estado final. Si CAPTURISTA ya tiene S1, volver a enviar S1 no inserta filas ni cambia estados y devuelve `changed: false` (E04). Son ideas diferentes: una operación puede ser atómica y no idempotente, como `assignPermissionToRole`, que rechaza la segunda vez.

Enviar varias mutaciones en una petición no garantiza un `rollback` conjunto. GraphQL ejecuta los campos raíz de mutación en serie, pero cada resolver abre su propia sesión y hace su propio `commit`; si la tercera falla, las dos primeras ya se confirmaron. La transacción la define el código del servidor, no la petición.

**Fuentes:** GraphQL Foundation, «Mutations», https://graphql.org/learn/mutations/ ; SQLAlchemy 2.0, «Transactions and Connection Management», https://docs.sqlalchemy.org/en/20/orm/session_transaction.html (consultadas el 17 de octubre de 2026).

## Cómo se aplicó lo investigado

- `PermissionResource`, `SetRolePermissionsInput`, `RolePermissionPlan` y `RolePermissionUpdate` se declararon con `@strawberry.enum`, `@strawberry.input` y `@strawberry.type` en `app/schema.py`.
- `previewRolePermissions` y `setRolePermissions` comparten `plan_role_permissions` (`app/rbac.py`), así las diferencias se calculan igual en las dos.
- Las respuestas de error devuelven `null` en el campo raíz y el motivo en `errors`, como explica la guía de respuestas de GraphQL (https://graphql.org/learn/response/, consultada el 17 de octubre de 2026).
- `operaciones.graphql` usa variables, alias y el fragmento `DatosPermiso`; cada caso tiene su JSON en `variables/`.
