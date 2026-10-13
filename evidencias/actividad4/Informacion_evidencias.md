# Unidad II, Actividad 4: evidencias de la configuración de permisos por rol

Las capturas se tomaron en GraphiQL (`/graphql`) y en MySQL, con una empresa en la que Ana es ADMINISTRADOR, Luis es CONTADOR, María y José son CAPTURISTA y Pedro empieza como CONSULTA. Las consultas exactas de cada captura están en `documentacion/PRUEBAS_GRAPHQL.md` y se tomaron con `documentacion/tomar_capturas.py`, que comprueba cada respuesta antes de guardar la imagen. Las capturas de MySQL muestran la salida real del cliente `mysql` dentro del contenedor `actividad4_mysql`.

## Captura 00, Catálogo de roles y permisos
`capturas/00_catalogo.png`

El catálogo tiene los cuatro roles, ADMINISTRADOR, CONTADOR, CAPTURISTA y CONSULTA, y los diez permisos. Ningún permiso pertenece a una persona, todos se reparten por rol.

## Captura 01, Lista del capturista antes del cambio
`capturas/01_lista_capturista_antes.png`

El rol CAPTURISTA puede registrar movimientos con transactions.write, pero su lista no incluye accounts.write, por eso todavía no puede crear cuentas.

## Captura 02, Cuenta rechazada para María y para José
`capturas/02a_cuenta_maria_rechazada.png`, `capturas/02b_cuenta_jose_rechazada.png`

María y José intentan crear una cuenta y el sistema los rechaza con el mismo mensaje, porque los dos tienen el rol CAPTURISTA y ese rol no tiene accounts.write. El rechazo ocurre en exigir_permiso antes del commit, así que no se guarda la cuenta.

## Captura 03, Ana agrega accounts.write al rol CAPTURISTA
`capturas/03_ana_agrega_accounts_write.png`

Ana, que tiene roles.write, agrega el permiso una sola vez al rol CAPTURISTA. No se edita a María ni a José.

## Captura 04, Cuenta aceptada para María y para José
`capturas/04a_cuenta_maria_aceptada.png`, `capturas/04b_cuenta_jose_aceptada.png`

Con el mismo rol de antes, María y José ya pueden crear cuentas. El cambio que se hizo en el rol alcanzó a las dos personas que lo tienen.

## Captura 05, Pareja desactivada y nuevo rechazo
`capturas/05_ana_quita_accounts_write.png`, `capturas/05a_pareja_inactiva_mysql.png`, `capturas/05b_cuenta_maria_rechazada.png`, `capturas/05c_cuenta_jose_rechazada.png`

Ana quita accounts.write del capturista. En MySQL la fila de la pareja sigue existiendo con is_active en 0, el historial no se borra, y María y José vuelven a recibir el rechazo.

## Captura 06, Pedro rechazado como consulta y aceptado después de assignRole
`capturas/06_login_pedro.png`, `capturas/06a_movimiento_pedro_rechazado.png`, `capturas/06a_movimientos_sin_fila_mysql.png`, `capturas/06b_assign_role_pedro.png`, `capturas/06c_movimiento_pedro_aceptado.png`, `capturas/06d_pedro_un_rol_activo_mysql.png`

Pedro inicia sesión y, como CONSULTA, no puede registrar un movimiento; en MySQL la cuenta sigue con cero movimientos, el rechazo no guardó la fila. Ana le asigna CAPTURISTA con assignRole, el rol anterior queda inactivo, Pedro conserva un solo rol activo y ya puede registrar el movimiento.

## Captura 07, Lista del contador igual antes y después del cambio de Pedro
`capturas/07a_listas_antes.png` (tomada antes de la captura 06), `capturas/07b_listas_despues.png`, `capturas/07c_cuenta_luis_aceptada.png`

Cambiar el puesto de Pedro no modificó ninguna lista. El contador conserva sus ocho permisos y Luis sigue creando cuentas, y consulta sigue sin permisos de escritura aunque Pedro ya no la use.

## Captura 08, José no puede cambiar la lista y Ana sí
`capturas/08a_jose_rechazado.png`, `capturas/08b_lista_consulta_sin_cambio_mysql.png`, `capturas/08c_ana_agrega_concepts_write.png`, `capturas/08d_ana_quita_concepts_write.png`

José intenta agregar concepts.write al rol CONSULTA y el sistema lo rechaza porque su rol no tiene roles.write, la lista activa en MySQL no cambia. Ana sí puede agregarlo, y al quitarlo otra vez consulta vuelve a quedar solo con lectura.

## Captura 09, SELECT final de role_permissions
`capturas/09_select_role_permissions.png`

Al cerrar la actividad la lista activa vuelve a coincidir con la tabla del documento, con 26 parejas activas, diez del administrador, ocho del contador, cuatro del capturista y cuatro de consulta. Las dos filas inactivas, CAPTURISTA accounts.write y CONSULTA concepts.write, son el historial de los cambios que se hicieron y se quitaron.

## Captura 10, Reinicio sin duplicados
`capturas/10a_catalogo_tras_reinicio.png`, `capturas/10b_reinicio_sin_duplicados.png`

Después de reiniciar el servidor, GraphQL sigue mostrando los mismos cuatro roles y diez permisos, y en MySQL siguen registrados cuatro roles, diez permisos y veintiséis parejas activas. La carga inicial no duplica datos ni reactiva los permisos que se quitaron.
