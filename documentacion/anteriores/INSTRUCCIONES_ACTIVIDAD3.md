# Unidad II · Actividad 3

Proyecto de continuación del sistema financiero de la Unidad I, desarrollado con FastAPI, Strawberry, SQLAlchemy y MySQL.

## Catálogos y relaciones

Se incorporaron `roles`, `permissions`, `role_permissions` y `company_user_roles`. El arranque carga los cuatro roles y los diez permisos si no existen. Se conservan `companies`, `users`, `company_users`, `accounts`, `concepts`, `account_concepts` y `transactions`.

La matriz inicial tiene 26 permisos activos distribuidos en 10 para ADMINISTRADOR, 8 para CONTADOR, 4 para CAPTURISTA y 4 para CONSULTA.

El administrador principal mantiene `isAdmin = true` y recibe ADMINISTRADOR. Los usuarios normales nuevos se registran inicialmente con CONSULTA para que el administrador les asigne posteriormente CAPTURISTA o CONTADOR. Al reutilizar una base con membresías anteriores, se asigna el rol que corresponde cuando no tenían ninguno. Cada membresía mantiene un único rol activo.

## Nombres de operaciones GraphQL

Consultas: `roles`, `role`, `permissions`, `rolePermissions`, `companyUsers`, `accounts`, `concepts`, `accountConcepts`, `transactions`.

Mutaciones: `createRole`, `deactivateRole`, `createPermission`, `assignPermissionToRole`, `removePermissionFromRole`, `assignRole`, además de las operaciones financieras y de usuarios existentes.

Las operaciones protegidas reciben `actorCompanyUserId` como argumento separado de `input` cuando existe este último. `createTransaction`, `deleteTransaction`, `createCompanyUser` y `deactivateCompanyUser` mantienen además la validación JWT existente; el token debe pertenecer al usuario indicado en la membresía.

El PDF explica que en la siguiente actividad la identidad de todas las operaciones se obtendrá directamente del token. Aquí se conserva el parámetro didáctico `actorCompanyUserId` en las operaciones nuevas, por lo que no debe considerarse un mecanismo de seguridad de producción.

## Arranque

Usa la misma base MySQL de la Unidad I en el puerto 3307. No crees otro contenedor si ya funciona `actividad4_mysql`.

En la carpeta `U2_Actividad3`, crea `.env` a partir de `.env.example` y configura `SECRET_KEY`. Activa el entorno Python, instala `requirements.txt` y arranca `uvicorn app.main:app --reload`.

## Pruebas

Con el servidor activo, ejecuta `python documentacion/anteriores/probar_actividad3.py` desde otra terminal. El programa crea una empresa de demostración con identificador nuevo, varios usuarios, prueba la matriz, autorizaciones, denegaciones y cambio de rol. Los resultados se almacenan en `evidencias/actividad3/*.json`. Las contraseñas de prueba son demostrativas y los tokens de login no se escriben en los JSON.

Las capturas PNG de GraphiQL se deben guardar manualmente en `evidencias/actividad3/` y acompañar con una frase que explique la regla demostrada. El script no genera capturas PNG ni las simula.

## Verificación de MySQL

Las tablas deben ser `roles`, `permissions`, `role_permissions` y `company_user_roles` junto con las existentes. Puedes consultar la matriz con `SELECT r.code, p.code, rp.is_active FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code;`.

Reinicia el servidor y compara el conteo de los roles y permisos para validar que la siembra inicial no duplicó las filas.

## Regla de aislamiento

Las consultas y operaciones financieras comprueban que el identificador de la empresa corresponde a la membresía actora. En la consulta de movimientos, la búsqueda sin cuenta filtra igualmente por empresa.
