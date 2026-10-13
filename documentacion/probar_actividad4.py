"""Pruebas de la Unidad II, Actividad 4: configuración de permisos por rol.

Requiere el servidor activo (uvicorn app.main:app --reload) y MySQL en marcha.
Uso, desde la carpeta del proyecto:
  python documentacion/probar_actividad4.py              corre las cuatro partes completas
  python documentacion/probar_actividad4.py --preparar   solo crea la empresa y las cinco personas,
                                                         y escribe la guía de capturas con sus id
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

URL = os.getenv("GRAPHQL_URL", "http://127.0.0.1:8000/graphql")
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://actividad4:actividad4@127.0.0.1:3307/actividad4_db")
PREPARAR = "--preparar" in sys.argv
EVIDENCIAS = RAIZ / "evidencias" / "actividad4"
SALIDA = EVIDENCIAS / ("preparacion" if PREPARAR else "json")
SALIDA.mkdir(parents=True, exist_ok=True)
engine = create_engine(DATABASE_URL)

# La tabla del documento de la actividad: es la configuración que debe existir al empezar y al terminar.
TABLA = {
    "ADMINISTRADOR": {
        "company.users.read", "company.users.write", "accounts.read", "accounts.write", "concepts.read",
        "concepts.write", "transactions.read", "transactions.write", "roles.read", "roles.write",
    },
    "CONTADOR": {
        "company.users.read", "accounts.read", "accounts.write", "concepts.read", "concepts.write",
        "transactions.read", "transactions.write", "roles.read",
    },
    "CAPTURISTA": {"accounts.read", "concepts.read", "transactions.read", "transactions.write"},
    "CONSULTA": {"company.users.read", "accounts.read", "concepts.read", "transactions.read"},
}

SELECT_ROLE_PERMISSIONS = """
SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code
"""


def ejecutar(nombre, consulta, token=None, error=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(URL, data=json.dumps({"query": consulta}).encode(), headers=headers)
    with urlopen(request, timeout=30) as response:
        resultado = json.load(response)
    visible = json.loads(json.dumps(resultado))
    if "login" in (visible.get("data") or {}):
        visible["data"]["login"]["token"] = "OCULTO"
    (SALIDA / f"{nombre}.json").write_text(json.dumps(visible, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if bool(resultado.get("errors")) != error:
        raise AssertionError(f"Resultado inesperado en {nombre}: {resultado}")
    detalle = f" -> {resultado['errors'][0]['message']}" if error else ""
    print(f"  {'RECHAZADO' if error else 'CORRECTO '}: {nombre}{detalle}")
    return resultado.get("data", {})


def sql(consulta, **parametros):
    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros).all()


def codigo(texto):
    return json.dumps(texto, ensure_ascii=False)


def guardar_identificadores():
    (SALIDA / "identificadores.json").write_text(json.dumps({
        "empresa_id": empresa_id, "cuenta_id": cuenta_id, "concepto_id": concepto_id,
        "membresias": {"Ana": ana_id, **{nombre: datos[0] for nombre, datos in personas.items()}},
        "correos": {nombre: correo(nombre) for nombre in ("Ana", "Luis", "Maria", "Jose", "Pedro")},
        "roles": roles, "permisos": permisos,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def escribir_guia():
    """Copia PRUEBAS_GRAPHQL.md con los id de esta empresa en lugar de ID_ANA, ID_CAPTURISTA, etc."""
    valores = {
        "ID_EMPRESA": empresa_id, "ID_CUENTA": cuenta_id, "ID_CONCEPTO": concepto_id, "ID_ANA": ana_id,
        **{f"ID_{nombre.upper()}": datos[0] for nombre, datos in personas.items()},
        **{f"ID_{rol}": id_rol for rol, id_rol in roles.items()},
        "ID_ACCOUNTS_WRITE": permisos["accounts.write"], "ID_CONCEPTS_WRITE": permisos["concepts.write"],
        "CORREO_PEDRO": correo("Pedro"), "CLAVE_DEMO": clave,
    }
    plantilla = (RAIZ / "documentacion" / "PRUEBAS_GRAPHQL.md").read_text(encoding="utf-8")
    pasos = plantilla[plantilla.index("## Parte 1."):]
    encabezado = (
        "# Unidad II, Actividad 4: guía de capturas\n\n"
        f"Empresa {empresa_id}. Membresías: Ana {ana_id}, "
        + ", ".join(f"{nombre} {datos[0]}" for nombre, datos in personas.items())
        + f". Cuenta {cuenta_id}, concepto {concepto_id}.\n\n"
        "Generada por `probar_actividad4.py --preparar` a partir de `documentacion/PRUEBAS_GRAPHQL.md`. "
        "Guarda cada captura en `evidencias/actividad4/capturas/`.\n\n"
        "MySQL: `docker exec -it actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db`\n\n---\n\n"
    )
    guia = encabezado + re.sub(r"\b(" + "|".join(valores) + r")\b", lambda m: str(valores[m.group(1)]), pasos)
    destino = EVIDENCIAS / "guia_capturas.md"
    destino.write_text(guia, encoding="utf-8")
    return destino


def lista_rol(nombre, rol):
    datos = ejecutar(nombre, f'query {{ rolePermissions(roleId: "{roles[rol]}") {{ role {{ code }} permission {{ code }} isActive }} }}')
    return {item["permission"]["code"] for item in datos["rolePermissions"]}


def lista_activa_mysql():
    return {(rol, permiso) for rol, permiso, activo in sql(SELECT_ROLE_PERMISSIONS) if activo}


def fila_pareja(rol, permiso):
    return sql(
        "SELECT rp.id, rp.is_active FROM role_permissions rp JOIN roles r ON r.id = rp.role_id "
        "JOIN permissions p ON p.id = rp.permission_id WHERE r.code = :rol AND p.code = :permiso",
        rol=rol, permiso=permiso,
    )


def roles_de(membresia):
    return sql(
        "SELECT r.code, cur.is_active FROM company_user_roles cur JOIN roles r ON r.id = cur.role_id "
        "WHERE cur.company_user_id = :id ORDER BY cur.id",
        id=int(membresia),
    )


def contar(tabla, columna, valor):
    return sql(f"SELECT COUNT(*) FROM {tabla} WHERE {columna} = :valor", valor=int(valor))[0][0]


def crear_cuenta(nombre, actor, nombre_cuenta, error=False):
    return ejecutar(nombre, f'mutation {{ createAccount(actorCompanyUserId: "{actor}", input: {{companyId: "{empresa_id}", accountType: CASH, name: {codigo(nombre_cuenta)}}}) {{ id name }} }}', error=error)


def asignar_permiso(nombre, actor, rol, permiso, error=False):
    return ejecutar(nombre, f'mutation {{ assignPermissionToRole(input: {{roleId: "{roles[rol]}", permissionId: "{permisos[permiso]}"}}, actorCompanyUserId: "{actor}") {{ id role {{ code }} permission {{ code }} isActive }} }}', error=error)


def quitar_permiso(nombre, actor, rol, permiso):
    return ejecutar(nombre, f'mutation {{ removePermissionFromRole(roleId: "{roles[rol]}", permissionId: "{permisos[permiso]}", actorCompanyUserId: "{actor}") }}')


def crear_movimiento(nombre, persona, error=False):
    membresia, token = persona
    return ejecutar(nombre, f'mutation {{ createTransaction(actorCompanyUserId: "{membresia}", input: {{accountId: "{cuenta_id}", conceptId: "{concepto_id}", transactionType: INCOME, amount: "250.00", shortDescription: "Venta de mostrador"}}) {{ id amount transactionType }} }}', token, error=error)


print("PARTE 1. La configuración inicial")
roles = {r["code"]: r["id"] for r in ejecutar("01_roles", "query { roles { id code name isActive } }")["roles"]}
permisos = {p["code"]: p["id"] for p in ejecutar("02_permissions", "query { permissions { id code name isActive } }")["permissions"]}
assert set(roles) == set(TABLA), roles
assert set(permisos) == TABLA["ADMINISTRADOR"] and len(permisos) == 10, permisos
inicial = {rol: lista_rol(f"03_lista_{rol.lower()}", rol) for rol in TABLA}
assert inicial == TABLA, f"La lista inicial no coincide con la tabla del documento: {inicial}"
assert "transactions.write" in inicial["CAPTURISTA"] and "accounts.write" not in inicial["CAPTURISTA"]
assert not any(p.endswith(".write") for p in inicial["CONSULTA"])
assert "accounts.write" in inicial["CONTADOR"] and "roles.write" not in inicial["CONTADOR"]

print("PREPARACIÓN. Una empresa y cinco personas")
unico = uuid4().hex[:8]
clave = "PruebaRoles2026!"
empresa_id = ejecutar("04_empresa", f'mutation {{ createCompany(input: {{name: "Sistema General de Ingresos {unico}"}}) {{ id name }} }}')["createCompany"]["id"]


def correo(nombre):
    return f"{nombre.lower()}-{unico}@ingresos.example.com"


def login(nombre):
    return ejecutar(f"05_login_{nombre.lower()}", f'mutation {{ login(input: {{email: {codigo(correo(nombre))}, password: {codigo(clave)}}}) {{ token }} }}')["login"]["token"]


ana_id = ejecutar("05_ana_administradora", f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa_id}", name: "Ana", email: {codigo(correo("Ana"))}, password: {codigo(clave)}}}) {{ id isAdmin user {{ name }} }} }}')["createCompanyAdmin"]["id"]
ana_token = login("Ana")
personas = {}
for nombre in ("Luis", "Maria", "Jose", "Pedro"):
    membresia = ejecutar(f"06_usuario_{nombre.lower()}", f'mutation {{ createCompanyUser(actorCompanyUserId: "{ana_id}", input: {{companyId: "{empresa_id}", name: {codigo(nombre)}, email: {codigo(correo(nombre))}, password: {codigo(clave)}}}) {{ id isAdmin user {{ name }} }} }}', ana_token)["createCompanyUser"]["id"]
    personas[nombre] = (membresia, login(nombre))
luis, maria, jose, pedro = (personas[n] for n in ("Luis", "Maria", "Jose", "Pedro"))
for nombre, rol in (("Luis", "CONTADOR"), ("Maria", "CAPTURISTA"), ("Jose", "CAPTURISTA")):
    ejecutar(f"07_rol_{nombre.lower()}", f'mutation {{ assignRole(actorCompanyUserId: "{ana_id}", input: {{companyUserId: "{personas[nombre][0]}", roleId: "{roles[rol]}"}}) {{ id role {{ code }} isActive }} }}')
assert [r for r, activo in roles_de(pedro[0]) if activo] == ["CONSULTA"]
cuenta_id = crear_cuenta("08_cuenta_caja_ana", ana_id, "Caja general")["createAccount"]["id"]
concepto_id = ejecutar("08_concepto_ventas", f'mutation {{ createConcept(actorCompanyUserId: "{ana_id}", input: {{companyId: "{empresa_id}", conceptType: INCOME, name: "Ventas"}}) {{ id name }} }}')["createConcept"]["id"]
ejecutar("08_concepto_en_caja", f'mutation {{ assignConceptToAccount(actorCompanyUserId: "{ana_id}", input: {{accountId: "{cuenta_id}", conceptId: "{concepto_id}"}}) {{ id isActive }} }}')
guardar_identificadores()
if PREPARAR:
    print(f"EMPRESA LISTA. Guía con los id de esta empresa: {escribir_guia()}")
    sys.exit(0)

print("PARTE 2. Un permiso nuevo en el rol, dos personas")
cuentas_antes = contar("accounts", "company_id", empresa_id)
crear_cuenta("10_cuenta_maria_rechazada", maria[0], "Cuenta de Maria", error=True)
crear_cuenta("11_cuenta_jose_rechazada", jose[0], "Cuenta de Jose", error=True)
assert contar("accounts", "company_id", empresa_id) == cuentas_antes, "Un rechazo guardó una cuenta"
asignar_permiso("12_ana_agrega_accounts_write_capturista", ana_id, "CAPTURISTA", "accounts.write")
assert "accounts.write" in lista_rol("13_lista_capturista_con_accounts_write", "CAPTURISTA")
crear_cuenta("14_cuenta_maria_aceptada", maria[0], "Cuenta de Maria")
crear_cuenta("15_cuenta_jose_aceptada", jose[0], "Cuenta de Jose")
assert [r for r, activo in roles_de(jose[0]) if activo] == ["CAPTURISTA"], "José fue editado"
quitar_permiso("16_ana_quita_accounts_write_capturista", ana_id, "CAPTURISTA", "accounts.write")
pareja = fila_pareja("CAPTURISTA", "accounts.write")
assert len(pareja) == 1 and not pareja[0][1], f"La pareja debe quedar inactiva, no borrada: {pareja}"
print(f"  MYSQL    : role_permissions id={pareja[0][0]} CAPTURISTA/accounts.write is_active=0 (no se borró)")
crear_cuenta("17_cuenta_maria_rechazada_otra_vez", maria[0], "Segunda de Maria", error=True)
crear_cuenta("18_cuenta_jose_rechazada_otra_vez", jose[0], "Segunda de Jose", error=True)
assert lista_rol("19_lista_capturista_sin_accounts_write", "CAPTURISTA") == TABLA["CAPTURISTA"]

print("PARTE 3. Cambiar el puesto de una persona")
contador_antes = lista_rol("20_lista_contador_antes", "CONTADOR")
consulta_antes = lista_rol("21_lista_consulta_antes", "CONSULTA")
movimientos_antes = contar("transactions", "account_id", cuenta_id)
crear_movimiento("22_movimiento_pedro_consulta_rechazado", pedro, error=True)
assert contar("transactions", "account_id", cuenta_id) == movimientos_antes, "Un rechazo guardó un movimiento"
ejecutar("23_ana_asigna_capturista_a_pedro", f'mutation {{ assignRole(actorCompanyUserId: "{ana_id}", input: {{companyUserId: "{pedro[0]}", roleId: "{roles["CAPTURISTA"]}"}}) {{ id role {{ code }} isActive companyUser {{ id user {{ name }} }} }} }}')
assert roles_de(pedro[0]) == [("CONSULTA", 0), ("CAPTURISTA", 1)], roles_de(pedro[0])
crear_movimiento("24_movimiento_pedro_capturista_aceptado", pedro)
assert contar("transactions", "account_id", cuenta_id) == movimientos_antes + 1
assert lista_rol("25_lista_contador_despues", "CONTADOR") == contador_antes
crear_cuenta("26_cuenta_luis_aceptada", luis[0], "Bancos de Luis")
consulta_despues = lista_rol("27_lista_consulta_despues", "CONSULTA")
assert consulta_despues == consulta_antes and not any(p.endswith(".write") for p in consulta_despues)
activos = [r for r, activo in roles_de(pedro[0]) if activo]
assert activos == ["CAPTURISTA"], f"Pedro debe tener un solo rol activo: {activos}"
print(f"  MYSQL    : Pedro company_user_roles = {roles_de(pedro[0])} (un solo rol activo)")

print("PARTE 4. Quién puede cambiar la lista")
lista_antes = lista_activa_mysql()
asignar_permiso("30_jose_intenta_cambiar_lista_rechazado", jose[0], "CONSULTA", "concepts.write", error=True)
assert lista_activa_mysql() == lista_antes, "El intento de José cambió la lista"
print("  MYSQL    : la lista activa de role_permissions no cambió tras el intento de José")
asignar_permiso("31_ana_agrega_concepts_write_consulta", ana_id, "CONSULTA", "concepts.write")
assert "concepts.write" in lista_rol("32_lista_consulta_con_concepts_write", "CONSULTA")
quitar_permiso("33_ana_quita_concepts_write_consulta", ana_id, "CONSULTA", "concepts.write")
assert not any(p.endswith(".write") for p in lista_rol("34_lista_consulta_final", "CONSULTA"))

print("CIERRE. La lista vuelve a coincidir con la tabla del documento")
final = {rol: lista_rol(f"40_lista_final_{rol.lower()}", rol) for rol in TABLA}
assert final == TABLA, final
assert lista_activa_mysql() == {(rol, p) for rol, codigos in TABLA.items() for p in codigos}
filas = sql(SELECT_ROLE_PERMISSIONS)
print(f"  {'rol':<14}{'permiso':<22}is_active")
for rol, permiso, activo in filas:
    print(f"  {rol:<14}{permiso:<22}{int(activo)}")
conteos = sql("SELECT (SELECT COUNT(*) FROM roles), (SELECT COUNT(*) FROM permissions), "
              "(SELECT COUNT(*) FROM role_permissions WHERE is_active = 1)")[0]
print(f"  roles={conteos[0]} permisos={conteos[1]} parejas activas={conteos[2]}")

(EVIDENCIAS / "select_role_permissions.txt").write_text(
    "\n".join(f"{rol}\t{permiso}\t{int(activo)}" for rol, permiso, activo in filas) + "\n", encoding="utf-8")
print("PRUEBAS TERMINADAS. Revisa evidencias/actividad4/json y evidencias/actividad4/select_role_permissions.txt.")
