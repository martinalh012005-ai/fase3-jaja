#!/usr/bin/env python3
"""
Verifica que el despliegue con Docker funcione de punta a punta.

Uso (con los contenedores YA levantados con `docker compose up -d --build`):
    python docker/verificar_despliegue.py

Revisa: Docker instalado, contenedores sanos, aplicación respondiendo, base de datos
cargada (tablas, vistas, procedimientos, triggers), conexión de la aplicación a la base,
y que el usuario de la aplicación NO tenga permisos de DDL.

Si algo falla, copie TODA la salida y péguela en el chat.
No necesita instalar nada: usa solo la biblioteca estándar de Python.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def leer_env():
    """Contraseñas: valores por defecto de docker-compose.yml, o los de .env si existe."""
    valores = {"MYSQL_ROOT_PASSWORD": "root_astro_2026", "DB_PASSWORD": "astro_app_2026"}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


ENV = leer_env()
APP_URL = os.getenv("APP_URL", "http://localhost:8501")
ESPERA = int(os.getenv("ESPERA_SEGUNDOS", "150"))   # tiempo máximo de espera por contenedor


def ejecutar(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=RAIZ)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"No se encontró el comando: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "El comando tardó demasiado (timeout)"


def sql_db(consulta, usuario="root", clave=None):
    clave = clave if clave is not None else ENV["MYSQL_ROOT_PASSWORD"]
    return ejecutar(["docker", "exec", "astro_db", "mysql", f"-u{usuario}", f"-p{clave}", "-N", "-B", "-e", consulta])


def sin_aviso_clave(texto):
    return "\n".join(l for l in texto.splitlines() if "Using a password" not in l).strip()


# ----------------------------------------------------------------------
# Verificaciones: cada una devuelve (ok, detalle, servicio_para_logs)
# ----------------------------------------------------------------------
def v_docker():
    c, o, e = ejecutar(["docker", "--version"])
    return c == 0, o or e, None


def v_compose():
    c, o, e = ejecutar(["docker", "compose", "version"])
    return c == 0, o or e or "Instale/actualice Docker Desktop", None


def esperar_sano(nombre, espera=None):
    """Espera hasta que el contenedor esté 'running' y 'healthy'."""
    limite = time.time() + (espera or ESPERA)
    ultimo = "no encontrado"
    while True:
        c, o, e = ejecutar(["docker", "inspect", "-f", "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}", nombre])
        if c == 0:
            ultimo = o
            estado, _, salud = o.partition("|")
            if estado == "running" and salud in ("healthy", ""):
                return True, o
            if estado in ("exited", "dead"):
                return False, o
        else:
            ultimo = sin_aviso_clave(e) or "no existe (¿ejecutó docker compose up?)"
        if time.time() > limite:
            return False, ultimo
        time.sleep(5)


def v_contenedor(nombre, servicio):
    def f():
        ok, det = esperar_sano(nombre)
        return ok, f"{nombre}: {det}", servicio
    return f


def v_http():
    limite = time.time() + max(ESPERA // 2, 4)
    while True:
        try:
            with urllib.request.urlopen(APP_URL + "/_stcore/health", timeout=5) as r:
                salud = r.read().decode().strip()
            with urllib.request.urlopen(APP_URL + "/", timeout=5) as r:
                codigo = r.status
            return salud == "ok" and codigo == 200, f"{APP_URL} -> salud '{salud}', página principal HTTP {codigo}", "app"
        except Exception as ex:  # noqa: BLE001
            if time.time() > limite:
                return False, f"{APP_URL} no responde: {ex}", "app"
            time.sleep(4)


def v_objetos():
    q = ("SELECT (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='turismo_astronomico' AND TABLE_TYPE='BASE TABLE'),"
         "(SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA='turismo_astronomico'),"
         "(SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='turismo_astronomico'),"
         "(SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='turismo_astronomico')")
    c, o, e = sql_db(q)
    if c != 0:
        return False, sin_aviso_clave(e) or "no se pudo consultar MySQL", "db"
    partes = o.split()
    ok = partes == ["16", "6", "6", "4"]
    return ok, f"tablas/vistas/rutinas/triggers = {'/'.join(partes)} (esperado 16/6/6/4)", "db"


def v_datos():
    c, o, e = sql_db("SELECT (SELECT COUNT(*) FROM turismo_astronomico.reserva),(SELECT COUNT(*) FROM turismo_astronomico.evaluacion),"
                     "(SELECT COUNT(*) FROM turismo_astronomico.cuenta_usuario)")
    if c != 0:
        return False, sin_aviso_clave(e), "db"
    r, ev, cu = (int(x) for x in o.split())
    ok = r >= 800 and ev >= 400 and cu >= 40
    return ok, f"reservas={r}, evaluaciones={ev}, cuentas={cu} (originales: 1294 / 608 / 50)", "db"


def v_procedimiento():
    c, o, e = sql_db("CALL turismo_astronomico.sp_r4_centros_actividades_visitantes('2026-03-01','2026-06-30')")
    filas = len([l for l in o.splitlines() if l.strip()])
    return c == 0 and filas == 16, f"R4 devolvió {filas} filas (esperado 16)" + ("" if c == 0 else " | " + sin_aviso_clave(e)), "db"


def v_app_a_db():
    codigo = ("import os,pymysql;cx=pymysql.connect(host=os.environ['DB_HOST'],user=os.environ['DB_USER'],"
              "password=os.environ['DB_PASSWORD'],database=os.environ['DB_NAME']);c=cx.cursor();"
              "c.execute('SELECT COUNT(*) FROM cuenta_usuario');print(c.fetchone()[0])")
    c, o, e = ejecutar(["docker", "exec", "astro_app", "python", "-c", codigo])
    return c == 0 and o.strip().isdigit(), f"la aplicación lee la base y ve {o.strip() or '?'} cuentas" + ("" if c == 0 else " | " + e[-200:]), "app"


def v_minimo_privilegio():
    c, o, e = sql_db("SELECT COUNT(*) FROM turismo_astronomico.reserva", "astro_app", ENV["DB_PASSWORD"])
    if c != 0:
        return False, "astro_app no puede leer la base: " + sin_aviso_clave(e), "db"
    c2, o2, e2 = sql_db("CREATE TABLE turismo_astronomico.zz_prueba_ddl (x INT)", "astro_app", ENV["DB_PASSWORD"])
    if c2 == 0:  # no debería ocurrir: limpiar y avisar
        sql_db("DROP TABLE turismo_astronomico.zz_prueba_ddl")
        return False, "astro_app PUDO crear una tabla: tiene permisos de más", "db"
    return "denied" in e2.lower(), "astro_app puede leer pero NO puede crear tablas (DDL denegado)", "db"


VERIFICACIONES = [
    ("Docker instalado", v_docker),
    ("Docker Compose disponible", v_compose),
    ("Contenedor de base de datos sano (astro_db)", v_contenedor("astro_db", "db")),
    ("Contenedor de la aplicación sano (astro_app)", v_contenedor("astro_app", "app")),
    ("La aplicación responde en el navegador", v_http),
    ("Base creada: 16 tablas, 6 vistas, 6 procedimientos, 4 triggers", v_objetos),
    ("Datos cargados", v_datos),
    ("Un procedimiento almacenado se ejecuta", v_procedimiento),
    ("La aplicación se conecta a la base", v_app_a_db),
    ("Usuario de la aplicación con mínimo privilegio", v_minimo_privilegio),
]


def main():
    print("=" * 66)
    print(" VERIFICACIÓN DEL DESPLIEGUE DOCKER - TDFI103 Fase 2 Caso 2")
    print("=" * 66)
    fallas, servicios = [], set()
    for n, (nombre, fn) in enumerate(VERIFICACIONES, 1):
        try:
            ok, detalle, servicio = fn()
        except Exception as ex:  # noqa: BLE001
            ok, detalle, servicio = False, f"error inesperado: {ex}", None
        print(f"[{'OK' if ok else 'FALLA'}] {n:>2}. {nombre}\n         {detalle}")
        if not ok:
            fallas.append(nombre)
            if servicio:
                servicios.add(servicio)
        if n == 1 and not ok:
            break
    print("-" * 66)
    if not fallas:
        print(f"RESULTADO: TODO OK ({len(VERIFICACIONES)}/{len(VERIFICACIONES)}). El despliegue funciona.")
        print(f"Abra {APP_URL} (admin / Astro2026!) y saque las capturas del informe (sección 12.5).")
        return 0
    print(f"RESULTADO: {len(fallas)} verificación(es) fallaron:")
    for f in fallas:
        print("   -", f)
    for s in sorted(servicios):
        c, o, e = ejecutar(["docker", "compose", "logs", "--tail", "15", s])
        print(f"\n--- últimas líneas del registro de '{s}' ---\n{(o or e)[-1500:]}")
    print("\nCopie TODA esta salida y péguela en el chat para que la revisemos.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
