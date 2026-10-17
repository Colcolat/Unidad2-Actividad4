from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session
from graphql import GraphQLError

from app.models import Company, CompanyUser, User
from app.rbac_models import CompanyUserRoleModel, PermissionModel, RoleModel, RolePermissionModel


ROLE_NAMES = {
    "ADMINISTRADOR": "Administrador",
    "CONTADOR": "Contador",
    "CAPTURISTA": "Capturista",
    "CONSULTA": "Consulta",
}

PERMISSION_NAMES = {
    "company.users.read": "Consultar membresías",
    "company.users.write": "Administrar membresías",
    "accounts.read": "Consultar cuentas",
    "accounts.write": "Crear cuentas",
    "concepts.read": "Consultar conceptos",
    "concepts.write": "Administrar conceptos",
    "transactions.read": "Consultar movimientos",
    "transactions.write": "Registrar movimientos",
    "roles.read": "Consultar roles y permisos",
    "roles.write": "Administrar roles y permisos",
}

PERMISSION_MATRIX = {
    "ADMINISTRADOR": list(PERMISSION_NAMES),
    "CONTADOR": [
        "company.users.read", "accounts.read", "accounts.write", "concepts.read",
        "concepts.write", "transactions.read", "transactions.write", "roles.read",
    ],
    "CAPTURISTA": ["accounts.read", "concepts.read", "transactions.read", "transactions.write"],
    "CONSULTA": ["company.users.read", "accounts.read", "concepts.read", "transactions.read"],
}


def seed_rbac(db: Session) -> None:
    for code, name in ROLE_NAMES.items():
        if db.scalar(select(RoleModel).where(RoleModel.code == code)) is None:
            db.add(RoleModel(code=code, name=name, description=name))
    for code, name in PERMISSION_NAMES.items():
        if db.scalar(select(PermissionModel).where(PermissionModel.code == code)) is None:
            db.add(PermissionModel(code=code, name=name, description=name))
    db.flush()
    roles = {r.code: r for r in db.scalars(select(RoleModel)).all()}
    permissions = {p.code: p for p in db.scalars(select(PermissionModel)).all()}
    for role_code, codes in PERMISSION_MATRIX.items():
        role = roles[role_code]
        # Un rol con filas, aunque todas estén inactivas, ya se inicializó: su lista vacía fue decidida
        # con setRolePermissions y no se vuelve a cargar la matriz.
        found = db.scalar(select(RolePermissionModel.id).where(RolePermissionModel.role_id == role.id).limit(1))
        if found is not None:
            continue
        for code in codes:
            entry = db.scalar(select(RolePermissionModel).where(RolePermissionModel.role_id == role.id, RolePermissionModel.permission_id == permissions[code].id))
            if entry is None:
                db.add(RolePermissionModel(role_id=role.id, permission_id=permissions[code].id))
            else:
                entry.is_active = True
    db.flush()
    memberships = db.scalars(select(CompanyUser).where(CompanyUser.is_active.is_(True))).all()
    for membership in memberships:
        active = db.scalar(select(CompanyUserRoleModel.id).where(CompanyUserRoleModel.company_user_id == membership.id, CompanyUserRoleModel.is_active.is_(True)))
        if active is None:
            code = "ADMINISTRADOR" if membership.is_admin else "CONSULTA"
            assign_role_internal(db, membership, roles[code])
    db.commit()


def assign_role_internal(db: Session, membership: CompanyUser, role: RoleModel) -> CompanyUserRoleModel:
    if not membership.is_active or not membership.company.is_active or not membership.user.is_active:
        raise GraphQLError("La membresía, empresa o usuario está inactivo.")
    if not role.is_active:
        raise GraphQLError("El rol está inactivo.")
    if membership.is_admin and role.code != "ADMINISTRADOR":
        raise GraphQLError("El administrador principal debe mantener el rol ADMINISTRADOR.")
    if not membership.is_admin and role.code == "ADMINISTRADOR":
        raise GraphQLError("El rol ADMINISTRADOR está reservado al administrador principal.")
    active = db.scalars(select(CompanyUserRoleModel).where(CompanyUserRoleModel.company_user_id == membership.id, CompanyUserRoleModel.is_active.is_(True))).all()
    if len(active) == 1 and active[0].role_id == role.id:
        return active[0]
    for entry in active:
        entry.is_active = False
    existing = db.scalar(select(CompanyUserRoleModel).where(CompanyUserRoleModel.company_user_id == membership.id, CompanyUserRoleModel.role_id == role.id))
    if existing is None:
        existing = CompanyUserRoleModel(company_user_id=membership.id, role_id=role.id)
        db.add(existing)
    else:
        existing.is_active = True
    db.flush()
    return existing


def exigir_permiso(db: Session, company_user_id: int, codigo: str, company_id: int | None = None) -> CompanyUser:
    member = db.get(CompanyUser, company_user_id)
    if member is None or not member.is_active or not member.user.is_active or not member.company.is_active:
        raise GraphQLError("La membresía no existe o está inactiva.")
    if company_id is not None and member.company_id != company_id:
        raise GraphQLError("Los datos no pertenecen a la empresa de esta membresía.")
    assignment = db.scalar(select(CompanyUserRoleModel).join(RoleModel).where(
        CompanyUserRoleModel.company_user_id == company_user_id,
        CompanyUserRoleModel.is_active.is_(True), RoleModel.is_active.is_(True)))
    if assignment is None:
        raise GraphQLError("La membresía no tiene un rol activo.")
    allowed = db.scalar(select(RolePermissionModel.id).join(PermissionModel).where(
        RolePermissionModel.role_id == assignment.role_id,
        RolePermissionModel.is_active.is_(True),
        PermissionModel.code == codigo, PermissionModel.is_active.is_(True)))
    if allowed is None:
        raise GraphQLError(f"El rol no tiene el permiso {codigo}.")
    return member


# Prefijo del código de permiso que corresponde a cada valor del enum PermissionResource.
RESOURCE_PREFIXES = {
    "COMPANY_USERS": "company.users.",
    "ACCOUNTS": "accounts.",
    "CONCEPTS": "concepts.",
    "TRANSACTIONS": "transactions.",
    "ROLES": "roles.",
}

# Regla del laboratorio: la lista del administrador no se cambia con setRolePermissions.
PROTECTED_ROLE = "ADMINISTRADOR"


def parse_id(value, label: str) -> int:
    """Convierte un ID de GraphQL a entero. "3" y 3 llegan como el mismo id."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        number = 0
    if number <= 0:
        raise GraphQLError(f"{label} {value!r} no es un id válido.")
    return number


@dataclass
class RolePermissionPlan:
    role: RoleModel
    current: list[PermissionModel]
    to_activate: list[PermissionModel]
    to_deactivate: list[PermissionModel]
    unchanged: list[PermissionModel]

    @property
    def final_count(self) -> int:
        return len(self.to_activate) + len(self.unchanged)

    @property
    def changed(self) -> bool:
        return bool(self.to_activate or self.to_deactivate)


def by_code(permissions) -> list[PermissionModel]:
    return sorted(permissions, key=lambda permission: permission.code)


def plan_role_permissions(db: Session, role_id, permission_ids) -> RolePermissionPlan:
    """Valida la lista deseada y la compara con la lista activa. Solo lee: no agrega ni cambia filas.

    La usan previewRolePermissions y setRolePermissions, así las dos calculan igual las diferencias.
    """
    role = db.get(RoleModel, parse_id(role_id, "El rol"))
    if role is None:
        raise GraphQLError(f"El rol {role_id} no existe.")
    if not role.is_active:
        raise GraphQLError(f"El rol {role.code} está inactivo.")
    if role.code == PROTECTED_ROLE:
        raise GraphQLError(f"La lista del rol {PROTECTED_ROLE} no se configura con esta operación.")

    desired_ids: list[int] = []
    for value in permission_ids:
        number = parse_id(value, "El permiso")
        if number in desired_ids:
            raise GraphQLError(f"El permiso {number} viene repetido en la lista. Cada permiso se envía una sola vez.")
        desired_ids.append(number)

    desired = {p.id: p for p in db.scalars(select(PermissionModel).where(PermissionModel.id.in_(desired_ids))).all()}
    missing = [str(number) for number in desired_ids if number not in desired]
    if missing:
        raise GraphQLError(f"Los permisos {', '.join(missing)} no existen.")
    inactive = [p.code for p in by_code(desired.values()) if not p.is_active]
    if inactive:
        raise GraphQLError(f"Los permisos {', '.join(inactive)} están inactivos en el catálogo.")

    current = db.scalars(select(PermissionModel).join(
        RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id
    ).where(
        RolePermissionModel.role_id == role.id,
        RolePermissionModel.is_active.is_(True),
        PermissionModel.is_active.is_(True),
    )).all()
    current_ids = {p.id for p in current}
    return RolePermissionPlan(
        role=role,
        current=by_code(current),
        to_activate=by_code(p for p in desired.values() if p.id not in current_ids),
        to_deactivate=by_code(p for p in current if p.id not in desired),
        unchanged=by_code(p for p in current if p.id in desired),
    )


def apply_role_permission_plan(db: Session, plan: RolePermissionPlan) -> None:
    """Escribe el plan en la sesión y hace flush. No confirma: el commit lo hace la operación completa."""
    changed_ids = [p.id for p in plan.to_activate + plan.to_deactivate]
    relations = {r.permission_id: r for r in db.scalars(select(RolePermissionModel).where(
        RolePermissionModel.role_id == plan.role.id,
        RolePermissionModel.permission_id.in_(changed_ids),
    )).all()}
    for permission in plan.to_activate:
        relation = relations.get(permission.id)
        if relation is None:
            db.add(RolePermissionModel(role_id=plan.role.id, permission_id=permission.id))
        else:
            # Se reactiva la misma fila: el id de la relación no cambia.
            relation.is_active = True
    for permission in plan.to_deactivate:
        relations[permission.id].is_active = False
    db.flush()
