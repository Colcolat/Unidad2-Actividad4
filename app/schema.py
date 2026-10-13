from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import strawberry

from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from strawberry.schema.config import StrawberryConfig

from app.database import SessionLocal
from app.models import Company, CompanyUser, User
from app.financial_models import Account, AccountConcept, Concept, Transaction, utcnow as financial_utcnow
from app.rbac_models import RoleModel, PermissionModel, RolePermissionModel, CompanyUserRoleModel
from app.rbac import ROLE_NAMES, exigir_permiso, assign_role_internal
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def obtener_actor_usuario(company_user_id: int) -> int:
    with SessionLocal() as db:
        membership = db.get(CompanyUser, company_user_id)
        if membership is None or not membership.is_active:
            raise GraphQLError("La membresía no existe o está inactiva.")
        return membership.user_id


email_adapter = TypeAdapter(EmailStr)



def normalize_email(value: str) -> str:
    try:
        email = email_adapter.validate_python(value)
        return str(email).lower()

    except ValidationError as exc:
        raise GraphQLError(
            "El correo electrónico no es válido."
        ) from exc


def clean_required_text(
    value: str,
    field_name: str
) -> str:

    value = value.strip()

    if not value:
        raise GraphQLError(
            f"{field_name} es obligatorio."
        )

    return value



def get_authenticated_user_id(
    info: strawberry.Info
) -> int:

    request = info.context["request"]

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith("Bearer "):
        raise GraphQLError(
            "Debes autenticarte con un token Bearer."
        )

    token = authorization.removeprefix(
        "Bearer "
    ).strip()

    try:
        return decode_access_token(token)

    except ValueError as exc:
        raise GraphQLError(
            str(exc)
        ) from exc


def ensure_company_admin(
    info: strawberry.Info,
    company_id: int
) -> None:

    user_id = get_authenticated_user_id(info)

    with SessionLocal() as db:

        user = db.get(
            User,
            user_id
        )

        if user is None or not user.is_active:
            raise GraphQLError(
                "Usuario autenticado no válido o inactivo."
            )

        relation = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
                CompanyUser.is_admin.is_(True),
                CompanyUser.is_active.is_(True),
            )
        )

        if relation is None:
            raise GraphQLError(
                "Solo el administrador de la empresa "
                "puede registrar usuarios."
            )



@strawberry.type(name="Company")
class CompanyType:
    id: strawberry.ID
    name: str
    legal_name: Optional[str]
    tax_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type(name="User")
class UserType:
    id: strawberry.ID
    name: str
    email: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type(name="CompanyUser")
class CompanyUserType:
    id: strawberry.ID
    company_id: strawberry.ID
    user_id: strawberry.ID
    is_admin: bool
    is_active: bool
    joined_at: datetime
    company: CompanyType
    user: UserType


@strawberry.type
class AuthUser:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class AuthPayload:
    token: str
    token_type: str
    user: AuthUser


@strawberry.enum(name="AccountType")
class AccountTypeEnum(Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum(name="ConceptType")
class ConceptTypeEnum(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum(name="TransactionType")
class TransactionTypeEnum(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.type(name="Account")
class AccountGraphQL:
    id: strawberry.ID
    company_id: strawberry.ID
    account_type: AccountTypeEnum
    name: str
    bank_name: Optional[str]
    account_number: Optional[str]
    clabe: Optional[str]
    card_last_digits: Optional[str]
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company: CompanyType


@strawberry.type(name="Concept")
class ConceptGraphQL:
    id: strawberry.ID
    company_id: strawberry.ID
    concept_type: ConceptTypeEnum
    name: str
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company: CompanyType


@strawberry.type(name="AccountConcept")
class AccountConceptGraphQL:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    is_active: bool
    created_at: datetime
    account: AccountGraphQL
    concept: ConceptGraphQL


@strawberry.type(name="Transaction")
class TransactionGraphQL:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionTypeEnum
    amount: Decimal
    transaction_date: datetime
    captured_at: datetime
    captured_by: strawberry.ID
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    account: AccountGraphQL
    concept: ConceptGraphQL
    captured_by_user: UserType



@strawberry.input
class CreateCompanyInput:
    name: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@strawberry.input
class UpdateCompanyInput:
    id: strawberry.ID
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class CreateCompanyAdminInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateCompanyUserInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateAccountInput:
    company_id: strawberry.ID
    account_type: AccountTypeEnum
    name: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    clabe: Optional[str] = None
    card_last_digits: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class CreateConceptInput:
    company_id: strawberry.ID
    concept_type: ConceptTypeEnum
    name: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class AssignConceptToAccountInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID


@strawberry.input
class CreateTransactionInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionTypeEnum
    amount: Decimal
    transaction_date: Optional[datetime] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None



def company_to_type(
    company: Company
) -> CompanyType:

    return CompanyType(
        id=strawberry.ID(str(company.id)),
        name=company.name,
        legal_name=company.legal_name,
        tax_id=company.tax_id,
        email=company.email,
        phone=company.phone,
        is_active=company.is_active,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def user_to_type(
    user: User
) -> UserType:

    return UserType(
        id=strawberry.ID(str(user.id)),
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def company_user_to_type(
    company_user: CompanyUser
) -> CompanyUserType:

    return CompanyUserType(
        id=strawberry.ID(
            str(company_user.id)
        ),

        company_id=strawberry.ID(
            str(company_user.company_id)
        ),

        user_id=strawberry.ID(
            str(company_user.user_id)
        ),

        is_admin=company_user.is_admin,
        is_active=company_user.is_active,
        joined_at=company_user.joined_at,

        company=company_to_type(
            company_user.company
        ),

        user=user_to_type(
            company_user.user
        ),
    )



def account_to_type(account: Account) -> AccountGraphQL:
    return AccountGraphQL(
        id=strawberry.ID(str(account.id)),
        company_id=strawberry.ID(str(account.company_id)),
        account_type=AccountTypeEnum(account.account_type),
        name=account.name,
        bank_name=account.bank_name,
        account_number=account.account_number,
        clabe=account.clabe,
        card_last_digits=account.card_last_digits,
        short_description=account.short_description,
        long_description=account.long_description,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        company=company_to_type(account.company),
    )


def concept_to_type(concept: Concept) -> ConceptGraphQL:
    return ConceptGraphQL(
        id=strawberry.ID(str(concept.id)),
        company_id=strawberry.ID(str(concept.company_id)),
        concept_type=ConceptTypeEnum(concept.concept_type),
        name=concept.name,
        short_description=concept.short_description,
        long_description=concept.long_description,
        is_active=concept.is_active,
        created_at=concept.created_at,
        updated_at=concept.updated_at,
        company=company_to_type(concept.company),
    )


def account_concept_to_type(relation: AccountConcept) -> AccountConceptGraphQL:
    return AccountConceptGraphQL(
        id=strawberry.ID(str(relation.id)),
        account_id=strawberry.ID(str(relation.account_id)),
        concept_id=strawberry.ID(str(relation.concept_id)),
        is_active=relation.is_active,
        created_at=relation.created_at,
        account=account_to_type(relation.account),
        concept=concept_to_type(relation.concept),
    )


def transaction_to_type(transaction: Transaction) -> TransactionGraphQL:
    return TransactionGraphQL(
        id=strawberry.ID(str(transaction.id)),
        account_id=strawberry.ID(str(transaction.account_id)),
        concept_id=strawberry.ID(str(transaction.concept_id)),
        transaction_type=TransactionTypeEnum(transaction.transaction_type),
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        captured_at=transaction.captured_at,
        captured_by=strawberry.ID(str(transaction.captured_by)),
        short_description=transaction.short_description,
        long_description=transaction.long_description,
        is_active=transaction.is_active,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        account=account_to_type(transaction.account),
        concept=concept_to_type(transaction.concept),
        captured_by_user=user_to_type(transaction.captured_by_user),
    )



@strawberry.type(name="Role")
class RoleType:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type(name="Permission")
class PermissionType:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type(name="RolePermission")
class RolePermissionType:
    id: strawberry.ID
    role: RoleType
    permission: PermissionType
    is_active: bool


@strawberry.type(name="CompanyUserRole")
class CompanyUserRoleType:
    id: strawberry.ID
    company_user: CompanyUserType
    role: RoleType
    is_active: bool


@strawberry.input(name="CreateRoleInput")
class CreateRoleInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input(name="CreatePermissionInput")
class CreatePermissionInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input(name="AssignPermissionToRoleInput")
class AssignPermissionToRoleInput:
    role_id: strawberry.ID
    permission_id: strawberry.ID


@strawberry.input(name="AssignRoleInput")
class AssignRoleInput:
    company_user_id: strawberry.ID
    role_id: strawberry.ID


def role_to_type(role: RoleModel) -> RoleType:
    return RoleType(id=strawberry.ID(str(role.id)), code=role.code, name=role.name, description=role.description, is_active=role.is_active)


def permission_to_type(permission: PermissionModel) -> PermissionType:
    return PermissionType(id=strawberry.ID(str(permission.id)), code=permission.code, name=permission.name, description=permission.description, is_active=permission.is_active)


def role_permission_to_type(relation: RolePermissionModel) -> RolePermissionType:
    return RolePermissionType(id=strawberry.ID(str(relation.id)), role=role_to_type(relation.role), permission=permission_to_type(relation.permission), is_active=relation.is_active)


def company_user_role_to_type(relation: CompanyUserRoleModel) -> CompanyUserRoleType:
    return CompanyUserRoleType(id=strawberry.ID(str(relation.id)), company_user=company_user_to_type(relation.company_user), role=role_to_type(relation.role), is_active=relation.is_active)


@strawberry.type
class Query:
    @strawberry.field
    def roles(self, active_only: Optional[bool] = None) -> list[RoleType]:
        with SessionLocal() as db:
            stmt = select(RoleModel).order_by(RoleModel.id)
            if active_only is True:
                stmt = stmt.where(RoleModel.is_active.is_(True))
            return [role_to_type(item) for item in db.scalars(stmt).all()]

    @strawberry.field
    def role(self, id: strawberry.ID) -> Optional[RoleType]:
        with SessionLocal() as db:
            item = db.get(RoleModel, int(id))
            return role_to_type(item) if item is not None else None

    @strawberry.field
    def permissions(self, active_only: Optional[bool] = None) -> list[PermissionType]:
        with SessionLocal() as db:
            stmt = select(PermissionModel).order_by(PermissionModel.id)
            if active_only is True:
                stmt = stmt.where(PermissionModel.is_active.is_(True))
            return [permission_to_type(item) for item in db.scalars(stmt).all()]

    @strawberry.field
    def role_permissions(self, role_id: strawberry.ID) -> list[RolePermissionType]:
        with SessionLocal() as db:
            role = db.get(RoleModel, int(role_id))
            if role is None:
                raise GraphQLError("El rol no existe.")
            stmt = select(RolePermissionModel).join(PermissionModel).where(
                RolePermissionModel.role_id == role.id,
                RolePermissionModel.is_active.is_(True), PermissionModel.is_active.is_(True)
            ).order_by(RolePermissionModel.id)
            return [role_permission_to_type(item) for item in db.scalars(stmt).all()]



    @strawberry.field
    def companies(
        self,
        active_only: Optional[bool] = None
    ) -> list[CompanyType]:

        with SessionLocal() as db:

            stmt = select(
                Company
            ).order_by(
                Company.id
            )

            if active_only is True:
                stmt = stmt.where(
                    Company.is_active.is_(True)
                )

            companies = db.scalars(
                stmt
            ).all()

            return [
                company_to_type(company)
                for company in companies
            ]


    @strawberry.field
    def company(
        self,
        id: strawberry.ID
    ) -> Optional[CompanyType]:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(id)
            )

            if company is None:
                return None

            return company_to_type(
                company
            )


    @strawberry.field
    def company_users(
        self,
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID
    ) -> list[CompanyUserType]:

        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "company.users.read", int(company_id))

            company = db.get(
                Company,
                int(company_id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            stmt = (
                select(CompanyUser)
                .where(
                    CompanyUser.company_id
                    == int(company_id)
                )
                .order_by(
                    CompanyUser.id
                )
            )

            relations = db.scalars(
                stmt
            ).all()

            return [
                company_user_to_type(relation)
                for relation in relations
            ]


    @strawberry.field
    def accounts(
        self,
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID,
        account_type: Optional[AccountTypeEnum] = None,
        active_only: Optional[bool] = None,
    ) -> list[AccountGraphQL]:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "accounts.read", int(company_id))
            company = db.get(Company, int(company_id))
            if company is None:
                raise GraphQLError("La empresa no existe.")

            stmt = select(Account).where(Account.company_id == int(company_id))
            if account_type is not None:
                stmt = stmt.where(Account.account_type == account_type.value)
            if active_only is True:
                stmt = stmt.where(Account.is_active.is_(True))
            stmt = stmt.order_by(Account.id)

            return [account_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def concepts(
        self,
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID,
        concept_type: Optional[ConceptTypeEnum] = None,
        active_only: Optional[bool] = None,
    ) -> list[ConceptGraphQL]:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "concepts.read", int(company_id))
            company = db.get(Company, int(company_id))
            if company is None:
                raise GraphQLError("La empresa no existe.")

            stmt = select(Concept).where(Concept.company_id == int(company_id))
            if concept_type is not None:
                stmt = stmt.where(Concept.concept_type == concept_type.value)
            if active_only is True:
                stmt = stmt.where(Concept.is_active.is_(True))
            stmt = stmt.order_by(Concept.id)

            return [concept_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def account_concepts(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: strawberry.ID,
    ) -> list[AccountConceptGraphQL]:
        with SessionLocal() as db:
            account = db.get(Account, int(account_id))
            if account is None:
                raise GraphQLError("La cuenta no existe.")
            exigir_permiso(db, int(actor_company_user_id), "concepts.read", account.company_id)

            stmt = (
                select(AccountConcept)
                .where(AccountConcept.account_id == int(account_id))
                .order_by(AccountConcept.id)
            )
            return [account_concept_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def transactions(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: Optional[strawberry.ID] = None,
        transaction_type: Optional[TransactionTypeEnum] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[TransactionGraphQL]:
        real_limit = 100 if limit is None else limit
        real_offset = 0 if offset is None else offset

        if real_limit <= 0 or real_limit > 100:
            raise GraphQLError("El limit debe estar entre 1 y 100.")
        if real_offset < 0:
            raise GraphQLError("El offset no puede ser negativo.")

        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "transactions.read")
            stmt = select(Transaction).join(Account).where(
                Transaction.is_active.is_(True),
                Account.company_id == actor.company_id
            )
            if account_id is not None:
                stmt = stmt.where(Transaction.account_id == int(account_id))
            if transaction_type is not None:
                stmt = stmt.where(Transaction.transaction_type == transaction_type.value)
            stmt = stmt.order_by(Transaction.id).limit(real_limit).offset(real_offset)

            return [transaction_to_type(item) for item in db.scalars(stmt).all()]



@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_role(self, input: CreateRoleInput) -> RoleType:
        code = clean_required_text(input.code, "El código").upper()
        name = clean_required_text(input.name, "El nombre")
        with SessionLocal() as db:
            if db.scalar(select(RoleModel).where(RoleModel.code == code)) is not None:
                raise GraphQLError("El código del rol ya existe.")
            row = RoleModel(code=code, name=name, description=input.description)
            db.add(row)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear el rol.") from exc
            db.refresh(row)
            return role_to_type(row)

    @strawberry.mutation
    def deactivate_role(self, id: strawberry.ID, actor_company_user_id: strawberry.ID) -> RoleType:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "roles.write")
            row = db.get(RoleModel, int(id))
            if row is None or not row.is_active:
                raise GraphQLError("El rol no existe o ya está inactivo.")
            row.is_active = False
            db.commit()
            return role_to_type(row)

    @strawberry.mutation
    def create_permission(self, input: CreatePermissionInput) -> PermissionType:
        code = clean_required_text(input.code, "El código").lower()
        name = clean_required_text(input.name, "El nombre")
        with SessionLocal() as db:
            if db.scalar(select(PermissionModel).where(PermissionModel.code == code)) is not None:
                raise GraphQLError("El código del permiso ya existe.")
            row = PermissionModel(code=code, name=name, description=input.description)
            db.add(row)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear el permiso.") from exc
            db.refresh(row)
            return permission_to_type(row)

    @strawberry.mutation
    def assign_permission_to_role(self, input: AssignPermissionToRoleInput, actor_company_user_id: strawberry.ID) -> RolePermissionType:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "roles.write")
            role = db.get(RoleModel, int(input.role_id))
            permission = db.get(PermissionModel, int(input.permission_id))
            if role is None or not role.is_active or permission is None or not permission.is_active:
                raise GraphQLError("El rol o permiso no existe o está inactivo.")
            relation = db.scalar(select(RolePermissionModel).where(
                RolePermissionModel.role_id == role.id, RolePermissionModel.permission_id == permission.id
            ))
            if relation is not None and relation.is_active:
                raise GraphQLError("El permiso ya está asignado a ese rol.")
            if relation is None:
                relation = RolePermissionModel(role_id=role.id, permission_id=permission.id)
                db.add(relation)
            else:
                relation.is_active = True
            db.commit()
            db.refresh(relation)
            return role_permission_to_type(relation)

    @strawberry.mutation
    def remove_permission_from_role(self, role_id: strawberry.ID, permission_id: strawberry.ID, actor_company_user_id: strawberry.ID) -> bool:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "roles.write")
            relation = db.scalar(select(RolePermissionModel).where(
                RolePermissionModel.role_id == int(role_id),
                RolePermissionModel.permission_id == int(permission_id),
                RolePermissionModel.is_active.is_(True)
            ))
            if relation is None:
                raise GraphQLError("El rol no tiene ese permiso activo.")
            relation.is_active = False
            db.commit()
            return True

    @strawberry.mutation
    def assign_role(self, input: AssignRoleInput, actor_company_user_id: strawberry.ID) -> CompanyUserRoleType:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "roles.write")
            membership = db.get(CompanyUser, int(input.company_user_id))
            role = db.get(RoleModel, int(input.role_id))
            if membership is None or role is None:
                raise GraphQLError("La membresía o el rol no existe.")
            if membership.company_id != actor.company_id:
                raise GraphQLError("No se puede asignar un rol en otra empresa.")
            assignment = assign_role_internal(db, membership, role)
            db.commit()
            db.refresh(assignment)
            return company_user_role_to_type(assignment)




    @strawberry.mutation
    def create_company(
        self,
        input: CreateCompanyInput
    ) -> CompanyType:

        with SessionLocal() as db:

            email = (
                normalize_email(input.email)
                if input.email
                else None
            )

            tax_id = (
                input.tax_id.strip().upper()
                if input.tax_id
                else None
            )

            if tax_id:

                existing_tax = db.scalar(
                    select(Company).where(
                        Company.tax_id == tax_id
                    )
                )

                if existing_tax:
                    raise GraphQLError(
                        "El taxId ya está registrado."
                    )

            company = Company(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),

                legal_name=(
                    input.legal_name.strip()
                    if input.legal_name
                    else None
                ),

                tax_id=tax_id,
                email=email,

                phone=(
                    input.phone.strip()
                    if input.phone
                    else None
                ),
            )

            db.add(company)
            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )



    @strawberry.mutation
    def update_company(
        self,
        input: UpdateCompanyInput
    ) -> CompanyType:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(input.id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if input.name is not None:

                company.name = clean_required_text(
                    input.name,
                    "El nombre"
                )

            if input.legal_name is not None:

                company.legal_name = (
                    input.legal_name.strip()
                    or None
                )

            if input.tax_id is not None:

                new_tax_id = (
                    input.tax_id.strip().upper()
                    or None
                )

                if new_tax_id:

                    existing = db.scalar(
                        select(Company).where(
                            Company.tax_id == new_tax_id,
                            Company.id != company.id
                        )
                    )

                    if existing:
                        raise GraphQLError(
                            "El taxId ya está registrado."
                        )

                company.tax_id = new_tax_id

            if input.email is not None:

                company.email = (
                    normalize_email(input.email)
                    if input.email.strip()
                    else None
                )

            if input.phone is not None:

                company.phone = (
                    input.phone.strip()
                    or None
                )

            if input.is_active is not None:

                company.is_active = (
                    input.is_active
                )

            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )



    @strawberry.mutation
    def deactivate_company(
        self,
        id: strawberry.ID
    ) -> CompanyType:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa ya está desactivada."
                )

            company.is_active = False

            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )



    @strawberry.mutation
    def create_company_admin(
        self,
        input: CreateCompanyAdminInput
    ) -> CompanyUserType:

        with SessionLocal() as db:

            company_id = int(
                input.company_id
            )

            company = db.get(
                Company,
                company_id
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa está inactiva."
                )

            existing_admin = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id
                    == company_id,

                    CompanyUser.is_admin.is_(
                        True
                    ),

                    CompanyUser.is_active.is_(
                        True
                    ),
                )
            )

            if existing_admin:
                raise GraphQLError(
                    "La empresa ya tiene "
                    "un administrador principal."
                )

            email = normalize_email(
                input.email
            )

            existing_user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if existing_user:
                raise GraphQLError(
                    "El correo electrónico "
                    "ya está registrado."
                )

            try:

                password_hash = hash_password(
                    input.password
                )

            except ValueError as exc:

                raise GraphQLError(
                    str(exc)
                ) from exc

            user = User(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),
                email=email,
                password_hash=password_hash,
            )

            db.add(user)
            db.flush()

            company_user = CompanyUser(
                company_id=company_id,
                user_id=user.id,
                is_admin=True,
            )

            db.add(company_user)
            db.flush()
            admin_role = db.scalar(select(RoleModel).where(RoleModel.code == "ADMINISTRADOR"))
            if admin_role is None:
                raise GraphQLError("No existe el rol ADMINISTRADOR.")
            assign_role_internal(db, company_user, admin_role)

            try:

                db.commit()

            except IntegrityError as exc:

                db.rollback()

                raise GraphQLError(
                    "No se pudo crear "
                    "el administrador."
                ) from exc

            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )



    @strawberry.mutation
    def create_company_user(
        self,
        actor_company_user_id: strawberry.ID,
        info: strawberry.Info,
        input: CreateCompanyUserInput
    ) -> CompanyUserType:

        company_id = int(
            input.company_id
        )

        with SessionLocal() as db:

            company = db.get(
                Company,
                company_id
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa está inactiva."
                )

        if get_authenticated_user_id(info) != obtener_actor_usuario(int(actor_company_user_id)):
            raise GraphQLError("El token no corresponde a la membresía que actúa.")

        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "company.users.write", company_id)

        with SessionLocal() as db:

            email = normalize_email(
                input.email
            )

            existing_user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if existing_user:
                raise GraphQLError(
                    "El correo electrónico "
                    "ya está registrado."
                )

            try:

                password_hash = hash_password(
                    input.password
                )

            except ValueError as exc:

                raise GraphQLError(
                    str(exc)
                ) from exc

            user = User(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),
                email=email,
                password_hash=password_hash,
            )

            db.add(user)
            db.flush()

            company_user = CompanyUser(
                company_id=company_id,
                user_id=user.id,
                is_admin=False,
            )

            db.add(company_user)
            db.flush()
            default_role = db.scalar(select(RoleModel).where(RoleModel.code == "CONSULTA"))
            if default_role is None:
                raise GraphQLError("No existe el rol CONSULTA.")
            assign_role_internal(db, company_user, default_role)

            try:

                db.commit()

            except IntegrityError as exc:

                db.rollback()

                raise GraphQLError(
                    "No se pudo registrar "
                    "el usuario."
                ) from exc

            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )



    @strawberry.mutation
    def deactivate_company_user(
        self,
        actor_company_user_id: strawberry.ID,
        info: strawberry.Info,
        id: strawberry.ID
    ) -> CompanyUserType:

        with SessionLocal() as db:

            company_user = db.get(
                CompanyUser,
                int(id)
            )

            if company_user is None:
                raise GraphQLError(
                    "La relación empresa-usuario "
                    "no existe."
                )

            company_id = (
                company_user.company_id
            )

        if get_authenticated_user_id(info) != obtener_actor_usuario(int(actor_company_user_id)):
            raise GraphQLError("El token no corresponde a la membresía que actúa.")

        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "company.users.write", company_id)

        with SessionLocal() as db:

            company_user = db.get(
                CompanyUser,
                int(id)
            )

            if company_user is None:
                raise GraphQLError(
                    "La relación empresa-usuario "
                    "no existe."
                )

            if company_user.is_admin:
                raise GraphQLError(
                    "No se puede desactivar "
                    "al administrador principal "
                    "desde esta operación."
                )

            if not company_user.is_active:
                raise GraphQLError(
                    "El usuario ya está "
                    "desactivado para esta empresa."
                )

            company_user.is_active = False

            db.commit()
            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )



    @strawberry.mutation
    def create_account(self, actor_company_user_id: strawberry.ID, input: CreateAccountInput) -> AccountGraphQL:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "accounts.write", int(input.company_id))
            company_id = int(input.company_id)
            company = db.get(Company, company_id)
            if company is None:
                raise GraphQLError("La empresa no existe.")
            if not company.is_active:
                raise GraphQLError("La empresa está inactiva.")

            name = clean_required_text(input.name, "El nombre de la cuenta")
            existing = db.scalar(
                select(Account).where(
                    Account.company_id == company_id,
                    Account.name == name,
                )
            )
            if existing:
                raise GraphQLError("Ya existe una cuenta con ese nombre en la empresa.")

            account = Account(
                company_id=company_id,
                account_type=input.account_type.value,
                name=name,
                bank_name=input.bank_name.strip() if input.bank_name and input.bank_name.strip() else None,
                account_number=input.account_number.strip() if input.account_number and input.account_number.strip() else None,
                clabe=input.clabe.strip() if input.clabe and input.clabe.strip() else None,
                card_last_digits=input.card_last_digits.strip() if input.card_last_digits and input.card_last_digits.strip() else None,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(account)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear la cuenta porque el registro está duplicado.") from exc
            db.refresh(account)
            return account_to_type(account)


    @strawberry.mutation
    def create_concept(self, actor_company_user_id: strawberry.ID, input: CreateConceptInput) -> ConceptGraphQL:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "concepts.write", int(input.company_id))
            company_id = int(input.company_id)
            company = db.get(Company, company_id)
            if company is None:
                raise GraphQLError("La empresa no existe.")
            if not company.is_active:
                raise GraphQLError("La empresa está inactiva.")

            name = clean_required_text(input.name, "El nombre del concepto")
            existing = db.scalar(
                select(Concept).where(
                    Concept.company_id == company_id,
                    Concept.concept_type == input.concept_type.value,
                    Concept.name == name,
                )
            )
            if existing:
                raise GraphQLError("Ya existe ese concepto del mismo tipo en la empresa.")

            concept = Concept(
                company_id=company_id,
                concept_type=input.concept_type.value,
                name=name,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(concept)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear el concepto porque el registro está duplicado.") from exc
            db.refresh(concept)
            return concept_to_type(concept)


    @strawberry.mutation
    def assign_concept_to_account(
        self,
        actor_company_user_id: strawberry.ID,
        input: AssignConceptToAccountInput,
    ) -> AccountConceptGraphQL:
        with SessionLocal() as db:
            account = db.get(Account, int(input.account_id))
            concept = db.get(Concept, int(input.concept_id))

            if account is None:
                raise GraphQLError("La cuenta no existe.")
            if concept is None:
                raise GraphQLError("El concepto no existe.")
            if not account.is_active:
                raise GraphQLError("La cuenta está inactiva.")
            if not concept.is_active:
                raise GraphQLError("El concepto está inactivo.")
            if account.company_id != concept.company_id:
                raise GraphQLError("La cuenta y el concepto deben pertenecer a la misma empresa.")
            exigir_permiso(db, int(actor_company_user_id), "concepts.write", account.company_id)

            existing = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == account.id,
                    AccountConcept.concept_id == concept.id,
                )
            )
            if existing:
                if existing.is_active:
                    raise GraphQLError("El concepto ya está asignado a la cuenta.")
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                return account_concept_to_type(existing)

            relation = AccountConcept(account_id=account.id, concept_id=concept.id)
            db.add(relation)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("La relación cuenta-concepto ya existe.") from exc
            db.refresh(relation)
            return account_concept_to_type(relation)


    @strawberry.mutation
    def remove_concept_from_account(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: strawberry.ID,
        concept_id: strawberry.ID,
    ) -> bool:
        with SessionLocal() as db:
            relation = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == int(account_id),
                    AccountConcept.concept_id == int(concept_id),
                )
            )
            if relation is None:
                raise GraphQLError("La relación cuenta-concepto no existe.")
            exigir_permiso(db, int(actor_company_user_id), "concepts.write", relation.account.company_id)
            if not relation.is_active:
                raise GraphQLError("La relación cuenta-concepto ya está desactivada.")

            relation.is_active = False
            db.commit()
            return True



    @strawberry.mutation
    def create_transaction(
        self,
        actor_company_user_id: strawberry.ID,
        info: strawberry.Info,
        input: CreateTransactionInput,
    ) -> TransactionGraphQL:
        user_id = get_authenticated_user_id(info)

        with SessionLocal() as db:
            user = db.get(User, user_id)
            if user is None or not user.is_active:
                raise GraphQLError("Usuario autenticado no válido o inactivo.")

            account = db.get(Account, int(input.account_id))
            if account is None:
                raise GraphQLError("La cuenta no existe.")
            if not account.is_active:
                raise GraphQLError("La cuenta está inactiva.")

            concept = db.get(Concept, int(input.concept_id))
            if concept is None:
                raise GraphQLError("El concepto no existe.")
            if not concept.is_active:
                raise GraphQLError("El concepto está inactivo.")

            if account.company_id != concept.company_id:
                raise GraphQLError("La cuenta y el concepto deben pertenecer a la misma empresa.")

            company_user = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id == account.company_id,
                    CompanyUser.user_id == user_id,
                    CompanyUser.is_active.is_(True),
                )
            )
            if company_user is None:
                raise GraphQLError("El usuario autenticado no pertenece de forma activa a la empresa de la cuenta.")
            if company_user.id != int(actor_company_user_id):
                raise GraphQLError("El token no corresponde a la membresía que actúa.")
            exigir_permiso(db, int(actor_company_user_id), "transactions.write", account.company_id)

            allowed = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == account.id,
                    AccountConcept.concept_id == concept.id,
                    AccountConcept.is_active.is_(True),
                )
            )
            if allowed is None:
                raise GraphQLError("El concepto no está permitido para la cuenta seleccionada.")

            if input.transaction_type.value != concept.concept_type:
                raise GraphQLError("El tipo de movimiento no es compatible con el tipo de concepto.")

            amount = Decimal(input.amount)
            if amount <= 0:
                raise GraphQLError("El monto del movimiento debe ser mayor que cero.")

            now = financial_utcnow()
            transaction = Transaction(
                account_id=account.id,
                concept_id=concept.id,
                transaction_type=input.transaction_type.value,
                amount=amount,
                transaction_date=input.transaction_date or now,
                captured_at=now,
                captured_by=user_id,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            return transaction_to_type(transaction)


    @strawberry.mutation
    def delete_transaction(
        self,
        actor_company_user_id: strawberry.ID,
        info: strawberry.Info,
        id: strawberry.ID,
    ) -> TransactionGraphQL:
        user_id = get_authenticated_user_id(info)

        with SessionLocal() as db:
            transaction = db.get(Transaction, int(id))
            if transaction is None:
                raise GraphQLError("El movimiento no existe.")
            if not transaction.is_active:
                raise GraphQLError("El movimiento ya está eliminado.")

            company_user = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id == transaction.account.company_id,
                    CompanyUser.user_id == user_id,
                    CompanyUser.is_active.is_(True),
                )
            )
            if company_user is None:
                raise GraphQLError("El usuario autenticado no pertenece de forma activa a la empresa del movimiento.")
            if company_user.id != int(actor_company_user_id):
                raise GraphQLError("El token no corresponde a la membresía que actúa.")
            exigir_permiso(db, int(actor_company_user_id), "transactions.write", transaction.account.company_id)

            transaction.is_active = False
            db.commit()
            db.refresh(transaction)
            return transaction_to_type(transaction)



    @strawberry.mutation
    def login(
        self,
        input: LoginInput
    ) -> AuthPayload:

        email = normalize_email(
            input.email
        )

        with SessionLocal() as db:

            user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if (
                user is None
                or not user.is_active
                or not verify_password(
                    input.password,
                    user.password_hash
                )
            ):
                raise GraphQLError(
                    "Correo electrónico o "
                    "contraseña incorrectos."
                )

            token = create_access_token(
                user.id
            )

            return AuthPayload(
                token=token,
                token_type="Bearer",

                user=AuthUser(
                    id=strawberry.ID(
                        str(user.id)
                    ),
                    name=user.name,
                    email=user.email,
                ),
            )



schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,

    config=StrawberryConfig(
        scalar_map={
            datetime: strawberry.scalar(
                name="Time",

                description=(
                    "Fecha y hora "
                    "en formato ISO-8601"
                ),

                serialize=lambda value: (
                    value.isoformat()
                ),

                parse_value=lambda value: (
                    datetime.fromisoformat(
                        value
                    )
                ),
            )
        }
    ),
)
