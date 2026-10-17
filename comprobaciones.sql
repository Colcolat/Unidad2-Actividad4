-- Unidad II · Actividad 5 · Comprobaciones en MySQL
-- Cliente: docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db
-- Se usan códigos, no id numéricos, para que funcione en cualquier base.

-- ============================================================
-- 1. Relaciones de todos los roles (E01, E03, E04, E05, E08, E09)
-- ============================================================
SELECT rp.id AS relacion_id,
       r.code AS rol,
       p.code AS permiso,
       rp.is_active AS relacion_activa,
       p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;

-- Solo el capturista (antes y después de cada operación en E03 a E08)
SELECT rp.id AS relacion_id,
       p.id AS permiso_id,
       p.code AS permiso,
       rp.is_active AS relacion_activa,
       p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
ORDER BY p.code;

-- ============================================================
-- 2. Duplicados: debe devolver cero filas (E04, E08, E09)
-- ============================================================
SELECT role_id, permission_id, COUNT(*) AS repeticiones
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;

-- La restricción que impide duplicados existe en la tabla
SHOW INDEX FROM role_permissions WHERE Key_name = 'uq_role_permission';

-- ============================================================
-- 3. Catálogo y conteos (E01, E08, E09)
-- ============================================================
SELECT id, code, is_active FROM roles ORDER BY code;
SELECT id, code, is_active FROM permissions ORDER BY code;

SELECT (SELECT COUNT(*) FROM roles) AS roles,
       (SELECT COUNT(*) FROM permissions) AS permisos,
       (SELECT COUNT(*) FROM role_permissions) AS relaciones,
       (SELECT COUNT(*) FROM role_permissions WHERE is_active = 1) AS relaciones_activas;

-- Parejas activas por rol: al final deben ser 10, 8, 4 y 4
SELECT r.code AS rol, COUNT(*) AS permisos_activos
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
WHERE rp.is_active = 1
GROUP BY r.code
ORDER BY r.code;

-- Lista activa por rol en una sola línea, para compararla con configuracion_inicial.json (E09)
SELECT r.code AS rol, GROUP_CONCAT(p.code ORDER BY p.code SEPARATOR ', ') AS permisos_activos
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE rp.is_active = 1 AND p.is_active = 1
GROUP BY r.code
ORDER BY r.code;

-- ============================================================
-- 4. E05. La relación de accounts.write conserva su id y el permiso sigue activo
-- ============================================================
SELECT rp.id AS relacion_id, rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA' AND p.code = 'accounts.write';

-- ============================================================
-- 5. E06. Preparación y restauración de datos de laboratorio
--    No hay mutación para desactivar un permiso ni para reactivar un rol;
--    se prepara aquí y se restablece al terminar cada variante.
-- ============================================================

-- E06 · rol inactivo. Preparar:
UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA';
--   ... ejecutar RevisarConfiguracion y AplicarConfiguracion con roleId = id de CONSULTA ...
-- Restaurar:
UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA';

-- E06 · permiso inactivo. Preparar:
UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write';
--   ... ejecutar con la lista S0 + id de concepts.write para CAPTURISTA ...
-- Restaurar:
UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write';

-- Comprobar que los estados quedaron restablecidos
SELECT code, is_active FROM roles WHERE code = 'CONSULTA';
SELECT code, is_active FROM permissions WHERE code = 'concepts.write';

-- ============================================================
-- 6. E10. Movimiento persistido con cuenta, concepto, empresa y monto
--    Cambiar el nombre de la empresa por el que se creó en la prueba.
-- ============================================================
SELECT t.id AS movimiento_id,
       c.name AS empresa,
       a.name AS cuenta,
       k.name AS concepto,
       t.transaction_type AS tipo,
       t.amount AS monto,
       u.name AS capturo
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN concepts k ON k.id = t.concept_id
JOIN companies c ON c.id = a.company_id
JOIN users u ON u.id = t.captured_by
ORDER BY t.id DESC
LIMIT 5;
