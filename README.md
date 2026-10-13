# Unidad II · Actividad 4: Configuración de permisos para diferentes roles

Sistema General de Ingresos. Es el mismo proyecto de la actividad 3 (FastAPI, Strawberry GraphQL, SQLAlchemy y MySQL con Docker Compose). Aquí no se agregaron tablas ni columnas: se usan `roles`, `permissions`, `role_permissions` y `company_user_roles` para configurar qué puede hacer cada puesto y demostrar que el servidor obedece esa configuración.

## Dónde vive cada pieza

| Pieza | Dónde vive |
|---|---|
| Usuario | `users` (`User`) |
| Su lugar en una empresa | `company_users` (`CompanyUser`) |
| El puesto de ese lugar | `company_user_roles`, con un solo rol activo por membresía |
| La lista de acciones de cada puesto | `role_permissions`. Quitar un permiso pone `is_active = 0`; la fila no se borra |
| La decisión | `exigir_permiso` en `app/rbac.py`, que corre antes de cualquier `commit` |

## Configuración que debe existir al empezar y al terminar

| Permiso | Administrador | Contador | Capturista | Consulta |
|---|:-:|:-:|:-:|:-:|
| company.users.read | sí | sí | no | sí |
| company.users.write | sí | no | no | no |
| accounts.read | sí | sí | sí | sí |
| accounts.write | sí | sí | no | no |
| concepts.read | sí | sí | sí | sí |
| concepts.write | sí | sí | no | no |
| transactions.read | sí | sí | sí | sí |
| transactions.write | sí | sí | sí | no |
| roles.read | sí | sí | no | no |
| roles.write | sí | no | no | no |

Son 26 parejas activas: 10, 8, 4 y 4. El arranque (`seed_rbac`) carga la lista solo si un rol está vacío, así que reiniciar no duplica roles, permisos ni parejas, y tampoco reactiva permisos que se quitaron a propósito.

## Arranque

```bash
docker compose up -d
```

Si el contenedor `actividad4_mysql` ya existe de las actividades anteriores, basta con `docker start actividad4_mysql`.

```bash
python -m venv .venv
```

Se activa el entorno (`.venv\Scripts\activate` en Windows, `source .venv/bin/activate` en Linux o macOS) y se instala lo necesario:

```bash
pip install -r requirements.txt
```

Se copia `.env.example` a `.env`, se pone una `SECRET_KEY` y se arranca el servidor:

```bash
uvicorn app.main:app --reload
```

GraphiQL queda en `http://127.0.0.1:8000/graphql`.

## Pruebas

Con el servidor activo, en otra terminal:

```bash
python documentacion/probar_actividad4.py
```

Crea una empresa nueva con Ana (ADMINISTRADOR), Luis (CONTADOR), María y José (CAPTURISTA) y Pedro (CONSULTA) y recorre las cuatro partes de la actividad. Además de la respuesta de GraphQL, revisa MySQL directamente: que un rechazo no guarde la fila, que la pareja quitada quede inactiva y no borrada, que Pedro tenga un solo rol activo y que el intento de José no cambie la lista. Al final comprueba que la lista vuelve a coincidir con la tabla de arriba. Las respuestas quedan en `evidencias/actividad4/json/` y el SELECT final en `evidencias/actividad4/select_role_permissions.txt`.

Para tomar las capturas en GraphiQL:

```bash
python documentacion/probar_actividad4.py --preparar
```

Solo crea la empresa y las cinco personas, y escribe `evidencias/actividad4/guia_capturas.md` con cada consulta ya lista para pegar, con los id de esa empresa. La plantilla de esa guía es [documentacion/PRUEBAS_GRAPHQL.md](documentacion/PRUEBAS_GRAPHQL.md).

`documentacion/tomar_capturas.py` puede tomar esas capturas automáticamente con Chrome y Playwright (`pip install playwright`). Las capturas van en `evidencias/actividad4/capturas/` y la frase de cada una está en [evidencias/actividad4/Informacion_evidencias.md](evidencias/actividad4/Informacion_evidencias.md).

## Operaciones GraphQL que se usan

| Qué se quiere hacer | GraphQL | Permiso que exige |
|---|---|---|
| Ver los roles | `roles` | — |
| Ver los permisos | `permissions` | — |
| Ver la lista de un rol | `rolePermissions(roleId:)` | — |
| Agregar un permiso a un rol | `assignPermissionToRole` | `roles.write` |
| Quitar un permiso de un rol | `removePermissionFromRole` | `roles.write` |
| Darle un rol a una persona | `assignRole` | `roles.write` |
| Crear una cuenta | `createAccount` | `accounts.write` |
| Registrar un movimiento | `createTransaction` (además pide el token de quien registra) | `transactions.write` |

`actorCompanyUserId` es la membresía con la que se prueba, como en la actividad 3. El servidor no confía en el permiso que diga el cliente: busca el rol activo de esa membresía y lee su lista en `role_permissions`. Si la membresía es de otra empresa, `exigir_permiso` también la rechaza.

## Estructura

```
app/                     código del sistema (sin cambios de lógica respecto a la actividad 3)
documentacion/
  PRUEBAS_GRAPHQL.md     guía de capturas de la actividad 4
  probar_actividad4.py   pruebas automáticas de la actividad 4
  tomar_capturas.py      toma las capturas de GraphiQL y MySQL
  ANALISIS.md            análisis del dominio
  anteriores/            instrucciones, pruebas y script de la actividad 3 y de la unidad 1
evidencias/
  actividad4/            capturas, JSON de las pruebas y SELECT final
  actividad3/            evidencias entregadas en la actividad 3
```
