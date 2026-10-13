# Actividad 3 - Sistema Financiero

## Día 1 y Día 2

## 1. Actores del sistema

### Administrador general

Es el encargado de registrar, consultar, modificar y desactivar las empresas registradas en el sistema.

### Administrador empresarial

Es el administrador principal de una empresa. Cada empresa solamente puede tener un administrador principal activo.

El administrador empresarial puede iniciar sesión y registrar usuarios relacionados con su empresa.

### Usuario empresarial

Es un usuario registrado dentro de una empresa mediante la relación CompanyUser.

Puede autenticarse utilizando su correo electrónico y contraseña.

---

# 2. Entidades del dominio

Las principales entidades son:

### Company

Representa una empresa registrada dentro del sistema financiero.

### User

Representa a una persona que puede autenticarse dentro del sistema.

### CompanyUser

Representa la relación existente entre una empresa y un usuario.

La utilización de esta entidad intermedia permite que la arquitectura pueda soportar posteriormente usuarios relacionados con diferentes empresas.

---

# 3. Atributos

## Company

- id
- name
- legalName
- taxId
- email
- phone
- isActive
- createdAt
- updatedAt

## User

- id
- name
- email
- passwordHash
- emailVerified
- isActive
- createdAt
- updatedAt

El atributo passwordHash no se expone mediante GraphQL.

## CompanyUser

- id
- companyId
- userId
- isAdmin
- isActive
- joinedAt

---

# 4. Relaciones

Una empresa puede tener varios registros CompanyUser.

Un usuario puede tener diferentes registros CompanyUser.

CompanyUser pertenece a una sola empresa y a un solo usuario.

Esto permite representar una relación muchos a muchos entre Company y User por medio de CompanyUser.

---

# 5. Cardinalidades

Company 1 ---- N CompanyUser

User 1 ---- N CompanyUser

Por lo tanto:

Company N ---- M User

utilizando CompanyUser como entidad intermedia.

Adicionalmente, una empresa solamente puede tener un CompanyUser activo marcado como administrador principal.

---

# 6. Reglas de negocio

1. Toda empresa debe tener un nombre.

2. El taxId de una empresa no puede repetirse cuando se proporciona.

3. Los correos electrónicos deben tener un formato válido.

4. Cada correo electrónico de usuario debe ser único dentro del sistema.

5. Las contraseñas deben tener por lo menos ocho caracteres.

6. Las contraseñas nunca se almacenan directamente, solamente se almacena su hash.

7. Cada empresa solamente puede tener un administrador principal activo.

8. No se pueden registrar usuarios o administradores en una empresa inexistente.

9. No se pueden registrar usuarios en una empresa inactiva.

10. Solamente el administrador principal de una empresa puede registrar usuarios dentro de ella.

11. Cada empresa mantiene sus relaciones de usuarios de forma independiente.

12. La eliminación de empresas se realiza de manera lógica cambiando isActive a false.

13. Si las credenciales de autenticación son incorrectas, el sistema no genera un token.

14. Un usuario desactivado no puede autenticarse.

---

# 7. Modelo general

Sistema
|
+-- Empresa A
|   |
|   +-- Administrador principal
|   |
|   +-- Usuario 1
|   +-- Usuario 2
|   +-- Usuario N
|
+-- Empresa B
|   |
|   +-- Administrador principal
|   |
|   +-- Usuarios
|
+-- Empresa N

---

# 8. Relación Empresa-Usuario

Company
   |
   | 1
   |
   | N
CompanyUser
   |
   | N
   |
   | 1
 User

CompanyUser funciona como la entidad intermedia entre Company y User.

---

# 9. Distribución sugerida para cinco integrantes

Integrante 1:
Análisis de actores, entidades, atributos, relaciones y cardinalidades.

Integrante 2:
Modelo Company y conexión a base de datos.

Integrante 3:
CRUD de empresas y validaciones.

Integrante 4:
User, CompanyUser, administrador empresarial y autenticación.

Integrante 5:
Pruebas GraphQL, manejo de errores y evidencias.

Los nombres reales de cada integrante deberán agregarse antes de entregar.
