import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

URL = os.getenv("GRAPHQL_URL", "http://127.0.0.1:8000/graphql")
EVIDENCIAS = Path(__file__).resolve().parents[2] / "evidencias" / "actividad3"
EVIDENCIAS.mkdir(parents=True, exist_ok=True)


def ejecutar(nombre, consulta, token=None, error=False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(URL, data=json.dumps({"query": consulta}).encode(), headers=headers)
    with urlopen(request, timeout=30) as response:
        resultado = json.load(response)
    visible = json.loads(json.dumps(resultado))
    if nombre.startswith(("07_login", "09_login")) and visible.get("data"):
        visible["data"]["login"]["token"] = "OCULTO"
    (EVIDENCIAS / f"{nombre}.json").write_text(json.dumps(visible, indent=2, ensure_ascii=False) + "\n")
    if bool(resultado.get("errors")) != error:
        raise AssertionError(f"Resultado inesperado en {nombre}: {resultado}")
    print(f"{'RECHAZADO' if error else 'CORRECTO'}: {nombre}")
    return resultado.get("data", {})


def codigo(texto):
    return json.dumps(texto, ensure_ascii=False)


roles = ejecutar("01_roles", "query { roles { id code name isActive } }")["roles"]
permisos = ejecutar("02_permissions", "query { permissions { id code isActive } }")["permissions"]
mapa_roles = {item["code"]: item["id"] for item in roles}
mapa_permisos = {item["code"]: item["id"] for item in permisos}
assert all(code in mapa_roles for code in ("ADMINISTRADOR", "CONTADOR", "CAPTURISTA", "CONSULTA"))
assert all(code in mapa_permisos for code in ("company.users.read", "company.users.write", "accounts.read", "accounts.write", "concepts.read", "concepts.write", "transactions.read", "transactions.write", "roles.read", "roles.write"))

captura_permisos = ejecutar("03_permisos_capturista", f'query {{ rolePermissions(roleId: "{mapa_roles["CAPTURISTA"]}") {{ permission {{ code }} }} }}')["rolePermissions"]
consulta_permisos = ejecutar("04_permisos_consulta", f'query {{ rolePermissions(roleId: "{mapa_roles["CONSULTA"]}") {{ permission {{ code }} }} }}')["rolePermissions"]
codigos_cap = {item["permission"]["code"] for item in captura_permisos}
codigos_cons = {item["permission"]["code"] for item in consulta_permisos}
assert "transactions.write" in codigos_cap and "accounts.write" not in codigos_cap
assert all(not code.endswith(".write") for code in codigos_cons)

unico = uuid4().hex[:10]
empresa = ejecutar("05_empresa_demo", f'mutation {{ createCompany(input: {{name: "Prueba U2 {unico}"}}) {{ id name }} }}')["createCompany"]
empresa_id = empresa["id"]
clave = "PruebaRBAC2026!"

admin_email = f"admin-{unico}@example.com"
admin = ejecutar("06_administrador", f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa_id}", name: "Administrador Prueba", email: {codigo(admin_email)}, password: {codigo(clave)}}}) {{ id isAdmin }} }}')["createCompanyAdmin"]
admin_id = admin["id"]
admin_token = ejecutar("07_login_administrador", f'mutation {{ login(input: {{email: {codigo(admin_email)}, password: {codigo(clave)}}}) {{ token }} }}')["login"]["token"]



def crear_usuario(puesto):
    correo = f"{puesto.lower()}-{unico}@example.com"
    usuario = ejecutar(f"08_usuario_{puesto.lower()}", f'mutation {{ createCompanyUser(actorCompanyUserId: "{admin_id}", input: {{companyId: "{empresa_id}", name: "{puesto}", email: {codigo(correo)}, password: {codigo(clave)}}}) {{ id isAdmin }} }}', admin_token)["createCompanyUser"]
    token = ejecutar(f"09_login_{puesto.lower()}", f'mutation {{ login(input: {{email: {codigo(correo)}, password: {codigo(clave)}}}) {{ token }} }}')["login"]["token"]
    return usuario["id"], token


capturista_id, capturista_token = crear_usuario("Capturista")
consulta_id, consulta_token = crear_usuario("Consulta")
contador_id, contador_token = crear_usuario("Contador")

for nombre, membresia, rol in (("capturista", capturista_id, "CAPTURISTA"), ("contador", contador_id, "CONTADOR")):
    ejecutar(f"10_asignar_{nombre}", f'mutation {{ assignRole(actorCompanyUserId: "{admin_id}", input: {{companyUserId: "{membresia}", roleId: "{mapa_roles[rol]}"}}) {{ id role {{ code }} isActive }} }}')

cuenta = ejecutar("11_cuenta_administrador", f'mutation {{ createAccount(actorCompanyUserId: "{admin_id}", input: {{companyId: "{empresa_id}", accountType: CASH, name: "Caja Demo"}}) {{ id name }} }}')["createAccount"]
concepto = ejecutar("12_concepto", f'mutation {{ createConcept(actorCompanyUserId: "{admin_id}", input: {{companyId: "{empresa_id}", conceptType: INCOME, name: "Ventas Demo"}}) {{ id name }} }}')["createConcept"]
ejecutar("13_asignar_concepto", f'mutation {{ assignConceptToAccount(actorCompanyUserId: "{admin_id}", input: {{accountId: "{cuenta["id"]}", conceptId: "{concepto["id"]}"}}) {{ id isActive }} }}')

operacion = f'createTransaction(actorCompanyUserId: "{capturista_id}", input: {{accountId: "{cuenta["id"]}", conceptId: "{concepto["id"]}", transactionType: INCOME, amount: "150.00"}}) {{ id amount }}'
ejecutar("14_movimiento_capturista_aceptado", 'mutation { ' + operacion + ' }', capturista_token)
q_conteo = f'query {{ transactions(actorCompanyUserId: "{consulta_id}", accountId: "{cuenta["id"]}") {{ id }} }}'
antes = ejecutar("15_movimientos_antes", q_conteo)["transactions"]
ejecutar("16_movimiento_consulta_rechazado", f'mutation {{ createTransaction(actorCompanyUserId: "{consulta_id}", input: {{accountId: "{cuenta["id"]}", conceptId: "{concepto["id"]}", transactionType: INCOME, amount: "150.00"}}) {{ id }} }}', consulta_token, error=True)
despues = ejecutar("17_movimientos_despues", q_conteo)["transactions"]
assert len(antes) == len(despues)

ejecutar("18_cuenta_capturista_rechazada", f'mutation {{ createAccount(actorCompanyUserId: "{capturista_id}", input: {{companyId: "{empresa_id}", accountType: CASH, name: "Cuenta No Autorizada"}}) {{ id }} }}', error=True)
ejecutar("19_cuenta_contador_aceptada", f'mutation {{ createAccount(actorCompanyUserId: "{contador_id}", input: {{companyId: "{empresa_id}", accountType: CASH, name: "Cuenta del Contador"}}) {{ id }} }}')
ejecutar("20_promocion_capturista_contador", f'mutation {{ assignRole(actorCompanyUserId: "{admin_id}", input: {{companyUserId: "{capturista_id}", roleId: "{mapa_roles["CONTADOR"]}"}}) {{ id role {{ code }} }} }}')
ejecutar("21_cuenta_tras_promocion", f'mutation {{ createAccount(actorCompanyUserId: "{capturista_id}", input: {{companyId: "{empresa_id}", accountType: CASH, name: "Cuenta Tras Ascenso"}}) {{ id }} }}')
ejecutar("22_segundo_admin_rechazado", f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa_id}", name: "Segundo Admin", email: "otro-{unico}@example.com", password: "{clave}"}}) {{ id }} }}', error=True)

(EVIDENCIAS / "identificadores_demo.json").write_text(json.dumps({"empresa_id": empresa_id, "administrador_id": admin_id, "contador_id": contador_id, "capturista_id": capturista_id, "consulta_id": consulta_id, "cuenta_id": cuenta["id"], "concepto_id": concepto["id"], "roles": mapa_roles, "permisos": mapa_permisos}, indent=2, ensure_ascii=False) + "\n")
print("PRUEBAS TERMINADAS. Revisa la carpeta evidencias.")
