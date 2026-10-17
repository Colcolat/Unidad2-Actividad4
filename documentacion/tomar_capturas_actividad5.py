"""Toma las capturas de la Actividad 5 (E01 a E10) en GraphiQL, en MySQL y en la terminal.

Antes: servidor activo y haber corrido las dos partes de
  python documentacion/probar_actividad5.py
(crea la empresa de prueba, escribe variables/ y deja CAPTURISTA en S0).

Necesita Playwright (pip install playwright) y un navegador; no está en requirements.txt porque solo sirve
para las evidencias. Se ejecuta en dos partes, igual que las pruebas:

  python documentacion/tomar_capturas_actividad5.py principal   E01 a E08 (aplica la lista vacía)
  (detener y volver a arrancar uvicorn)
  python documentacion/tomar_capturas_actividad5.py reinicio    E08 tras el reinicio, E09 y E10

Las operaciones se copian de operaciones.graphql y las variables de variables/, así cada captura muestra
exactamente lo que está en la entrega. Cada paso comprueba la respuesta antes de guardar la imagen.
Las capturas de MySQL son la salida real del cliente mysql (-t). Por omisión se usa el contenedor de
docker-compose; otro cliente se indica con MYSQL_CMD, por ejemplo:
  MYSQL_CMD="mysql -h127.0.0.1 -P3307 -uactividad4 -pactividad4 actividad4_db"
El token de E10 se pide por HTTP y en la captura aparece oculto.
"""
import html
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from graphql import OperationDefinitionNode, parse
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
GRUPO = sys.argv[1] if len(sys.argv) > 1 else "principal"
OUT = RAIZ / "evidencias" / "actividad5" / "capturas"
OUT.mkdir(parents=True, exist_ok=True)
URL = os.getenv("GRAPHQL_URL", "http://127.0.0.1:8000/graphql")
CLAVE = os.getenv("CLAVE_PRUEBAS", "PruebaPermisos2026!")
MYSQL_CMD = shlex.split(os.getenv(
    "MYSQL_CMD", "docker exec -i actividad4_mysql mysql -uactividad4 -pactividad4 actividad4_db"))
# Ruta a un Chrome/Chromium si Playwright no trae el suyo (por ejemplo /opt/pw-browsers/chromium).
NAVEGADOR = os.getenv("NAVEGADOR")
# Carpeta con copias de los archivos de unpkg.com, por si la red no deja cargar GraphiQL desde la CDN.
CDN_LOCAL = os.getenv("CDN_LOCAL")

ESTADO = json.loads((RAIZ / "evidencias" / "actividad5" / "json" / "identificadores.json").read_text(encoding="utf-8"))
TEXTO_OPERACIONES = (RAIZ / "operaciones.graphql").read_text(encoding="utf-8")
DOCUMENTO = parse(TEXTO_OPERACIONES)
FRAGMENTOS = {d.name.value: TEXTO_OPERACIONES[d.loc.start:d.loc.end] for d in DOCUMENTO.definitions
              if not isinstance(d, OperationDefinitionNode)}
OPERACIONES = {d.name.value: TEXTO_OPERACIONES[d.loc.start:d.loc.end] for d in DOCUMENTO.definitions
               if isinstance(d, OperationDefinitionNode)}

SQL_CAPTURISTA = """SELECT rp.id AS relacion_id, p.code AS permiso,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
ORDER BY p.code;"""
SQL_DUPLICADOS = """SELECT role_id, permission_id, COUNT(*) AS repeticiones
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;"""
SQL_CONTEOS = """SELECT (SELECT COUNT(*) FROM roles) AS roles,
       (SELECT COUNT(*) FROM permissions) AS permisos,
       (SELECT COUNT(*) FROM role_permissions) AS relaciones,
       (SELECT COUNT(*) FROM role_permissions WHERE is_active = 1) AS activas;"""
SQL_ACCOUNTS_WRITE = """SELECT rp.id AS relacion_id, r.code AS rol,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE p.code = 'accounts.write'
ORDER BY r.code;"""
SQL_LISTAS = """SELECT r.code AS rol, COUNT(*) AS activos,
       GROUP_CONCAT(p.code ORDER BY p.code SEPARATOR ', ') AS permisos
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE rp.is_active = 1 AND p.is_active = 1
GROUP BY r.code
ORDER BY r.code;"""
SQL_ESTADOS = """SELECT 'rol' AS tipo, code, is_active FROM roles WHERE code = 'CONSULTA'
UNION ALL
SELECT 'permiso', code, is_active FROM permissions WHERE code = 'concepts.write';"""


def texto_operacion(nombre):
    texto = OPERACIONES[nombre]
    usados = [f for f in FRAGMENTOS if "..." + f in texto]
    return texto + "".join("\n\n" + FRAGMENTOS[f] for f in usados)


def variables(archivo):
    return (RAIZ / "variables" / f"{archivo}.json").read_text(encoding="utf-8").strip()


def nueva_pagina(pw, ancho=1500, alto=900):
    navegador = pw.chromium.launch(executable_path=NAVEGADOR) if NAVEGADOR else pw.chromium.launch()
    pagina = navegador.new_page(viewport={"width": ancho, "height": alto})
    if CDN_LOCAL:
        def servir(route):
            relativo = route.request.url.split("unpkg.com/", 1)[1]
            tipo = "text/css" if relativo.endswith(".css") else "application/javascript"
            route.fulfill(path=str(Path(CDN_LOCAL) / relativo), content_type=tipo)
        pagina.route("https://unpkg.com/**", servir)
    return navegador, pagina


def graphiql(pw, nombre, operacion=None, archivo=None, documento=None, espera="ok", token=None):
    """espera: 'ok' o un texto que debe aparecer en el primer error. Devuelve la respuesta JSON."""
    consulta = documento or texto_operacion(operacion)
    url = URL + "?q=" + quote(consulta)
    if archivo:
        url += "&variables=" + quote(variables(archivo))
    if token:
        url += "&headers=" + quote(json.dumps({"Authorization": "Bearer " + token}, indent=2))
    navegador, pg = nueva_pagina(pw)
    pg.goto(url)
    pg.wait_for_selector(".graphiql-execute-button", timeout=30000)
    # Editor más ancho que la respuesta y panel de variables con espacio para todas sus líneas.
    lineas_consulta, lineas_variables = consulta.count("\n") + 1, (variables(archivo).count("\n") + 1 if archivo else 3)
    pg.evaluate("""([consulta, vars]) => {
        const barra = document.querySelector('.graphiql-horizontal-drag-bar');
        barra.previousElementSibling.style.flex = '1.45 1 0%';
        const editor = document.querySelector('.graphiql-query-editor').closest('[style*="flex: 3"]');
        editor.style.flex = Math.max(consulta, 8) + ' 1 0%';
        editor.parentElement.lastElementChild.style.flex = (Math.max(vars, 3) + 3) + ' 1 0%';
    }""", [lineas_consulta, max(lineas_variables, 4 if token else 0)])
    if token:
        pg.get_by_text("Headers", exact=True).click()
    pg.click(".graphiql-execute-button")
    pg.wait_for_function("() => { const c = document.querySelector('.result-window .CodeMirror');"
                         " return c && c.CodeMirror.getValue().trim().length > 0; }", timeout=20000)
    respuesta = json.loads(pg.evaluate("document.querySelector('.result-window .CodeMirror').CodeMirror.getValue()"))
    errores = respuesta.get("errors")
    if espera == "ok":
        assert not errores, f"{nombre}: {respuesta}"
    else:
        assert errores and espera in errores[0]["message"], f"{nombre}: {respuesta}"
    if token:
        # El token ya se usó; en la imagen queda oculto.
        pg.evaluate("""() => { for (const c of document.querySelectorAll('.graphiql-editor-tool .CodeMirror'))
            if (c.CodeMirror.getValue().includes('Bearer')) c.CodeMirror.setValue('{\\n  "Authorization": "Bearer <token de María, oculto>"\\n}'); }""")
    alto_resultado = pg.evaluate("document.querySelector('.result-window .CodeMirror-sizer').offsetHeight")
    alto_editores = (lineas_consulta + max(lineas_variables, 3) + 6) * 23 + 200
    pg.set_viewport_size({"width": 1500, "height": max(900, alto_resultado + 160, alto_editores)})
    pg.wait_for_timeout(700)
    pg.screenshot(path=str(OUT / f"{nombre}.png"))
    navegador.close()
    print(f"{nombre:<44} {'OK' if espera == 'ok' else 'RECHAZADO: ' + errores[0]['message']}")
    return respuesta


def terminal(pw, nombre, titulo, texto):
    lineas = texto.split("\n")
    ancho = min(2400, max(1000, max(len(l) for l in lineas) * 9 + 80))
    pagina = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1e1e1e;font-family:'DejaVu Sans Mono',Consolas,monospace;display:inline-block;min-width:100%}}
.bar{{background:#2d2d2d;color:#ccc;font:13px sans-serif;padding:8px 14px}}
pre{{color:#e6e6e6;font-size:15px;line-height:1.35;margin:0;padding:14px 18px;white-space:pre}}
</style><div class="bar">{html.escape(titulo)}</div><pre>{html.escape(texto)}</pre>"""
    navegador, pg = nueva_pagina(pw, ancho, 300)
    pg.set_content(pagina)
    pg.screenshot(path=str(OUT / f"{nombre}.png"), full_page=True)
    navegador.close()
    print(f"{nombre:<44} terminal")


def mysql(pw, nombre, consultas, comprobar=None):
    bloques = []
    for consulta in consultas:
        r = subprocess.run(MYSQL_CMD + ["-t", "-vv", "-e", consulta], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        # -vv repite la consulta entre guiones; se reemplaza por el prompt interactivo.
        cuerpo = r.stdout.split("--------------\n")[-1].replace("Bye\n", "").strip("\n")
        lineas = consulta.strip().split("\n")
        bloques.append("mysql> " + lineas[0] + "".join("\n    -> " + l for l in lineas[1:]) + "\n" + cuerpo + "\n")
    if comprobar:
        comprobar("\n".join(bloques))
    version = subprocess.run(MYSQL_CMD + ["-N", "-e", "SELECT VERSION()"], capture_output=True, text=True).stdout.strip()
    terminal(pw, nombre, f"Cliente mysql · servidor {version} · actividad4_db", "\n".join(bloques) + "\nmysql> ")


def debe(*textos):
    """Textos que deben aparecer en la salida; los espacios de relleno de las tablas no cuentan."""
    def revisar(cuerpo):
        plano = " ".join(cuerpo.split())
        for texto in textos:
            assert texto in plano, f"Falta «{texto}» en:\n{cuerpo}"
    return revisar


def http(consulta):
    cuerpo = json.dumps({"query": consulta}).encode()
    with urlopen(Request(URL, data=cuerpo, headers={"Content-Type": "application/json"}), timeout=30) as respuesta:
        return json.load(respuesta)


def codigos(lista):
    return [p["code"] for p in lista]


S0 = ["accounts.read", "concepts.read", "transactions.read", "transactions.write"]
S1 = sorted(S0 + ["accounts.write"])


def principal(pw):
    actuales = http(f'query {{ rolePermissions(roleId: "{ESTADO["roles"]["CAPTURISTA"]}") {{ permission {{ code }} }} }}')
    assert sorted(r["permission"]["code"] for r in actuales["data"]["rolePermissions"]) == S0, \
        "CAPTURISTA debe estar en S0: corre antes probar_actividad5.py completo"

    # E01
    graphiql(pw, "E01a_punto_de_partida", "PuntoDePartida")
    graphiql(pw, "E01b_lista_capturista", "ListaDelRol", "E01_lista_capturista")
    terminal(pw, "E01c_configuracion_inicial", "Terminal", "$ cat configuracion_inicial.json\n"
             + (RAIZ / "configuracion_inicial.json").read_text(encoding="utf-8"))
    mysql(pw, "E01d_mysql_capturista", [SQL_CAPTURISTA, SQL_CONTEOS], debe("transactions.write"))

    # E02
    r = graphiql(pw, "E02a_explorar_catalogo", "ExplorarCatalogo", "E02_actor")
    assert codigos(r["data"]["cuentas"]) == ["accounts.read", "accounts.write"]
    r = graphiql(pw, "E02b_catalogo_completo", "CatalogoCompleto", "E02_actor")
    assert len(r["data"]["catalogo"]) == 10
    graphiql(pw, "E02c_catalogo_resource_null", "CatalogoPorRecurso", "E02_resource_null")
    graphiql(pw, "E02d_payments_variable", "CatalogoPorRecurso", "E02_resource_payments", espera="PAYMENTS")
    graphiql(pw, "E02e_payments_literal", documento=(
        "query CatalogoPagos {\n  permissionCatalog(\n    resource: PAYMENTS\n"
        f'    actorCompanyUserId: "{ESTADO["ana"]}"\n  ) {{\n    code\n  }}\n}}'), espera="PAYMENTS")
    graphiql(pw, "I01_comparar_puestos", "CompararPuestos", "comparar_puestos")

    # E03
    mysql(pw, "E03a_mysql_antes", [SQL_CAPTURISTA], debe("accounts.write | 0"))
    r = graphiql(pw, "E03b_revisar_S1", "RevisarConfiguracion", "S1_capturista")["data"]["previewRolePermissions"]
    assert codigos(r["toActivate"]) == ["accounts.write"] and r["toDeactivate"] == [] and r["finalCount"] == 5
    mysql(pw, "E03c_mysql_despues", [SQL_CAPTURISTA], debe("accounts.write | 0"))

    # E04
    r = graphiql(pw, "E04a_aplicar_S1_primera", "AplicarConfiguracion", "S1_capturista")["data"]["setRolePermissions"]
    assert r["changed"] is True and codigos(r["activated"]) == ["accounts.write"]
    r = graphiql(pw, "E04b_aplicar_S1_segunda", "AplicarConfiguracion", "S1_capturista")["data"]["setRolePermissions"]
    assert r["changed"] is False and r["activated"] == r["deactivated"] == [] and r["finalCount"] == 5
    mysql(pw, "E04c_mysql_filas_y_duplicados", [SQL_CAPTURISTA, SQL_DUPLICADOS], debe("accounts.write | 1"))

    # E05
    mysql(pw, "E05a_mysql_accounts_write_activa", [SQL_ACCOUNTS_WRITE])
    r = graphiql(pw, "E05b_aplicar_S0", "AplicarConfiguracion", "S0_capturista")["data"]["setRolePermissions"]
    assert codigos(r["deactivated"]) == ["accounts.write"]
    mysql(pw, "E05c_mysql_accounts_write_inactiva", [SQL_ACCOUNTS_WRITE])
    r = graphiql(pw, "E05d_aplicar_S1", "AplicarConfiguracion", "S1_capturista")["data"]["setRolePermissions"]
    assert codigos(r["activated"]) == ["accounts.write"]
    mysql(pw, "E05e_mysql_accounts_write_reactivada", [SQL_ACCOUNTS_WRITE])

    # E06
    mysql(pw, "E06a_mysql_antes", [SQL_CAPTURISTA, SQL_ESTADOS])
    variantes = [
        ("b", "rol_inexistente", "no existe", None),
        ("c", "rol_inactivo", "inactivo", ("UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA';",
                                          "UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA';")),
        ("d", "administrador", "ADMINISTRADOR", None),
        ("e", "permiso_inexistente", "no existen", None),
        ("f", "permiso_inactivo", "inactivos", ("UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write';",
                                                "UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write';")),
        ("g", "permiso_repetido", "repetido", None),
        ("h", "mismo_id_texto_y_numero", "repetido", None),
        ("i", "actor_sin_roles_write", "roles.", None),
    ]
    for letra, variante, mensaje, preparacion in variantes:
        if preparacion:
            mysql(pw, f"E06{letra}0_preparacion_{variante}", [preparacion[0]])
        try:
            graphiql(pw, f"E06{letra}1_{variante}_revisar", "RevisarConfiguracion", f"E06_{variante}", espera=mensaje)
            graphiql(pw, f"E06{letra}2_{variante}_aplicar", "AplicarConfiguracion", f"E06_{variante}", espera=mensaje)
        finally:
            if preparacion:
                mysql(pw, f"E06{letra}3_restauracion_{variante}", [preparacion[1]])
    mysql(pw, "E06j_mysql_despues", [SQL_CAPTURISTA, SQL_ESTADOS])

    # E07
    prueba = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_e07_reversion"],
                            cwd=RAIZ, capture_output=True, text=True)
    assert prueba.returncode == 0, prueba.stderr
    terminal(pw, "E07a_unittest", "Terminal", "$ python -m unittest -v tests.test_e07_reversion\n" + prueba.stderr + prueba.stdout)
    mysql(pw, "E07b_mysql_sesion_nueva", [SQL_CAPTURISTA], debe("accounts.write | 1"))

    # E08 (antes del reinicio)
    r = graphiql(pw, "E08a_aplicar_lista_vacia", "AplicarConfiguracion", "E08_lista_vacia")["data"]["setRolePermissions"]
    assert codigos(r["deactivated"]) == S1 and r["finalCount"] == 0
    mysql(pw, "E08b_mysql_antes_reinicio", [SQL_CAPTURISTA])
    print("\nDETÉN Y VUELVE A ARRANCAR EL SERVIDOR (uvicorn) y luego ejecuta:\n"
          "  python documentacion/tomar_capturas_actividad5.py reinicio")


def reinicio(pw):
    # E08 (después del reinicio)
    mysql(pw, "E08c_mysql_despues_reinicio", [SQL_CAPTURISTA, SQL_CONTEOS, SQL_DUPLICADOS])
    r = graphiql(pw, "E08d_lista_capturista_tras_reinicio", "ListaDelRol", "E01_lista_capturista")
    assert r["data"]["rolePermissions"] == []

    # E09
    r = graphiql(pw, "E09a_aplicar_S0", "AplicarConfiguracion", "S0_capturista")["data"]["setRolePermissions"]
    assert codigos(r["activated"]) == S0
    final = {}
    for rol, id_rol in ESTADO["roles"].items():
        datos = http(f'query {{ rolePermissions(roleId: "{id_rol}") {{ permission {{ code }} }} }}')["data"]
        final[rol] = sorted(item["permission"]["code"] for item in datos["rolePermissions"])
    final = dict(sorted(final.items()))
    (RAIZ / "configuracion_final.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    diferencia = subprocess.run(["diff", "configuracion_inicial.json", "configuracion_final.json"], cwd=RAIZ,
                                capture_output=True, text=True)
    assert diferencia.returncode == 0, diferencia.stdout
    terminal(pw, "E09b_comparar_configuraciones", "Terminal",
             "$ diff configuracion_inicial.json configuracion_final.json && echo \"Sin diferencias\"\nSin diferencias\n")
    mysql(pw, "E09c_mysql_listas_por_rol", [SQL_LISTAS, SQL_DUPLICADOS],
          debe("ADMINISTRADOR | 10", "CAPTURISTA | 4", "CONSULTA | 4", "CONTADOR | 8"))

    # E10
    graphiql(pw, "E10a_cuentas", "CuentasDeLaEmpresa", "E10_cuentas")
    token = http(f'mutation {{ login(input: {{email: "{ESTADO["correo_maria"]}", password: "{CLAVE}"}}) {{ token }} }}')["data"]["login"]["token"]
    r = graphiql(pw, "E10b_registrar_movimiento", "RegistrarMovimiento", "E10_movimiento", token=token)
    movimiento = int(r["data"]["createTransaction"]["id"])
    mysql(pw, "E10c_mysql_movimiento", [f"""SELECT t.id AS movimiento, c.name AS empresa, a.name AS cuenta,
       k.name AS concepto, t.transaction_type AS tipo, t.amount AS monto, u.name AS capturo
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN concepts k ON k.id = t.concept_id
JOIN companies c ON c.id = a.company_id
JOIN users u ON u.id = t.captured_by
WHERE t.id = {movimiento};"""], debe("1 row in set"))


with sync_playwright() as playwright:
    principal(playwright) if GRUPO == "principal" else reinicio(playwright)
