#!/usr/bin/env python3
"""
Generador de datos sintéticos - Caso 2: Centros de Turismo Astronómico
TDFI103 Proyecto Semestral 2026 - Fase 2

Genera sql/02_datos.sql con INSERT masivos, coherentes y REPRODUCIBLES
(semilla fija). Respeta claves foráneas, capacidades, estados y fechas.

Uso:
    pip install faker
    python generar_datos.py                  # escribe ../sql/02_datos.sql
    python generar_datos.py --salida otra.sql --semilla 2026
"""
import argparse
import hashlib
import random
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path

from faker import Faker

HOY = date(2026, 11, 15)          # fecha "actual" del escenario
INICIO = date(2026, 1, 5)         # inicio del período de actividades
FIN = date(2026, 12, 20)          # fin del período de actividades
PASSWORD_DEMO = "Astro2026!"      # contraseña de TODAS las cuentas de prueba

# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def q(v):
    """Literal SQL seguro."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(v, date):
        return "'" + v.isoformat() + "'"
    if isinstance(v, time):
        return "'" + v.strftime("%H:%M:%S") + "'"
    s = str(v).replace("\\", "\\\\").replace("'", "''")
    return "'" + s + "'"


def ascii_min(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "".join(c for c in s.lower() if c.isalnum())


def hash_password(usuario, password=PASSWORD_DEMO, iteraciones=200_000):
    """PBKDF2-SHA256 con sal determinista (reproducible). Formato:
    pbkdf2_sha256$iteraciones$sal$hash"""
    sal = hashlib.sha256(usuario.encode()).hexdigest()[:16]
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal}${h.hex()}"


class Salida:
    def __init__(self):
        self.partes = []

    def insert(self, tabla, columnas, filas, lote=100):
        cols = ", ".join(columnas)
        for i in range(0, len(filas), lote):
            bloque = filas[i:i + lote]
            vals = ",\n  ".join("(" + ", ".join(q(x) for x in f) + ")" for f in bloque)
            self.partes.append(f"INSERT INTO {tabla} ({cols}) VALUES\n  {vals};\n")

    def texto(self):
        return "\n".join(self.partes)


def pesos_pareto(n, alfa, rnd, tope=12.0):
    return [min(rnd.paretovariate(alfa), tope) for _ in range(n)]


def muestra_ponderada_sin_reemplazo(poblacion, pesos, k, rnd):
    elegidos, p, w = [], list(poblacion), list(pesos)
    k = min(k, len(p))
    for _ in range(k):
        i = rnd.choices(range(len(p)), weights=w, k=1)[0]
        elegidos.append(p.pop(i))
        w.pop(i)
    return elegidos


# ----------------------------------------------------------------------
# Datos maestros curados (realismo del dominio)
# ----------------------------------------------------------------------
REGIONES = [  # nombre, superficie protegida km2, presupuesto act. científicas CLP
    ("Tarapacá", 5420.50, 380_000_000),
    ("Antofagasta", 9810.20, 920_000_000),
    ("Atacama", 7350.75, 610_000_000),
    ("Coquimbo", 4120.00, 840_000_000),
    ("Valparaíso", 1890.30, 260_000_000),
    ("Metropolitana de Santiago", 640.10, 410_000_000),
    ("Biobío", 2210.60, 150_000_000),
    ("Magallanes y de la Antártica Chilena", 12650.90, 330_000_000),
]

# nombre, región (índice 1..8), inauguración, altitud, lat, lon, cap_diaria,
# presupuesto anual, estado, certificación, base de oscuridad (1-10)
CENTROS = [
    ("Centro Astronómico Salar del Huasco", 1, "2016-03-12", 3800, -20.270, -68.850, 220, 210_000_000, "OPERATIVO", "AVANZADA", 9),
    ("Observatorio Turístico Pampa del Tamarugal", 1, "2012-08-05", 1050, -20.500, -69.800, 160, 120_000_000, "OPERATIVO", "INTERMEDIA", 8),
    ("Centro Astronómico Valle de la Luna Austral", 2, "2009-11-20", 2510, -22.930, -68.200, 380, 450_000_000, "OPERATIVO", "EXCELENCIA", 9),
    ("Observatorio Ruta del Cóndor", 2, "2015-06-18", 2900, -23.500, -68.050, 190, 180_000_000, "OPERATIVO", "AVANZADA", 9),
    ("Centro Astronómico Altiplano Atacameño", 2, "2018-02-09", 3500, -22.600, -67.900, 150, 140_000_000, "MANTENIMIENTO", "INTERMEDIA", 10),
    ("Centro Astronómico Desierto Florido", 3, "2013-09-30", 820, -27.400, -70.400, 200, 190_000_000, "OPERATIVO", "AVANZADA", 8),
    ("Observatorio Cielos de Copiapó", 3, "2019-04-22", 1210, -27.370, -70.330, 120, 85_000_000, "OPERATIVO", "BASICA", 7),
    ("Centro Astronómico Valle del Elqui Norte", 4, "2008-01-15", 1120, -30.000, -70.500, 420, 520_000_000, "OPERATIVO", "EXCELENCIA", 8),
    ("Observatorio Cielo Limpio de Vicuña", 4, "2011-07-07", 930, -30.030, -70.700, 260, 260_000_000, "OPERATIVO", "AVANZADA", 7),
    ("Centro Astronómico Cochiguaz Alto", 4, "2017-12-01", 1820, -30.100, -70.200, 140, 130_000_000, "OPERATIVO", "INTERMEDIA", 9),
    ("Observatorio Río Hurtado", 4, "2014-05-26", 1310, -30.300, -70.700, 175, 150_000_000, "OPERATIVO", "AVANZADA", 8),
    ("Centro Astronómico Cordillera de Los Andes", 5, "2020-10-10", 1540, -32.900, -70.300, 130, 110_000_000, "OPERATIVO", "BASICA", 5),
    ("Observatorio Urbano Cerro Alto Santiago", 6, "2010-04-02", 910, -33.400, -70.500, 300, 230_000_000, "OPERATIVO", "INTERMEDIA", 3),
    ("Centro Astronómico Laja Austral", 7, "2021-01-28", 410, -37.300, -71.500, 90, 60_000_000, "CERRADO", "BASICA", 5),
    ("Observatorio Estrecho de Magallanes", 8, "2017-09-14", 150, -52.900, -70.800, 110, 95_000_000, "OPERATIVO", "INTERMEDIA", 7),
    ("Centro Astronómico Torres Australes", 8, "2022-03-03", 310, -51.000, -72.900, 100, 78_000_000, "OPERATIVO", "BASICA", 8),
]
POPULARIDAD_CENTRO = [1.0, 0.7, 2.4, 1.1, 0.6, 1.2, 0.4, 3.0, 1.8, 0.8, 1.0, 0.6, 1.6, 0.2, 0.5, 0.5]

NOMBRES_ZONA = ["Mirador Principal", "Terraza de Telescopios", "Domo Científico",
                "Explanada Sur", "Sector Aislado Norte", "Cúpula Solar",
                "Plataforma de Astrofotografía", "Sala de Proyección Celeste"]
EQUIPAMIENTO = ["Telescopios refractores", "Telescopio reflector de 40 cm", "Binoculares de campo",
                "Filtros solares H-alfa", "Cámaras CCD", "Montura ecuatorial computarizada",
                "Planetario portátil", "Telescopio Dobson de 30 cm", "Espectrógrafo didáctico"]

SOLAR = [  # nombre, tipo_evento
    ("Eclipse solar total", "eclipse"), ("Eclipse solar anular", "eclipse"),
    ("Eclipse solar parcial", "eclipse"), ("Eclipse solar híbrido", "eclipse"),
    ("Perlas de Baily", "eclipse"), ("Tránsito de Mercurio", "tránsito"),
    ("Tránsito de Venus", "tránsito"), ("Grupo de manchas solares complejo", "mancha solar"),
    ("Mancha solar gigante", "mancha solar"), ("Máximo del ciclo de manchas solares", "mancha solar"),
    ("Fáculas solares", "mancha solar"), ("Llamarada solar clase M", "llamarada"),
    ("Llamarada solar clase X", "llamarada"), ("Prominencia solar en bucle", "prominencia"),
    ("Prominencia solar eruptiva", "prominencia"), ("Filamento solar", "prominencia"),
    ("Eyección de masa coronal", "eyección"), ("Corona solar visible", "corona"),
    ("Granulación solar", "fotosfera"), ("Espículas cromosféricas", "cromosfera"),
    ("Tormenta geomagnética solar", "tormenta"), ("Viento solar intenso", "viento solar"),
]
LUNAR = [  # nombre, fase, tipo_evento
    ("Eclipse lunar total", "Luna llena", "eclipse"), ("Eclipse lunar parcial", "Luna llena", "eclipse"),
    ("Eclipse lunar penumbral", "Luna llena", "eclipse"), ("Luna de sangre", "Luna llena", "eclipse"),
    ("Superluna", "Luna llena", "superluna"), ("Superluna azul", "Luna llena", "superluna"),
    ("Micro luna", "Luna llena", "apogeo"), ("Luna azul", "Luna llena", "luna especial"),
    ("Luna de cosecha", "Luna llena", "luna especial"), ("Luna del cazador", "Luna llena", "luna especial"),
    ("Ocultación de Júpiter por la Luna", "Creciente", "ocultación"),
    ("Ocultación de Saturno por la Luna", "Creciente", "ocultación"),
    ("Ocultación de las Pléyades por la Luna", "Creciente", "ocultación"),
    ("Conjunción Luna-Venus", "Creciente", "conjunción"), ("Conjunción Luna-Marte", "Menguante", "conjunción"),
    ("Luz cenicienta lunar", "Creciente", "luz cenicienta"), ("Libración lunar extrema", "Cuarto creciente", "libración"),
    ("Terminador lunar en cuarto creciente", "Cuarto creciente", "terminador"),
    ("Luna nueva oscura", "Luna nueva", "luna nueva"), ("Cuarto menguante rasante", "Cuarto menguante", "terminador"),
]
ESPACIO = [  # nombre, tipo_objeto, distancia (años luz), magnitud aparente
    ("Nebulosa de Orión", "nebulosa", 1344, 4.00), ("Nebulosa de la Laguna", "nebulosa", 4100, 6.00),
    ("Nebulosa Trífida", "nebulosa", 5200, 6.30), ("Nebulosa de Carina", "nebulosa", 8500, 1.00),
    ("Nebulosa del Anillo", "nebulosa planetaria", 2300, 8.80), ("Nebulosa Helix", "nebulosa planetaria", 650, 7.60),
    ("Nebulosa del Cangrejo", "remanente de supernova", 6500, 8.40), ("Nebulosa Ojo de Gato", "nebulosa planetaria", 3300, 8.10),
    ("Nebulosa de la Tarántula", "nebulosa", 160000, 8.00), ("Saco de Carbón", "nebulosa oscura", 600, 3.00),
    ("Galaxia de Andrómeda", "galaxia", 2537000, 3.40), ("Galaxia del Triángulo", "galaxia", 2730000, 5.70),
    ("Gran Nube de Magallanes", "galaxia", 160000, 0.90), ("Pequeña Nube de Magallanes", "galaxia", 200000, 2.70),
    ("Galaxia del Remolino", "galaxia", 23000000, 8.40), ("Galaxia del Sombrero", "galaxia", 29000000, 8.00),
    ("Centaurus A", "galaxia", 13000000, 6.80), ("Galaxia del Escultor", "galaxia", 11000000, 8.00),
    ("Cúmulo de las Pléyades", "cúmulo abierto", 444, 1.60), ("Cúmulo del Joyero", "cúmulo abierto", 6400, 4.20),
    ("Omega Centauri", "cúmulo globular", 15800, 3.70), ("47 Tucanae", "cúmulo globular", 14800, 4.00),
    ("Cúmulo globular M13", "cúmulo globular", 22200, 5.80), ("Cúmulo globular M22", "cúmulo globular", 10600, 5.10),
    ("Cúmulo de las Híadas", "cúmulo abierto", 153, 0.50), ("Cúmulo de la Mariposa", "cúmulo abierto", 1000, 4.20),
    ("Cúmulo Doble de Perseo", "cúmulo abierto", 7500, 3.70), ("Eta Carinae", "estrella variable", 7500, 4.30),
]
NO_CLASIF = [
    ("Lluvia de meteoros Líridas", "Lluvia de meteoros anual"), ("Lluvia de meteoros Perseidas", "Lluvia de meteoros anual"),
    ("Cometa visible a ojo desnudo", "Cometa de período largo"), ("Luz zodiacal", "Fenómeno de luz dispersa"),
    ("Aurora austral", "Fenómeno atmosférico polar"),
]

PLANTILLAS_ACTIVIDAD = {
    "NOCTURNA": ["Noche de estrellas en {z}", "Recorrido del cielo austral", "Observación de nebulosas y galaxias",
                 "Constelaciones y mitología del hemisferio sur", "Cielo profundo para principiantes"],
    "SOLAR_DIURNA": ["Observación solar con filtro H-alfa", "Manchas y prominencias del Sol",
                     "Día solar en {z}", "Taller de astronomía solar"],
    "TALLER": ["Taller de uso de telescopios", "Taller de lectura de cartas celestes",
               "Taller de fotografía astronómica básica", "Taller para familias: construye tu planisferio"],
    "ASTROFOTOGRAFIA": ["Astrofotografía de la Vía Láctea", "Fotografía de cielo profundo",
                        "Astrofotografía lunar y planetaria"],
    "CIENTIFICA_GUIADA": ["Visita científica guiada al domo", "Observación asistida con investigadores",
                          "Seminario de campo: espectroscopía", "Noche científica de fenómenos transitorios"],
}
RANGO_VALOR = {"NOCTURNA": (12000, 26000), "SOLAR_DIURNA": (8000, 16000), "TALLER": (14000, 24000),
               "ASTROFOTOGRAFIA": (24000, 42000), "CIENTIFICA_GUIADA": (32000, 60000)}
EFECTO_MODALIDAD = {"NOCTURNA": 0.0, "SOLAR_DIURNA": -0.1, "TALLER": 0.1, "ASTROFOTOGRAFIA": 0.25, "CIENTIFICA_GUIADA": 0.35}

COMENTARIOS = {
    5: ["Experiencia inolvidable, el guía explicó todo con mucha claridad.", "Cielo espectacular, volvería sin dudarlo.",
        "Excelente organización y telescopios de gran calidad.", "Lo mejor de nuestro viaje, 100% recomendable."],
    4: ["Muy buena actividad, aunque hacía bastante frío.", "Buen guía y buen cielo, faltó un poco más de tiempo.",
        "Recomendable para familias, muy bien explicada."],
    3: ["Estuvo bien, pero había mucha gente en el grupo.", "El cielo se nubló a ratos, la actividad cumplió.",
        "Correcta, esperaba más tiempo en los telescopios."],
    2: ["Muy poca visibilidad y demasiadas personas por telescopio.", "La explicación fue muy técnica para el público general."],
    1: ["Se canceló parte de la observación por nubes y no hubo compensación.", "Mala experiencia, desorganizada y con retrasos."],
}


# ----------------------------------------------------------------------
def generar(semilla):
    rnd = random.Random(semilla)
    Faker.seed(semilla)
    fk = Faker("es_CL")
    out = Salida()
    out.partes.append(
        "-- =====================================================================\n"
        "-- 02_datos.sql  (GENERADO por generador/generar_datos.py - semilla %d)\n"
        "-- No editar a mano: volver a ejecutar el generador.\n"
        "-- =====================================================================\n"
        "SET NAMES utf8mb4;\nUSE turismo_astronomico;\n" % semilla)

    # ---- REGIONES
    out.insert("region", ["id_region", "nombre_oficial", "superficie_protegida", "presupuesto_actividades_cientificas"],
               [(i + 1, n, s, p) for i, (n, s, p) in enumerate(REGIONES)])

    # ---- CENTROS
    out.insert("centro_astronomico",
               ["id_centro", "id_region", "nombre", "fecha_inauguracion", "altitud", "latitud", "longitud",
                "capacidad_max_diaria", "presupuesto_anual", "estado_operativo", "nivel_certificacion", "activo"],
               [(i + 1, c[1], c[0], date.fromisoformat(c[2]), c[3], c[4], c[5], c[6], c[7], c[8], c[9],
                 0 if c[8] == "CERRADO" else 1) for i, c in enumerate(CENTROS)])

    # ---- ZONAS (3 por centro = 48)
    zonas = []   # (id, centro, cap, oscuridad)
    filas_z = []
    zid = 1
    for ci, c in enumerate(CENTROS, start=1):
        nombres = rnd.sample(NOMBRES_ZONA, 3)
        osc_base = c[10]
        # oscuridades distintas dentro del centro para que R10 sea no trivial
        offs = rnd.sample([-2, -1, 0, 1, 2], 3)
        for n_int, (nom, off) in enumerate(zip(nombres, offs), start=1):
            osc = max(1, min(10, osc_base + off))
            cap = rnd.choice([12, 15, 18, 20, 24, 30, 36, 40, 48, 60])
            acceso = rnd.choices(["PUBLICO", "RESTRINGIDO", "CIENTIFICO"], weights=[6, 2, 2])[0]
            equip = ", ".join(rnd.sample(EQUIPAMIENTO, rnd.randint(2, 3)))
            filas_z.append((zid, ci, n_int, nom, round(rnd.uniform(80, 1500), 2), osc, cap, equip, acceso))
            zonas.append((zid, ci, cap, osc))
            zid += 1
    out.insert("zona_observacion",
               ["id_zona", "id_centro", "numero_interno", "nombre", "superficie", "nivel_oscuridad",
                "capacidad_max", "equipamiento_disponible", "nivel_acceso"], filas_z)

    # ---- FENÓMENOS
    fen = []  # (id, tipo)
    filas_f, f_sol, f_lun, f_ep = [], [], [], []
    fid = 1

    def fecha_hist():
        return date(rnd.randint(1609, 2015), rnd.randint(1, 12), rnd.randint(1, 28))

    for nombre, ev in SOLAR:
        filas_f.append((fid, nombre, f"Fenómeno solar de tipo {ev}; se observa con filtros solares certificados.",
                        fecha_hist(), rnd.choice(["Anual", "Mensual", "Cada 11 años", "Irregular", "Cada varios años"]),
                        rnd.randint(2, 5), "SOLAR", 1))
        f_sol.append((fid, "SOLAR", ev, rnd.choice([5, 10, 30, 60, 120, 180, 240]), rnd.randint(1, 5)))
        fen.append((fid, "SOLAR")); fid += 1
    for nombre, fase, ev in LUNAR:
        filas_f.append((fid, nombre, f"Fenómeno lunar ({ev}) asociado a la fase {fase.lower()}.",
                        fecha_hist(), rnd.choice(["Mensual", "Anual", "Cada varios años", "Irregular"]),
                        rnd.randint(1, 5), "LUNAR", 1))
        f_lun.append((fid, "LUNAR", fase, ev, round(rnd.uniform(15, 100), 2)))
        fen.append((fid, "LUNAR")); fid += 1
    for nombre, tipo, dist, mag in ESPACIO:
        filas_f.append((fid, nombre, f"Objeto de espacio profundo ({tipo}) visible con instrumentos de apertura media.",
                        fecha_hist(), "Permanente", rnd.randint(3, 5), "ESPACIO_PROFUNDO", 1))
        f_ep.append((fid, "ESPACIO_PROFUNDO", tipo, dist, mag))
        fen.append((fid, "ESPACIO_PROFUNDO")); fid += 1
    for nombre, desc in NO_CLASIF:
        filas_f.append((fid, nombre, desc + "; aún sin clasificación dentro de los tres tipos del catálogo.",
                        fecha_hist(), rnd.choice(["Anual", "Irregular"]), rnd.randint(1, 3), "NO_CLASIFICADO", 1))
        fen.append((fid, "NO_CLASIFICADO")); fid += 1
    out.insert("fenomeno_astronomico",
               ["id_fenomeno", "nombre", "descripcion", "fecha_primera_observacion", "frecuencia_estimada",
                "nivel_interes_cientifico", "tipo_clasificacion", "activo"], filas_f)
    out.insert("fenomeno_solar", ["id_fenomeno", "tipo_clasificacion", "tipo_evento", "duracion_estimada_min", "nivel_intensidad"], f_sol)
    out.insert("fenomeno_lunar", ["id_fenomeno", "tipo_clasificacion", "fase_lunar", "tipo_evento", "visibilidad_porcentaje"], f_lun)
    out.insert("fenomeno_espacio_profundo", ["id_fenomeno", "tipo_clasificacion", "tipo_objeto", "distancia_anios_luz", "magnitud_aparente"], f_ep)

    # ---- OBSERVACIONES (registro zona-fenómeno)
    peso_zona = [POPULARIDAD_CENTRO[z[1] - 1] * (0.6 + z[3] / 10) for z in zonas]
    peso_fen = pesos_pareto(len(fen), 1.1, rnd, tope=14)
    vistos, filas_o, oid = set(), [], 1
    while len(filas_o) < 420:
        z = rnd.choices(zonas, weights=peso_zona, k=1)[0]
        f = rnd.choices(fen, weights=peso_fen, k=1)[0]
        d = date(2025, 1, 1) + timedelta(days=rnd.randint(0, (date(2026, 11, 14) - date(2025, 1, 1)).days))
        if f[1] == "SOLAR":
            h = time(rnd.randint(9, 15), rnd.choice([0, 15, 30, 45]))
        else:
            h = time(rnd.choice([20, 21, 22, 23, 0, 1, 2, 3]), rnd.choice([0, 15, 30, 45]))
        llave = (z[0], f[0], d, h)
        if llave in vistos:
            continue
        vistos.add(llave)
        clima = rnd.choices(["DESPEJADO", "PARCIALMENTE_NUBLADO", "NUBLADO", "VIENTO_FUERTE"], weights=[60, 22, 12, 6])[0]
        res = {"DESPEJADO": rnd.choices(["EXITOSA", "PARCIAL", "FALLIDA"], weights=[88, 10, 2]),
               "PARCIALMENTE_NUBLADO": rnd.choices(["EXITOSA", "PARCIAL", "FALLIDA"], weights=[45, 45, 10]),
               "NUBLADO": rnd.choices(["EXITOSA", "PARCIAL", "FALLIDA"], weights=[8, 32, 60]),
               "VIENTO_FUERTE": rnd.choices(["EXITOSA", "PARCIAL", "FALLIDA"], weights=[30, 45, 25])}[clima][0]
        filas_o.append((oid, z[0], f[0], d, h, clima, rnd.choice([10, 15, 20, 30, 45, 60, 90, 120, 180]), res))
        oid += 1
    out.insert("observacion",
               ["id_observacion", "id_zona", "id_fenomeno", "fecha", "hora", "condiciones_climaticas",
                "duracion_min", "resultado"], filas_o)

    # ---- PERSONAS: trabajadores 1..60, visitantes 61..280
    N_TRAB, N_VIS = 60, 220
    usados_email = set()

    def persona(pid, tipo):
        nombre, ap1, ap2 = fk.first_name(), fk.last_name(), fk.last_name()
        base = f"{ascii_min(nombre)}.{ascii_min(ap1)}"
        email, k = f"{base}@correo.cl", 1
        while email in usados_email:
            k += 1
            email = f"{base}{k}@correo.cl"
        usados_email.add(email)
        tel = "+569" + "".join(str(rnd.randint(0, 9)) for _ in range(8))
        return (pid, nombre, ap1, ap2, tel, email, tipo)

    # cargos: 12 administrativos, 24 guías, 14 técnicos, 10 investigadores
    cargos = (["ADMINISTRATIVO"] * 12 + ["GUIA_CIENTIFICO"] * 24 + ["TECNICO"] * 14 + ["INVESTIGADOR"] * 10)
    rnd.shuffle(cargos)
    # los 16 primeros guías se reparten uno por centro (cada centro tiene ≥1 guía)
    idx_guias = [i for i, c in enumerate(cargos) if c == "GUIA_CIENTIFICO"]
    centros_trab = [None] * N_TRAB
    for k, i in enumerate(idx_guias[:16]):
        centros_trab[i] = k + 1
    for i in range(N_TRAB):
        if centros_trab[i] is None:
            centros_trab[i] = rnd.choices(range(1, 17), weights=POPULARIDAD_CENTRO, k=1)[0]

    personas, trabajadores = [], []
    for i in range(N_TRAB):
        pid = i + 1
        personas.append(persona(pid, "TRABAJADOR"))
        trabajadores.append((pid, "TRABAJADOR", centros_trab[i], cargos[i],
                             date(2010, 1, 1) + timedelta(days=rnd.randint(0, 5800))))
    visitantes = []
    for j in range(N_VIS):
        pid = N_TRAB + j + 1
        personas.append(persona(pid, "VISITANTE"))
        visitantes.append((pid, "VISITANTE", date(2024, 6, 1) + timedelta(days=rnd.randint(0, 880))))
    out.insert("persona", ["id_persona", "nombre_pila", "ap_paterno", "ap_materno", "telefono", "email", "tipo_persona"], personas)
    out.insert("visitante", ["id_persona", "tipo_persona", "fecha_registro"], visitantes)
    out.insert("trabajador", ["id_persona", "tipo_persona", "id_centro", "cargo", "fecha_contratacion"], trabajadores)

    guias_por_centro = {}
    for t in trabajadores:
        if t[3] == "GUIA_CIENTIFICO":
            guias_por_centro.setdefault(t[2], []).append(t[0])

    # ---- ACTIVIDADES (180): 1 por zona + 132 ponderadas por popularidad
    zona_por_id = {z[0]: z for z in zonas}
    ids_zona = [z[0] for z in zonas]
    asignacion = ids_zona[:] + rnd.choices(ids_zona, weights=peso_zona, k=180 - len(ids_zona))
    rnd.shuffle(asignacion)
    actividades, filas_a = [], []
    for aid, zid_ in enumerate(asignacion, start=1):
        z = zona_por_id[zid_]
        modalidad = rnd.choices(list(PLANTILLAS_ACTIVIDAD), weights=[40, 14, 18, 12, 16])[0]
        nombre_zona = next(f[3] for f in filas_z if f[0] == zid_)
        nombre = rnd.choice(PLANTILLAS_ACTIVIDAD[modalidad]).format(z=nombre_zona)
        fecha = INICIO + timedelta(days=rnd.randint(0, (FIN - INICIO).days))
        horario = time(rnd.randint(10, 15), rnd.choice([0, 30])) if modalidad == "SOLAR_DIURNA" \
            else time(rnd.choice([19, 20, 21, 22]), rnd.choice([0, 30]))
        if fecha < HOY:
            estado = rnd.choices(["REALIZADA", "CANCELADA"], weights=[92, 8])[0]
        else:
            estado = rnd.choices(["PROGRAMADA", "CANCELADA"], weights=[95, 5])[0]
        cap = rnd.randint(6, min(z[2], 22))
        lo, hi = RANGO_VALOR[modalidad]
        valor = round(rnd.randint(lo // 500, hi // 500) * 500, 2)
        guia = rnd.choice(guias_por_centro[z[1]])
        dur = rnd.choice([60, 90, 120, 150, 180, 240])
        actividades.append(dict(id=aid, zona=zid_, centro=z[1], osc=z[3], fecha=fecha, estado=estado,
                                cap=cap, valor=valor, modalidad=modalidad))
        filas_a.append((aid, f"ACT-{aid:04d}", zid_, guia, nombre, fecha, horario, dur, modalidad, valor, cap, estado))
    out.insert("actividad_observacion",
               ["id_actividad", "cod_actividad", "id_zona", "id_guia", "nombre", "fecha", "horario",
                "duracion_min", "modalidad", "valor", "capacidad", "estado"], filas_a)

    # ---- RESERVAS
    ids_vis = [v[0] for v in visitantes]
    pesos_vis = pesos_pareto(len(ids_vis), 1.6, rnd, tope=5)
    ocupado = set()   # (visitante, fecha): no asistir a dos actividades el mismo día
    filas_r, reservas, rid = [], [], 1
    for a in sorted(actividades, key=lambda x: x["fecha"]):
        if a["estado"] == "CANCELADA":
            n = rnd.randint(1, min(6, a["cap"]))
        elif a["estado"] == "REALIZADA":
            n = max(2, round(a["cap"] * rnd.uniform(0.25, 0.9)))
        else:
            n = max(1, round(a["cap"] * rnd.uniform(0.1, 0.7)))
        disponibles = [v for v in ids_vis if (v, a["fecha"]) not in ocupado]
        pw = [pesos_vis[ids_vis.index(v)] for v in disponibles]
        elegidos = muestra_ponderada_sin_reemplazo(disponibles, pw, n, rnd)
        confirmadas = 0
        for v in elegidos:
            if a["estado"] == "CANCELADA":
                est = "CANCELADA"
            else:
                est = "CANCELADA" if rnd.random() < 0.08 else "CONFIRMADA"
            if est == "CONFIRMADA" and confirmadas >= a["cap"]:
                est = "CANCELADA"
            asist = 0
            if est == "CONFIRMADA":
                confirmadas += 1
                ocupado.add((v, a["fecha"]))
                if a["estado"] == "REALIZADA":
                    asist = 1 if rnd.random() < 0.82 else 0
            f_res = datetime.combine(a["fecha"] - timedelta(days=rnd.randint(1, 45)),
                                     time(rnd.randint(8, 22), rnd.randint(0, 59), rnd.randint(0, 59)))
            obs = rnd.choice([None, None, None, "Requiere acceso para silla de ruedas", "Viaja con menores de edad",
                              "Solicita guía en inglés", "Cumpleaños del visitante", "Alergia a la humedad del cerro"])
            filas_r.append((rid, v, a["id"], f_res, est, asist, obs))
            reservas.append(dict(id=rid, act=a, asist=asist, est=est))
            rid += 1
    out.insert("reserva",
               ["id_reserva", "id_visitante", "id_actividad", "fecha_reserva", "estado", "asistencia_efectiva",
                "observaciones"], filas_r)

    # ---- EVALUACIONES (solo asistentes; ~68 % evalúa)
    asistentes_por_act = {}
    for r in reservas:
        if r["asist"]:
            asistentes_por_act[r["act"]["id"]] = asistentes_por_act.get(r["act"]["id"], 0) + 1
    filas_e, eid = [], 1
    for r in reservas:
        if not r["asist"] or rnd.random() > 0.68:
            continue
        a = r["act"]
        ocupacion = asistentes_por_act[a["id"]] / a["cap"]
        # escenario diseñado: la saturación (más asistentes por actividad) reduce levemente la evaluación
        mu = (3.9 + 0.12 * (a["osc"] - 6) + EFECTO_MODALIDAD[a["modalidad"]]
              - 0.9 * (ocupacion - 0.5) - 0.07 * (asistentes_por_act[a["id"]] - 6))
        cal = max(1, min(5, round(rnd.gauss(mu, 0.85))))
        comentario = rnd.choice(COMENTARIOS[cal]) if rnd.random() < 0.7 else None
        fe = min(a["fecha"] + timedelta(days=rnd.randint(0, 5)), HOY)
        filas_e.append((eid, r["id"], fe, cal, comentario))
        eid += 1
    out.insert("evaluacion", ["id_evaluacion", "id_reserva", "fecha", "calificacion", "comentario"], filas_e)

    # ---- ROLES Y CUENTAS
    roles = [
        (1, "ADMINISTRADOR", "Gestión completa del sistema", "reservas,crud_centros,crud_fenomenos,usuarios,dashboard", 1),
        (2, "OPERADOR", "Registro de reservas y consulta del dashboard", "reservas,dashboard", 1),
        (3, "ANALISTA", "Solo consulta del dashboard", "dashboard", 1),
    ]
    out.insert("rol", ["id_rol", "nombre", "descripcion", "permisos", "activo"], roles)

    cuentas, ya_admin, n_tec = [], 0, 0
    base_usuario = {1: "admin", 2: "operador", 3: "analista"}
    asignados_demo = set()
    nombre_por_id = {p[0]: p for p in personas}
    for t in trabajadores:
        pid, cargo = t[0], t[3]
        if cargo == "ADMINISTRATIVO":
            ya_admin += 1
            rol = 1 if ya_admin <= 4 else 2
        elif cargo == "GUIA_CIENTIFICO":
            rol = 2
        elif cargo == "INVESTIGADOR":
            rol = 3
        else:  # TECNICO: solo 4 de 14 tienen cuenta
            n_tec += 1
            if n_tec > 4:
                continue
            rol = 2
        p = nombre_por_id[pid]
        usuario = f"{ascii_min(p[1])[0]}{ascii_min(p[2])}"[:20]
        if rol not in asignados_demo:
            usuario = base_usuario[rol]
            asignados_demo.add(rol)
        cuentas.append([pid, rol, usuario])
    # unicidad de nombres de usuario
    vistos_u = set()
    for c in cuentas:
        u, k = c[2], 1
        while u in vistos_u:
            k += 1
            u = f"{c[2]}{k}"
        c[2] = u
        vistos_u.add(u)
    out.insert("cuenta_usuario",
               ["id_cuenta", "id_trabajador", "id_rol", "nombre_usuario", "contrasena_hash", "activa"],
               [(i + 1, c[0], c[1], c[2], hash_password(c[2]), 1) for i, c in enumerate(cuentas)])

    resumen = dict(region=len(REGIONES), centros=len(CENTROS), zonas=len(zonas), fenomenos=len(fen),
                   observaciones=len(filas_o), personal=N_TRAB, visitantes=N_VIS, actividades=len(filas_a),
                   reservas=len(filas_r), evaluaciones=len(filas_e), cuentas=len(cuentas), roles=len(roles))
    return out.texto(), resumen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default=str(Path(__file__).resolve().parent.parent / "sql" / "02_datos.sql"))
    args = ap.parse_args()
    sql, resumen = generar(args.semilla)
    Path(args.salida).write_text(sql, encoding="utf-8")
    print(f"Archivo generado: {args.salida}")
    for k, v in resumen.items():
        print(f"  {k:14} {v}")


if __name__ == "__main__":
    main()
