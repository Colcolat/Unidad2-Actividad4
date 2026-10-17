"""E07. Reversión de un fallo en setRolePermissions.

Usa la base configurada en DATABASE_URL (la misma MySQL del proyecto). La prueba crea su propia empresa
con una administradora, provoca un fallo después del flush y antes del commit, y comprueba desde una
sesión nueva que role_permissions quedó igual. Al terminar borra la empresa de prueba.

  python -m unittest discover -v
"""
import logging
import unittest
from unittest import mock
from uuid import uuid4

from sqlalchemy import select

import app.schema as schema_module
from app.database import Base, SessionLocal, engine
from app.models import Company, CompanyUser, User
from app.rbac import apply_role_permission_plan, assign_role_internal, seed_rbac
from app.rbac_models import CompanyUserRoleModel, PermissionModel, RoleModel, RolePermissionModel
from app.schema import schema
from app.security import hash_password

APLICAR = """
mutation AplicarConfiguracion($actor: ID!, $input: SetRolePermissionsInput!) {
  setRolePermissions(input: $input, actorCompanyUserId: $actor) {
    activated { code }
    deactivated { code }
    changed
  }
}
"""


class FalloControlado(RuntimeError):
    pass


def relaciones(rol_id):
    """Estado persistido de la lista del rol, leído con una sesión nueva."""
    with SessionLocal() as db:
        return sorted(db.execute(select(
            RolePermissionModel.id, RolePermissionModel.permission_id, RolePermissionModel.is_active
        ).where(RolePermissionModel.role_id == rol_id)).all())


class E07ReversionTest(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_rbac(db)
            empresa = Company(name=f"Prueba E07 {uuid4().hex[:8]}")
            ana = User(name="Ana E07", email=f"ana-e07-{uuid4().hex[:8]}@ingresos.example.com",
                       password_hash=hash_password("PruebaE07-2026"))
            db.add_all([empresa, ana])
            db.flush()
            membresia = CompanyUser(company_id=empresa.id, user_id=ana.id, is_admin=True)
            db.add(membresia)
            db.flush()
            assign_role_internal(db, membresia, db.scalar(select(RoleModel).where(RoleModel.code == "ADMINISTRADOR")))
            db.commit()
            self.empresa_id, self.usuario_id, self.ana_id = empresa.id, ana.id, membresia.id
            self.capturista_id = db.scalar(select(RoleModel.id).where(RoleModel.code == "CAPTURISTA"))
            self.catalogo = {p.code: p.id for p in db.scalars(select(PermissionModel).where(PermissionModel.is_active.is_(True)))}

    def tearDown(self):
        with SessionLocal() as db:
            for modelo, filtro in (
                (CompanyUserRoleModel, CompanyUserRoleModel.company_user_id == self.ana_id),
                (CompanyUser, CompanyUser.id == self.ana_id),
                (User, User.id == self.usuario_id),
                (Company, Company.id == self.empresa_id),
            ):
                for fila in db.scalars(select(modelo).where(filtro)).all():
                    db.delete(fila)
                db.flush()
            db.commit()

    def test_fallo_despues_del_flush_revierte_toda_la_lista(self):
        antes = relaciones(self.capturista_id)
        activos = {pid for _, pid, activo in antes if activo}
        codigos = {pid: code for code, pid in self.catalogo.items()}
        faltantes = sorted(pid for pid in self.catalogo.values() if pid not in activos)
        self.assertTrue(activos and faltantes, "CAPTURISTA necesita al menos un permiso activo y uno sin asignar")
        quitar, agregar = min(activos), faltantes[0]
        deseada = sorted(activos - {quitar} | {agregar})

        visto_tras_flush = {}

        def aplicar_y_fallar(db, plan):
            apply_role_permission_plan(db, plan)  # hace flush: las escrituras ya llegaron a MySQL
            visto_tras_flush.update(db.execute(select(
                RolePermissionModel.permission_id, RolePermissionModel.is_active
            ).where(RolePermissionModel.role_id == self.capturista_id)).all())
            raise FalloControlado("fallo controlado después del flush y antes del commit")

        # Strawberry registra la excepción con su traza; aquí se espera, así que no se imprime.
        with mock.patch.object(schema_module, "apply_role_permission_plan", side_effect=aplicar_y_fallar), \
                mock.patch.object(logging.getLogger("strawberry.execution"), "disabled", True):
            resultado = schema.execute_sync(APLICAR, variable_values={
                "actor": str(self.ana_id),
                "input": {"roleId": str(self.capturista_id), "permissionIds": [str(pid) for pid in deseada]},
            })

        # El fallo ocurrió con las escrituras pendientes ya enviadas por flush.
        self.assertTrue(visto_tras_flush[agregar], f"{codigos[agregar]} debía verse activo tras el flush")
        self.assertFalse(visto_tras_flush[quitar], f"{codigos[quitar]} debía verse inactivo tras el flush")
        # GraphQL informa el error y no inventa un resultado.
        self.assertIsNone(resultado.data["setRolePermissions"])
        self.assertIn("fallo controlado", resultado.errors[0].message)
        # Desde una sesión nueva la lista es exactamente la anterior: mismos ids, mismas parejas, mismos estados.
        self.assertEqual(relaciones(self.capturista_id), antes)


if __name__ == "__main__":
    unittest.main()
