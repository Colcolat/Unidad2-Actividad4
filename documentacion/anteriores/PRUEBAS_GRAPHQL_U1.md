# Actividad 3 - Evidencias de pruebas GraphQL

## Día 1 - Gestión de Empresas

Las operaciones correspondientes al Día 1 fueron probadas mediante GraphiQL.

### 1. Creación de empresa

Se ejecutó la mutación `createCompany` proporcionando los datos de una nueva empresa.

Resultado:

La empresa fue creada correctamente y se asignó un identificador único.

Estado: Correcto.

### 2. Consulta de empresas

Se ejecutó la consulta `companies`.

Resultado:

El sistema mostró correctamente las empresas registradas.

Estado: Correcto.

### 3. Consulta de empresa por ID

Se ejecutó la consulta `company(id)`.

Resultado:

El sistema devolvió correctamente la información correspondiente a la empresa solicitada.

Estado: Correcto.

### 4. Actualización de empresa

Se ejecutó la mutación `updateCompany`.

Resultado:

Los datos de la empresa fueron actualizados correctamente.

Estado: Correcto.

### 5. Desactivación de empresa

Se ejecutó la mutación `deactivateCompany`.

Resultado:

La empresa cambió su atributo `isActive` a `false`, implementando una eliminación lógica.

Estado: Correcto.

### 6. Consulta de empresas activas

Se ejecutó:

`companies(activeOnly: true)`

Resultado:

Solamente se mostraron las empresas que se encontraban activas.

Estado: Correcto.

---

# Día 2 - Gestión de Usuarios

## 1. Creación correcta del administrador

Se ejecutó la mutación `createCompanyAdmin`.

Resultado:

Se creó correctamente el administrador principal relacionado con la empresa.

El registro generado presentó:

- `isAdmin: true`
- `isActive: true`

Estado: Correcto.

---

## 2. Autenticación correcta

Se ejecutó la mutación `login` utilizando el correo electrónico y contraseña correctos del administrador.

Resultado:

El sistema generó correctamente un token JWT con tipo `Bearer`.

Estado: Correcto.

---

## 3. Creación correcta de usuario

Se utilizó el token JWT del administrador para ejecutar `createCompanyUser`.

Usuario creado:

- Nombre: Usuario Uno
- Correo: usuario1@techsolutions.com
- Empresa: Tech Solutions Mérida
- isAdmin: false
- isActive: true

Resultado:

El usuario fue registrado correctamente y relacionado con la empresa mediante `CompanyUser`.

Estado: Correcto.

---

## 4. Relación Empresa-Usuario

Se ejecutó la consulta `companyUsers(companyId: "1")`.

Resultado:

Se obtuvieron los siguientes registros:

- Administrador Empresa - `isAdmin: true`
- Usuario Uno - `isAdmin: false`

Esto demuestra la relación:

Company -> CompanyUser -> User

Estado: Correcto.

---

## 5. Correo electrónico duplicado

Se intentó crear otro usuario utilizando:

`usuario1@techsolutions.com`

Resultado:

El sistema rechazó la operación mostrando:

`El correo electrónico ya está registrado.`

Estado: Validación correcta.

---

## 6. Segundo administrador para la misma empresa

Se intentó registrar un segundo administrador principal en la empresa.

Resultado:

El sistema rechazó la operación mostrando:

`La empresa ya tiene un administrador principal.`

Estado: Validación correcta.

---

## 7. Usuario en empresa inexistente

Se intentó registrar un usuario utilizando el identificador de empresa `9999`.

Resultado:

El sistema mostró:

`La empresa no existe.`

Estado: Validación correcta.

---

## 8. Autenticación incorrecta

Se intentó iniciar sesión utilizando una contraseña incorrecta.

Resultado:

El sistema mostró:

`Correo electrónico o contraseña incorrectos.`

No se generó ningún token.

Estado: Validación correcta.

---

## 9. Validación de correo electrónico

Se intentó crear un usuario utilizando:

`correo-invalido`

Resultado:

El sistema rechazó la operación mostrando:

`El correo electrónico no es válido.`

Estado: Validación correcta.

---

## 10. Contraseñas almacenadas mediante hash

Se consultó directamente la tabla `users`.

Las contraseñas almacenadas presentaron el formato:

`$argon2id$...`

Las contraseñas originales no se encuentran almacenadas en texto plano.

Estado: Correcto.

---

## 11. Desactivación de usuario

Se ejecutó la mutación `deactivateCompanyUser`.

Resultado:

La relación del usuario con la empresa cambió:

`isActive: true`

a:

`isActive: false`

Estado: Correcto.

---

## 12. Estructura de base de datos

Se ejecutó:

`SHOW TABLES;`

Resultado:

Se encontraron las siguientes tablas:

- companies
- company_users
- users

Estado: Correcto.

---

# Resultado final

Las pruebas realizadas comprobaron el funcionamiento del CRUD de empresas, la relación Empresa-Usuario, la creación de un único administrador principal por empresa, el registro de usuarios, la autenticación mediante JWT, el almacenamiento seguro de contraseñas mediante hash y las validaciones solicitadas.

También se comprobó el manejo de errores para correos duplicados, correos inválidos, empresas inexistentes, credenciales incorrectas e intentos de crear más de un administrador principal para una misma empresa.
