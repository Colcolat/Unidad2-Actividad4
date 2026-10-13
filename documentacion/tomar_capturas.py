"""Toma las capturas de la Actividad 4 en GraphiQL y de MySQL, en el orden de PRUEBAS_GRAPHQL.md.

Antes: servidor activo y una empresa recién preparada con
  python documentacion/probar_actividad4.py --preparar
Necesita Google Chrome y Playwright (pip install playwright); no está en requirements.txt
porque solo sirve para las evidencias.

  python documentacion/tomar_capturas.py principal   capturas 00 a 09
  (reiniciar el servidor)
  python documentacion/tomar_capturas.py reinicio    capturas 10a y 10b

Cada paso comprueba la respuesta antes de guardar la imagen y se detiene si no es la esperada.
Las capturas de MySQL son la salida real del cliente mysql (-t), mostrada como terminal.
"""
import html
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

PROYECTO = Path(__file__).resolve().parent.parent
GRUPO = sys.argv[1] if len(sys.argv) > 1 else "principal"
OUT = PROYECTO / "evidencias" / "actividad4" / "capturas"
OUT.mkdir(parents=True, exist_ok=True)
ids = json.loads((PROYECTO / "evidencias" / "actividad4" / "preparacion" / "identificadores.json").read_text(encoding="utf-8"))
M, R, P = ids["membresias"], ids["roles"], ids["permisos"]
E, CTA, CON = ids["empresa_id"], ids["cuenta_id"], ids["concepto_id"]
URL = "http://127.0.0.1:8000/graphql"


def graphiql(pw, nombre, q, espera, headers=None):
    """espera: 'ok' o el texto de error esperado. Devuelve la respuesta JSON."""
    b = pw.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1500, "height": 860})
    url = URL + "?q=" + quote(q) + ("&headers=" + quote(headers) if headers else "")
    pg.goto(url)
    pg.wait_for_selector(".graphiql-execute-button", timeout=30000)
    if headers:
        pg.get_by_role("tab", name="Headers").click() if pg.get_by_role("tab", name="Headers").count() else pg.get_by_text("Headers", exact=True).click()
    pg.click(".graphiql-execute-button")
    pg.wait_for_function("() => { const c = document.querySelector('.result-window .CodeMirror'); return c && c.CodeMirror.getValue().trim().length > 0; }", timeout=20000)
    texto = pg.evaluate("document.querySelector('.result-window .CodeMirror').CodeMirror.getValue()")
    resp = json.loads(texto)
    if espera == "ok":
        assert not resp.get("errors"), f"{nombre}: {resp}"
    else:
        assert resp.get("errors") and espera in resp["errors"][0]["message"], f"{nombre}: {resp}"
    alto = pg.evaluate("Math.max(document.querySelector('.result-window .CodeMirror-sizer').offsetHeight, document.querySelector('.graphiql-query-editor .CodeMirror-sizer').offsetHeight + 300)")
    pg.set_viewport_size({"width": 1500, "height": max(860, alto + 120)})
    pg.wait_for_timeout(700)
    pg.screenshot(path=str(OUT / f"{nombre}.png"))
    b.close()
    print(f"{nombre:<40} {'OK' if espera == 'ok' else 'RECHAZADO: ' + resp['errors'][0]['message']}")
    return resp


def mysql(pw, nombre, consultas, comprobar=None):
    bloques = []
    for consulta in consultas:
        r = subprocess.run(["docker", "exec", "actividad4_mysql", "mysql", "-uactividad4", "-pactividad4", "actividad4_db", "-t", "-vv", "-e", consulta],
                           capture_output=True, text=True, encoding="utf-8")
        salida = r.stdout
        assert r.returncode == 0, r.stderr
        # -vv repite la consulta entre guiones; se reemplaza por el prompt interactivo.
        partes = salida.split("--------------\n")
        cuerpo = partes[-1].replace("Bye\n", "").strip("\n")
        lineas = consulta.strip().split("\n")
        prompt = "mysql> " + lineas[0] + "".join("\n    -> " + l for l in lineas[1:])
        bloques.append(prompt + "\n" + cuerpo + "\n")
        if comprobar:
            comprobar(cuerpo)
    texto = "\n".join(bloques) + "\nmysql> "
    pagina = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1e1e1e;font-family:Consolas,'Cascadia Mono',monospace}}
.bar{{background:#2d2d2d;color:#ccc;font:13px 'Segoe UI',sans-serif;padding:8px 14px}}
pre{{color:#e6e6e6;font-size:15px;line-height:1.35;margin:0;padding:14px 18px;white-space:pre}}
.cmd{{color:#9cdcfe}}</style>
<div class="bar">MySQL 8.4 · actividad4_mysql · actividad4_db</div>
<pre><span class="cmd">&gt; docker exec -it actividad4_mysql mysql -uactividad4 -p actividad4_db</span>

{html.escape(texto)}</pre>"""
    b = pw.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1100, "height": 300})
    pg.set_content(pagina)
    pg.screenshot(path=str(OUT / f"{nombre}.png"), full_page=True)
    b.close()
    print(f"{nombre:<40} MySQL")


def debe(texto):
    def f(cuerpo):
        assert texto in cuerpo, cuerpo
    return f


def cuenta(actor, nombre):
    return f'mutation {{\n  createAccount(\n    actorCompanyUserId: "{actor}"\n    input: {{ companyId: "{E}", accountType: CASH, name: "{nombre}" }}\n  ) {{\n    id\n    name\n  }}\n}}'


def permiso_rol(op, rol, permiso, actor):
    if op == "assign":
        return (f'mutation {{\n  assignPermissionToRole(\n    input: {{ roleId: "{R[rol]}", permissionId: "{P[permiso]}" }}\n'
                f'    actorCompanyUserId: "{actor}"\n  ) {{\n    id\n    role {{ code }}\n    permission {{ code }}\n    isActive\n  }}\n}}')
    return (f'mutation {{\n  removePermissionFromRole(\n    roleId: "{R[rol]}"\n    permissionId: "{P[permiso]}"\n'
            f'    actorCompanyUserId: "{actor}"\n  )\n}}')


LISTAS = (f'query {{\n  contador: rolePermissions(roleId: "{R["CONTADOR"]}") {{\n    permission {{ code }}\n  }}\n'
          f'  consulta: rolePermissions(roleId: "{R["CONSULTA"]}") {{\n    permission {{ code }}\n  }}\n}}')
SQL_PAREJA = ("SELECT rp.id, r.code AS rol, p.code AS permiso, rp.is_active\nFROM role_permissions rp\nJOIN roles r ON r.id = rp.role_id\n"
              "JOIN permissions p ON p.id = rp.permission_id\nWHERE r.code = 'CAPTURISTA' AND p.code = 'accounts.write';")
SQL_TODO = ("SELECT r.code AS rol, p.code AS permiso, rp.is_active\nFROM role_permissions rp\nJOIN roles r ON r.id = rp.role_id\n"
            "JOIN permissions p ON p.id = rp.permission_id\nORDER BY r.code, p.code;")
SQL_CONSULTA = SQL_TODO.replace("ORDER BY r.code, p.code;", "WHERE r.code = 'CONSULTA'\nORDER BY p.code;")
SQL_CONTEOS = ("SELECT\n  (SELECT COUNT(*) FROM roles) AS roles,\n  (SELECT COUNT(*) FROM permissions) AS permisos,\n"
               "  (SELECT COUNT(*) FROM role_permissions WHERE is_active = 1) AS parejas_activas;")


def movimiento():
    return (f'mutation MovimientoPedro {{\n  createTransaction(\n    actorCompanyUserId: "{M["Pedro"]}"\n    input: {{\n      accountId: "{CTA}"\n'
            f'      conceptId: "{CON}"\n      transactionType: INCOME\n      amount: "250.00"\n      shortDescription: "Venta de mostrador"\n    }}\n'
            f'  ) {{\n    id\n    amount\n    transactionType\n  }}\n}}')


with sync_playwright() as pw:
    if GRUPO == "principal":
        graphiql(pw, "00_catalogo", "query {\n  roles {\n    id\n    code\n  }\n  permissions {\n    id\n    code\n  }\n}", "ok")
        graphiql(pw, "01_lista_capturista_antes", f'query {{\n  rolePermissions(roleId: "{R["CAPTURISTA"]}") {{\n    role {{ code }}\n    permission {{ code }}\n    isActive\n  }}\n}}', "ok")
        antes = graphiql(pw, "07a_listas_antes", LISTAS, "ok")
        graphiql(pw, "02a_cuenta_maria_rechazada", cuenta(M["Maria"], "Cuenta de Maria"), "accounts.write")
        graphiql(pw, "02b_cuenta_jose_rechazada", cuenta(M["Jose"], "Cuenta de Jose"), "accounts.write")
        graphiql(pw, "03_ana_agrega_accounts_write", permiso_rol("assign", "CAPTURISTA", "accounts.write", M["Ana"]), "ok")
        graphiql(pw, "04a_cuenta_maria_aceptada", cuenta(M["Maria"], "Cuenta de Maria"), "ok")
        graphiql(pw, "04b_cuenta_jose_aceptada", cuenta(M["Jose"], "Cuenta de Jose"), "ok")
        graphiql(pw, "05_ana_quita_accounts_write", permiso_rol("remove", "CAPTURISTA", "accounts.write", M["Ana"]), "ok")
        mysql(pw, "05a_pareja_inactiva_mysql", [SQL_PAREJA], debe("accounts.write |         0"))
        graphiql(pw, "05b_cuenta_maria_rechazada", cuenta(M["Maria"], "Segunda de Maria"), "accounts.write")
        graphiql(pw, "05c_cuenta_jose_rechazada", cuenta(M["Jose"], "Segunda de Jose"), "accounts.write")
        login = graphiql(pw, "06_login_pedro", f'mutation {{\n  login(input: {{ email: "{ids["correos"]["Pedro"]}", password: "PruebaRoles2026!" }}) {{\n    token\n  }}\n}}', "ok")
        cabecera = json.dumps({"Authorization": "Bearer " + login["data"]["login"]["token"]}, indent=2)
        graphiql(pw, "06a_movimiento_pedro_rechazado", movimiento(), "transactions.write", cabecera)
        mysql(pw, "06a_movimientos_sin_fila_mysql", [f"SELECT COUNT(*) AS movimientos FROM transactions WHERE account_id = {CTA};"], debe("|           0 |"))
        graphiql(pw, "06b_assign_role_pedro", f'mutation {{\n  assignRole(\n    actorCompanyUserId: "{M["Ana"]}"\n    input: {{ companyUserId: "{M["Pedro"]}", roleId: "{R["CAPTURISTA"]}" }}\n  ) {{\n    id\n    role {{ code }}\n    isActive\n    companyUser {{\n      id\n      user {{ name }}\n    }}\n  }}\n}}', "ok")
        graphiql(pw, "06c_movimiento_pedro_aceptado", movimiento(), "ok", cabecera)
        mysql(pw, "06d_pedro_un_rol_activo_mysql", [
            f"SELECT cur.company_user_id, r.code AS rol, cur.is_active\nFROM company_user_roles cur\nJOIN roles r ON r.id = cur.role_id\nWHERE cur.company_user_id = {M['Pedro']};",
            f"SELECT COUNT(*) AS movimientos FROM transactions WHERE account_id = {CTA};",
        ])
        despues = graphiql(pw, "07b_listas_despues", LISTAS, "ok")
        assert antes == despues
        graphiql(pw, "07c_cuenta_luis_aceptada", f'mutation {{\n  createAccount(\n    actorCompanyUserId: "{M["Luis"]}"\n    input: {{ companyId: "{E}", accountType: DEBIT, name: "Bancos de Luis" }}\n  ) {{\n    id\n    name\n    accountType\n  }}\n}}', "ok")
        graphiql(pw, "08a_jose_rechazado", permiso_rol("assign", "CONSULTA", "concepts.write", M["Jose"]), "roles.write")
        mysql(pw, "08b_lista_consulta_sin_cambio_mysql", [SQL_CONSULTA])
        graphiql(pw, "08c_ana_agrega_concepts_write", permiso_rol("assign", "CONSULTA", "concepts.write", M["Ana"]), "ok")
        graphiql(pw, "08d_ana_quita_concepts_write", permiso_rol("remove", "CONSULTA", "concepts.write", M["Ana"]), "ok")
        mysql(pw, "09_select_role_permissions", [SQL_TODO], debe("28 rows in set"))
    else:
        graphiql(pw, "10a_catalogo_tras_reinicio", "query {\n  roles {\n    code\n  }\n  permissions {\n    code\n  }\n}", "ok")
        mysql(pw, "10b_reinicio_sin_duplicados", [SQL_CONTEOS], debe("|     4 |       10 |              26 |"))
