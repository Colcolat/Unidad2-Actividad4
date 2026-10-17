"""Casos de prueba E01 a E10 de la Unidad II, Actividad 5: configurar permisos con GraphQL.

Requiere el servidor activo (uvicorn app.main:app --reload) y MySQL en marcha. Ejecuta las operaciones
con nombre de operaciones.graphql, escribe en variables/ el JSON real de cada una (con los id de esta base)
y compara cada respuesta con el estado de MySQL.

Uso, desde la carpeta del proyecto:
  python documentacion/probar_actividad5.py                     E01 a E07 y la primera mitad de E08
  (detener y volver a arrancar uvicorn)
  python documentacion/probar_actividad5.py --despues-reinicio  segunda mitad de E08, E09 y E10

Las respuestas quedan en evidencias/actividad5/json/ y las consultas SQL en evidencias/actividad5/sql/.
"""
import json
import os
import subprocess
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
CLAVE = os.getenv("CLAVE_PRUEBAS", "PruebaPermisos2026!")  # usuarios ficticios; no se escribe en evidencias
DESPUES_REINICIO = "--despues-reinicio" in sys.argv

OPERACIONES = (RAIZ / "operaciones.graphql").read_text(encoding="utf-8")
VARIABLES = RAIZ / "variables"
EVIDENCIAS = RAIZ / "evidencias" / "actividad5"
JSON_DIR, SQL_DIR = EVIDENCIAS / "json", EVIDENCIAS / "sql"
for carpeta in (VARIABLES, JSON_DIR, SQL_DIR):
    carpeta.mkdir(parents=True, exist_ok=True)
ESTADO = JSON_DIR / "identificadores.json"
INICIAL = json.loads((RAIZ / "configuracion_inicial.json").read_text(encoding="utf-8"))
S0 = ["accounts.read", "concepts.read", "transactions.read", "transactions.write"]
S1 = S0 + ["accounts.write"]
engine = create_engine(DATABASE_URL)

SQL_CAPTURISTA = """
SELECT rp.id AS relacion_id, p.id AS permiso_id, p.code AS permiso,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
ORDER BY p.code"""
SQL_RELACIONES = """
SELECT rp.id AS relacion_id, r.code AS rol, p.code AS permiso,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code"""
SQL_DUPLICADOS = """
SELECT role_id, permission_id, COUNT(*) AS repeticiones
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1"""
SQL_CONTEOS = """
SELECT (SELECT COUNT(*) FROM roles) AS roles,
       (SELECT COUNT(*) FROM permissions) AS permisos,
       (SELECT COUNT(*) FROM role_permissions) AS relaciones,
       (SELECT COUNT(*) FROM role_permissions WHERE is_active = 1) AS relaciones_activas"""


# ---------- utilidades ----------

def graphql(documento, variables=None, operacion=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    cuerpo = {"query": documento, "variables": variables or {}, "operationName": operacion}
    with urlopen(Request(URL, data=json.dumps(cuerpo).encode(), headers=headers), timeout=30) as respuesta:
        return json.load(respuesta)


def guardar(nombre, contenido):
    (JSON_DIR / f"{nombre}.json").write_text(json.dumps(contenido, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def operacion(caso, operacion_nombre, archivo_variables=None, variables=None, token=None, error=None):
    """Ejecuta una operación con nombre de operaciones.graphql.

    Si se da archivo_variables, las variables se escriben en variables/<archivo>.json y se leen de ahí.
    error: None si se espera éxito, o un texto que debe aparecer en el mensaje de error.
    """
    if archivo_variables:
        ruta = VARIABLES / f"{archivo_variables}.json"
        if variables is not None:
            ruta.write_text(json.dumps(variables, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        variables = json.loads(ruta.read_text(encoding="utf-8"))
    resultado = graphql(OPERACIONES, variables, operacion_nombre, token)
    guardar(caso, {"operacion": operacion_nombre, "variables": archivo_variables and f"variables/{archivo_variables}.json",
                   "respuesta": resultado})
    revisar(caso, resultado, error)
    return resultado.get("data")


def revisar(caso, resultado, error):
    errores = resultado.get("errors")
    if error is None and errores:
        raise AssertionError(f"{caso}: se esperaba éxito y llegó {errores}")
    if error is not None and not (errores and error in errores[0]["message"]):
        raise AssertionError(f"{caso}: se esperaba un error con «{error}» y llegó {resultado}")
    print(f"  {'CORRECTO ' if error is None else 'RECHAZADO'}: {caso}" + (f" -> {errores[0]['message']}" if errores else ""))


def sql(consulta, **parametros):
    with engine.connect() as conexion:
        resultado = conexion.execute(text(consulta), parametros)
        return list(resultado.keys()), [tuple(fila) for fila in resultado.all()]


def sql_evidencia(nombre, consulta):
    """Ejecuta la consulta con una conexión nueva y la guarda como tabla de texto, igual que el cliente mysql."""
    columnas, filas = sql(consulta)
    anchos = [max([len(c)] + [len(str(f[i])) for f in filas]) for i, c in enumerate(columnas)]
    borde = "+" + "+".join("-" * (a + 2) for a in anchos) + "+"
    linea = lambda valores: "| " + " | ".join(str(v).ljust(a) for v, a in zip(valores, anchos)) + " |"
    cuerpo = [borde, linea(columnas), borde] + [linea(f) for f in filas] + ([borde] if filas else [])
    salida = "mysql> " + consulta.strip() + ";\n" + ("\n".join(cuerpo) + "\n" if filas else "") + \
             (f"{len(filas)} rows in set\n" if filas else "Empty set\n")
    (SQL_DIR / f"{nombre}.txt").write_text(salida, encoding="utf-8")
    return filas


def codigos(lista):
    return [item["code"] for item in lista]


def ids(lista_codigos):
    return [estado["permisos"][codigo] for codigo in lista_codigos]


def entrada(rol, lista):
    return {"actor": estado["ana"], "input": {"roleId": estado["roles"][rol], "permissionIds": lista}}


def listas_activas():
    """Lista activa de cada rol según GraphQL (rolePermissions)."""
    return {rol: sorted(item["permission"]["code"] for item in operacion(
        f"lista_{rol.lower()}", "ListaDelRol", variables={"roleId": estado["roles"][rol]})["rolePermissions"])
        for rol in INICIAL}


def mutacion_directa(nombre, documento, token=None):
    resultado = graphql(documento, token=token)
    visible = json.loads(json.dumps(resultado))
    if "login" in (visible.get("data") or {}):
        visible["data"]["login"]["token"] = "OCULTO"
    guardar(nombre, {"operacion": "preparación", "respuesta": visible})
    revisar(nombre, resultado, None)
    return resultado["data"]


def login(correo):
    return mutacion_directa("00_login", f'mutation {{ login(input: {{email: "{correo}", password: "{CLAVE}"}}) {{ token }} }}')["login"]["token"]


# ---------- primera parte: E01 a E08 (antes del reinicio) ----------

def primera_parte():
    global estado
    print("PREPARACIÓN. Empresa, Ana (ADMINISTRADOR) y María (CAPTURISTA)")
    unico = uuid4().hex[:8]
    empresa = mutacion_directa("00_empresa", f'mutation {{ createCompany(input: {{name: "Sistema General de Ingresos A5 {unico}"}}) {{ id name }} }}')["createCompany"]
    correo_ana, correo_maria = f"ana-{unico}@ingresos.example.com", f"maria-{unico}@ingresos.example.com"
    ana = mutacion_directa("00_ana", f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa["id"]}", name: "Ana", email: "{correo_ana}", password: "{CLAVE}"}}) {{ id isAdmin }} }}')["createCompanyAdmin"]["id"]
    maria = mutacion_directa("00_maria", f'mutation {{ createCompanyUser(actorCompanyUserId: "{ana}", input: {{companyId: "{empresa["id"]}", name: "María", email: "{correo_maria}", password: "{CLAVE}"}}) {{ id }} }}', login(correo_ana))["createCompanyUser"]["id"]
    roles = {r["code"]: r["id"] for r in graphql("query { roles { id code } }")["data"]["roles"]}
    mutacion_directa("00_rol_maria", f'mutation {{ assignRole(actorCompanyUserId: "{ana}", input: {{companyUserId: "{maria}", roleId: "{roles["CAPTURISTA"]}"}}) {{ role {{ code }} isActive }} }}')
    cuenta = mutacion_directa("00_cuenta", f'mutation {{ createAccount(actorCompanyUserId: "{ana}", input: {{companyId: "{empresa["id"]}", accountType: CASH, name: "Caja general"}}) {{ id }} }}')["createAccount"]["id"]
    concepto = mutacion_directa("00_concepto", f'mutation {{ createConcept(actorCompanyUserId: "{ana}", input: {{companyId: "{empresa["id"]}", conceptType: INCOME, name: "Ventas de mostrador"}}) {{ id }} }}')["createConcept"]["id"]
    mutacion_directa("00_concepto_en_cuenta", f'mutation {{ assignConceptToAccount(actorCompanyUserId: "{ana}", input: {{accountId: "{cuenta}", conceptId: "{concepto}"}}) {{ id }} }}')

    print("E01. Punto de partida")
    datos = operacion("E01_punto_de_partida", "PuntoDePartida")
    roles = {r["code"]: r["id"] for r in datos["roles"]}
    permisos = {p["code"]: p["id"] for p in datos["permissions"]}
    assert sorted(roles) == sorted(INICIAL) and len(permisos) == 10, (roles, permisos)
    estado = {"empresa": empresa["id"], "empresa_nombre": empresa["name"], "ana": ana, "maria": maria,
              "correo_maria": correo_maria, "cuenta": cuenta, "concepto": concepto, "roles": roles, "permisos": permisos}
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    operacion("E01_lista_capturista", "ListaDelRol", "E01_lista_capturista", {"roleId": roles["CAPTURISTA"]})
    actuales = listas_activas()
    assert actuales == INICIAL, f"La base no coincide con configuracion_inicial.json: {actuales}"
    activas = [f for f in sql_evidencia("E01_capturista", SQL_CAPTURISTA) if f[3]]
    assert sorted(f[2] for f in activas) == S0
    sql_evidencia("E01_relaciones", SQL_RELACIONES)
    sql_evidencia("E01_conteos", SQL_CONTEOS)

    print("E02. Catálogo filtrado")
    datos = operacion("E02_explorar_catalogo", "ExplorarCatalogo", "E02_actor", {"actor": ana})
    assert codigos(datos["cuentas"]) == ["accounts.read", "accounts.write"]
    assert codigos(datos["movimientos"]) == ["transactions.read", "transactions.write"]
    datos = operacion("E02_catalogo_completo", "CatalogoCompleto", "E02_actor")
    assert len(datos["catalogo"]) == 10 and codigos(datos["catalogo"]) == sorted(permisos)
    datos = operacion("E02_catalogo_resource_null", "CatalogoPorRecurso", "E02_resource_null", {"actor": ana, "resource": None})
    assert len(datos["catalogo"]) == 10
    datos = operacion("E02_catalogo_company_users", "CatalogoPorRecurso", "E02_resource_company_users", {"actor": ana, "resource": "COMPANY_USERS"})
    assert codigos(datos["catalogo"]) == ["company.users.read", "company.users.write"]
    operacion("E02_enum_inexistente_variable", "CatalogoPorRecurso", "E02_resource_payments",
              {"actor": ana, "resource": "PAYMENTS"}, error="PAYMENTS")
    literal = f'query CatalogoPagos {{ permissionCatalog(resource: PAYMENTS, actorCompanyUserId: "{ana}") {{ code }} }}'
    resultado = graphql(literal)
    guardar("E02_enum_inexistente_literal", {"documento": literal, "respuesta": resultado})
    revisar("E02_enum_inexistente_literal", resultado, "PAYMENTS")
    assert "data" not in resultado or resultado["data"] is None, "Un error de validación no ejecuta el resolver"
    datos = operacion("investigacion_comparar_puestos", "CompararPuestos", "comparar_puestos",
                      {"capturista": roles["CAPTURISTA"], "contador": roles["CONTADOR"]})
    assert len(datos["capturista"]) == 4 and len(datos["contador"]) == 8

    print("E03. Previsualización de S1 con S0 guardada")
    antes = sql_evidencia("E03_antes", SQL_CAPTURISTA)
    datos = operacion("E03_revisar_S1", "RevisarConfiguracion", "S1_capturista", entrada("CAPTURISTA", ids(S1)))["previewRolePermissions"]
    assert codigos(datos["current"]) == S0 and codigos(datos["toActivate"]) == ["accounts.write"]
    assert datos["toDeactivate"] == [] and codigos(datos["unchanged"]) == S0 and datos["finalCount"] == 5
    assert sql_evidencia("E03_despues", SQL_CAPTURISTA) == antes, "La previsualización cambió filas"

    print("E04. Aplicar S1 y repetir")
    datos = operacion("E04_aplicar_S1_primera", "AplicarConfiguracion", "S1_capturista")["setRolePermissions"]
    assert datos["changed"] is True and codigos(datos["activated"]) == ["accounts.write"] and datos["deactivated"] == []
    despues_primera = sql_evidencia("E04_despues_primera", SQL_CAPTURISTA)
    datos = operacion("E04_aplicar_S1_segunda", "AplicarConfiguracion", "S1_capturista")["setRolePermissions"]
    assert datos["changed"] is False and datos["activated"] == [] and datos["deactivated"] == [] and datos["finalCount"] == 5
    assert sql_evidencia("E04_despues_segunda", SQL_CAPTURISTA) == despues_primera, "La repetición cambió filas"
    assert sql_evidencia("E04_duplicados", SQL_DUPLICADOS) == []

    print("E05. Desactivar y reactivar accounts.write")
    fila = lambda filas: next((f[0], f[3], f[4]) for f in filas if f[2] == "accounts.write")
    momento1 = fila(despues_primera)
    datos = operacion("E05_aplicar_S0", "AplicarConfiguracion", "S0_capturista", entrada("CAPTURISTA", ids(S0)))["setRolePermissions"]
    assert codigos(datos["deactivated"]) == ["accounts.write"] and datos["finalCount"] == 4
    momento2 = fila(sql_evidencia("E05_tras_S0", SQL_CAPTURISTA))
    datos = operacion("E05_aplicar_S1", "AplicarConfiguracion", "S1_capturista")["setRolePermissions"]
    assert codigos(datos["activated"]) == ["accounts.write"] and datos["finalCount"] == 5
    momento3 = fila(sql_evidencia("E05_tras_S1", SQL_CAPTURISTA))
    assert momento1[0] == momento2[0] == momento3[0], "La relación cambió de id"
    assert (momento1[1], momento2[1], momento3[1]) == (1, 0, 1) and momento1[2] == momento2[2] == momento3[2] == 1
    sql_evidencia("E05_relacion_accounts_write_contador", """
SELECT rp.id AS relacion_id, r.code AS rol, rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp JOIN roles r ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id
WHERE p.code = 'accounts.write' ORDER BY r.code""")
    print(f"  MYSQL    : relación {momento1[0]} activa -> inactiva -> activa; el permiso siguió activo")

    print("E06. Entradas inválidas (previsualizar y aplicar)")
    s0_ids = ids(S0)
    repetido = estado["permisos"]["accounts.read"]
    variantes = [
        ("rol_inexistente", {"actor": ana, "input": {"roleId": "999999", "permissionIds": s0_ids}}, "no existe", None),
        ("rol_inactivo", entrada("CONSULTA", ids(INICIAL["CONSULTA"])), "inactivo",
         ("UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA'", "UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA'")),
        ("administrador", entrada("ADMINISTRADOR", ids(INICIAL["ADMINISTRADOR"])), "ADMINISTRADOR", None),
        ("permiso_inexistente", entrada("CAPTURISTA", s0_ids + ["999999"]), "no existen", None),
        ("permiso_inactivo", entrada("CAPTURISTA", ids(S0 + ["concepts.write"])), "inactivos",
         ("UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write'", "UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write'")),
        ("permiso_repetido", entrada("CAPTURISTA", s0_ids + [repetido]), "repetido", None),
        ("mismo_id_texto_y_numero", entrada("CAPTURISTA", s0_ids + [int(repetido)]), "repetido", None),
        ("actor_sin_roles_write", {"actor": maria, "input": entrada("CAPTURISTA", s0_ids)["input"]}, "roles.", None),
    ]
    tabla = []
    for nombre, variables, mensaje, preparacion in variantes:
        antes = sql_evidencia(f"E06_{nombre}_antes", SQL_RELACIONES)
        if preparacion:
            with engine.begin() as conexion:
                conexion.execute(text(preparacion[0]))
        try:
            vista = operacion(f"E06_{nombre}_revisar", "RevisarConfiguracion", f"E06_{nombre}", variables, error=mensaje)
            aplicada = operacion(f"E06_{nombre}_aplicar", "AplicarConfiguracion", f"E06_{nombre}", error=mensaje)
            assert vista["previewRolePermissions"] is None and aplicada["setRolePermissions"] is None
        finally:
            if preparacion:
                with engine.begin() as conexion:
                    conexion.execute(text(preparacion[1]))
        assert sql_evidencia(f"E06_{nombre}_despues", SQL_RELACIONES) == antes, f"{nombre} cambió relaciones"
        respuesta = json.loads((JSON_DIR / f"E06_{nombre}_aplicar.json").read_text(encoding="utf-8"))
        tabla.append({"variante": nombre, "variables": f"variables/E06_{nombre}.json", "preparacion": preparacion,
                      "mensaje": respuesta["respuesta"]["errors"][0]["message"], "relaciones_sin_cambio": True})
    sql_evidencia("E06_estados_restablecidos", "SELECT 'rol' AS tipo, code, is_active FROM roles WHERE code = 'CONSULTA' "
                  "UNION ALL SELECT 'permiso', code, is_active FROM permissions WHERE code = 'concepts.write'")
    guardar("E06_resumen", tabla)

    print("E07. Reversión de un fallo después del flush (unittest)")
    antes = sql_evidencia("E07_antes", SQL_CAPTURISTA)
    prueba = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_e07_reversion"],
                            cwd=RAIZ, capture_output=True, text=True)
    (EVIDENCIAS / "E07_unittest.txt").write_text("$ python -m unittest -v tests.test_e07_reversion\n" + prueba.stderr + prueba.stdout, encoding="utf-8")
    assert prueba.returncode == 0, prueba.stderr
    assert sql_evidencia("E07_despues_sesion_nueva", SQL_CAPTURISTA) == antes
    print("  CORRECTO : tests.test_e07_reversion (salida en evidencias/actividad5/E07_unittest.txt)")

    print("E08. Lista vacía (antes del reinicio)")
    datos = operacion("E08_aplicar_vacia", "AplicarConfiguracion", "E08_lista_vacia", entrada("CAPTURISTA", []))["setRolePermissions"]
    assert codigos(datos["deactivated"]) == sorted(S1) and datos["finalCount"] == 0 and datos["changed"] is True
    filas = sql_evidencia("E08_antes_reinicio", SQL_CAPTURISTA)
    assert filas and not any(f[3] for f in filas), "Debe haber filas y todas inactivas"
    estado["E08_filas_antes_reinicio"] = [list(f) for f in filas]
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nDETÉN Y VUELVE A ARRANCAR EL SERVIDOR (uvicorn) y luego ejecuta:\n"
          "  python documentacion/probar_actividad5.py --despues-reinicio")


# ---------- segunda parte: E08 a E10 (después del reinicio) ----------

def segunda_parte():
    global estado
    estado = json.loads(ESTADO.read_text(encoding="utf-8"))

    print("E08. Lista vacía (después del reinicio)")
    filas = sql_evidencia("E08_despues_reinicio", SQL_CAPTURISTA)
    assert [list(f) for f in filas] == estado["E08_filas_antes_reinicio"], "El arranque cambió las filas del capturista"
    datos = operacion("E08_lista_capturista_tras_reinicio", "ListaDelRol", "E01_lista_capturista")
    assert datos["rolePermissions"] == []
    conteos = sql_evidencia("E08_conteos_tras_reinicio", SQL_CONTEOS)[0]
    assert conteos[0] == 4 and conteos[1] == 10, conteos
    assert sql_evidencia("E08_duplicados_tras_reinicio", SQL_DUPLICADOS) == []

    print("E09. Restauración de S0")
    datos = operacion("E09_aplicar_S0", "AplicarConfiguracion", "S0_capturista")["setRolePermissions"]
    assert codigos(datos["activated"]) == sorted(S0) and datos["finalCount"] == 4
    final = listas_activas()
    (RAIZ / "configuracion_final.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert final == INICIAL, f"La matriz final no coincide con la inicial: {final}"
    sql_evidencia("E09_relaciones_final", SQL_RELACIONES)
    sql_evidencia("E09_listas_por_rol", """
SELECT r.code AS rol, COUNT(*) AS activos, GROUP_CONCAT(p.code ORDER BY p.code SEPARATOR ', ') AS permisos_activos
FROM role_permissions rp JOIN roles r ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id
WHERE rp.is_active = 1 AND p.is_active = 1
GROUP BY r.code ORDER BY r.code""")
    assert sql_evidencia("E09_duplicados", SQL_DUPLICADOS) == []
    print("  CORRECTO : configuracion_final.json coincide con configuracion_inicial.json")

    print("E10. Continuidad del proyecto")
    datos = operacion("E10_cuentas", "CuentasDeLaEmpresa", "E10_cuentas", {"actor": estado["maria"], "companyId": estado["empresa"]})
    assert [c["id"] for c in datos["accounts"]] == [estado["cuenta"]]
    token = login(estado["correo_maria"])
    datos = operacion("E10_registrar_movimiento", "RegistrarMovimiento", "E10_movimiento", {
        "actor": estado["maria"],
        "input": {"accountId": estado["cuenta"], "conceptId": estado["concepto"], "transactionType": "INCOME",
                  "amount": "350.00", "shortDescription": "Venta de mostrador"},
    }, token=token)
    movimiento = datos["createTransaction"]["id"]
    filas = sql_evidencia("E10_movimiento", f"""
SELECT t.id AS movimiento_id, c.name AS empresa, a.name AS cuenta, k.name AS concepto,
       t.transaction_type AS tipo, t.amount AS monto, u.name AS capturo
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN concepts k ON k.id = t.concept_id
JOIN companies c ON c.id = a.company_id
JOIN users u ON u.id = t.captured_by
WHERE t.id = {int(movimiento)}""")
    assert len(filas) == 1 and str(filas[0][5]) == "350.00" and filas[0][1] == estado["empresa_nombre"]
    print("\nPRUEBAS TERMINADAS. Evidencias en evidencias/actividad5/ y variables en variables/.")


estado = {}
if DESPUES_REINICIO:
    segunda_parte()
else:
    primera_parte()
