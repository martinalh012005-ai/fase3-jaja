#!/usr/bin/env python3
"""
Genera el MERE definitivo (Fase 2, Caso 2) en dos formatos a partir de UNA especificación:
  - MERE_Caso2_corregido.drawio  (editable en app.diagrams.net)
  - MERE_Caso2_corregido.png     (imagen legible para el informe)
Notación: Chen extendida (EER). Cardinalidades (mín,máx) junto a CADA entidad,
leídas como "esa entidad participa mín..máx veces en la relación".
"""
import math
import html
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, Polygon

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# ESPECIFICACIÓN
# ---------------------------------------------------------------------------
# kind: E entidad, W entidad débil, R relación, I relación identificadora, D especialización
NODES = {
    # --- territorio
    "REGION":   dict(k="E", x=1650, y=300, t="REGION"),
    "r_alb_rc": dict(k="R", x=2150, y=300, t="alberga"),
    "CENTRO":   dict(k="E", x=2750, y=300, t="CENTRO_ASTRONOMICO"),
    "r_cont":   dict(k="I", x=2750, y=800, t="contiene"),
    "ZONA":     dict(k="W", x=2750, y=1300, t="ZONA_OBSERVACION"),
    # --- observaciones y fenómenos
    "r_reg":    dict(k="R", x=2150, y=1300, t="registra"),
    "OBSERV":   dict(k="E", x=1600, y=1300, t="OBSERVACION"),
    "r_corr_f": dict(k="R", x=1050, y=1300, t="corresponde a"),
    "FENOM":    dict(k="E", x=500,  y=1300, t="FENOMENO_ASTRONOMICO"),
    "d_f":      dict(k="D", x=500,  y=1750, t="d"),
    "SOLAR":    dict(k="E", x=150,  y=2150, t="SOLAR"),
    "LUNAR":    dict(k="E", x=650,  y=2150, t="LUNAR"),
    "ESPACIO":  dict(k="E", x=1150, y=2150, t="ESPACIO_PROFUNDO"),
    # --- actividades y reservas
    "r_alb_za": dict(k="R", x=2750, y=1800, t="alberga"),
    "ACTIV":    dict(k="E", x=2750, y=2250, t="ACTIVIDAD_OBSERVACION"),
    "r_corr_a": dict(k="R", x=2750, y=2750, t="corresponde a"),
    "RESERVA":  dict(k="E", x=2750, y=3250, t="RESERVA"),
    "r_orig":   dict(k="R", x=2150, y=3250, t="origina"),
    "EVAL":     dict(k="E", x=1600, y=3250, t="EVALUACION"),
    "r_real":   dict(k="R", x=3450, y=3250, t="realiza"),
    # --- personas
    "VISIT":    dict(k="E", x=4150, y=3250, t="VISITANTE"),
    "d_p":      dict(k="D", x=4150, y=2650, t="d"),
    "PERSONA":  dict(k="E", x=4750, y=2650, t="PERSONA"),
    "TRAB":     dict(k="E", x=4150, y=2050, t="TRABAJADOR"),
    "r_pert":   dict(k="R", x=3750, y=1050, t="pertenece a"),
    "r_guia":   dict(k="R", x=3450, y=2150, t="guía de"),
    # --- usuarios
    "r_posee":  dict(k="R", x=4650, y=1450, t="posee"),
    "CUENTA":   dict(k="E", x=5150, y=900, t="CUENTA_USUARIO"),
    "r_asig":   dict(k="R", x=5150, y=1450, t="tiene"),
    "ROL":      dict(k="E", x=5150, y=2000, t="ROL"),
}

# atributos: (nombre, flags) flags: pk, partial(clave parcial), comp[...] (compuesto)
ATTRS = {
    "REGION": [("id_region", "pk"), "nombre_oficial", "superficie_protegida",
               "presupuesto_actividades_cientificas"],
    "CENTRO": [("id_centro", "pk"), "nombre", "fecha_inauguracion", "altitud",
               ("coordenadas", ["latitud", "longitud"]), "capacidad_max_diaria",
               "presupuesto_anual", "estado_operativo", "nivel_certificacion", "activo"],
    "ZONA": [("numero_interno", "partial"), "nombre", "superficie", "nivel_oscuridad",
             "capacidad_max", "equipamiento_disponible", "nivel_acceso"],
    "OBSERV": [("id_observacion", "pk"), "fecha", "hora", "condiciones_climaticas",
               "duracion_min", "resultado"],
    "FENOM": [("id_fenomeno", "pk"), "nombre", "descripcion", "fecha_primera_observacion",
              "frecuencia_estimada", "nivel_interes_cientifico", "tipo_clasificacion", "activo"],
    "SOLAR": ["tipo_evento", "duracion_estimada_min", "nivel_intensidad"],
    "LUNAR": ["fase_lunar", "tipo_evento", "visibilidad_porcentaje"],
    "ESPACIO": ["tipo_objeto", "distancia_anios_luz", "magnitud_aparente"],
    "ACTIV": [("id_actividad", "pk"), "cod_actividad", "nombre", "fecha", "horario",
              "duracion_min", "modalidad", "valor", "capacidad", "estado"],
    "RESERVA": [("id_reserva", "pk"), "fecha_reserva", "estado", "asistencia_efectiva", "observaciones"],
    "EVAL": [("id_evaluacion", "pk"), "fecha", "calificacion", "comentario"],
    "PERSONA": [("id_persona", "pk"), ("nombre", ["nombre_pila", "ap_paterno", "ap_materno"]),
                "telefono", "email", "tipo_persona"],
    "VISIT": ["fecha_registro"],
    "TRAB": ["cargo", "fecha_contratacion"],
    "CUENTA": [("id_cuenta", "pk"), "nombre_usuario", "contrasena_hash", "activa"],
    "ROL": [("id_rol", "pk"), "nombre", "descripcion", "permisos", "activo"],
}

# aristas (entidad, nodo_relacion, cardinalidad, estilo)   estilo: '' | 'total'
# Cada relación tiene exactamente dos extremos con cardinalidad.
EDGES = [
    ("REGION", "r_alb_rc", "(0,N)", ""), ("CENTRO", "r_alb_rc", "(1,1)", ""),
    ("CENTRO", "r_cont", "(1,N)", ""), ("ZONA", "r_cont", "(1,1)", "total"),
    ("ZONA", "r_reg", "(0,N)", ""), ("OBSERV", "r_reg", "(1,1)", ""),
    ("FENOM", "r_corr_f", "(0,N)", ""), ("OBSERV", "r_corr_f", "(1,1)", ""),
    ("ZONA", "r_alb_za", "(0,N)", ""), ("ACTIV", "r_alb_za", "(1,1)", ""),
    ("ACTIV", "r_corr_a", "(0,N)", ""), ("RESERVA", "r_corr_a", "(1,1)", ""),
    ("VISIT", "r_real", "(0,N)", ""), ("RESERVA", "r_real", "(1,1)", ""),
    ("RESERVA", "r_orig", "(0,1)", ""), ("EVAL", "r_orig", "(1,1)", ""),
    ("CENTRO", "r_pert", "(0,N)", ""), ("TRAB", "r_pert", "(1,1)", ""),
    ("TRAB", "r_guia", "(0,N)", ""), ("ACTIV", "r_guia", "(0,1)", ""),
    ("TRAB", "r_posee", "(0,1)", ""), ("CUENTA", "r_posee", "(1,1)", ""),
    ("ROL", "r_asig", "(0,N)", ""), ("CUENTA", "r_asig", "(1,1)", ""),
]
# especializaciones: (superclase, nodo d, [subclases], total?)
ISA = [("FENOM", "d_f", ["SOLAR", "LUNAR", "ESPACIO"], False),
       ("PERSONA", "d_p", ["VISIT", "TRAB"], True)]

COLOR = {  # relleno, borde (misma paleta del diagrama original)
    "E": ("#dae8fc", "#6c8ebf"), "W": ("#f8cecc", "#b85450"), "R": ("#fff2cc", "#d6b656"),
    "I": ("#f8cecc", "#b85450"), "D": ("#ffffff", "#333333"),
}
FONT = 17


def w_text(t, base=26, per=9.3):
    return base + per * len(t)


def size(n):
    nd = NODES[n]
    k, t = nd["k"], nd["t"]
    if k in ("E", "W"):
        return max(170, w_text(t, 44, 14.2)), 72
    if k in ("R", "I"):
        return max(170, w_text(t, 70, 11.5)), 100
    return 62, 62


# ---------------------------------------------------------------------------
# DISTRIBUCIÓN DE ATRIBUTOS (abanico automático lejos de las conexiones)
# ---------------------------------------------------------------------------
def conexiones(ent):
    res = []
    for e, r, _, _ in EDGES:
        if e == ent:
            res.append(r)
    for sup, d, subs, _ in ISA:
        if sup == ent:
            res.append(d)
        if ent in subs:
            res.append(d)
    return res


def ang(a, b):
    return math.degrees(math.atan2(NODES[b]["y"] - NODES[a]["y"], NODES[b]["x"] - NODES[a]["x"])) % 360


def arcos_libres(ent, margen=38):
    bloqueos = [ang(ent, c) for c in conexiones(ent)]
    pasos = 360
    libres = []
    for i in range(pasos):
        a = i
        if all(min(abs(a - b), 360 - abs(a - b)) > margen for b in bloqueos):
            libres.append(a)
    return libres


def puntos_aristas():
    """puntos muestreados sobre todas las líneas estructurales (para no taparlas)."""
    pts = []
    def seg(a, b):
        ax_, ay_ = NODES[a]["x"], NODES[a]["y"]
        bx_, by_ = NODES[b]["x"], NODES[b]["y"]
        for t in [i / 24 for i in range(25)]:
            pts.append((ax_ + (bx_ - ax_) * t, ay_ + (by_ - ay_) * t))
    for e, r, _, _ in EDGES:
        seg(e, r)
    for sup, d, subs, _ in ISA:
        seg(sup, d)
        for s_ in subs:
            seg(d, s_)
    return pts


def solapa(x, y, w, h, caja, margen=10):
    return abs(x - caja[0]) < (w + caja[2]) / 2 + margen and abs(y - caja[1]) < (h + caja[3]) / 2 + margen


def segmento_libre(p, q, cajas, ignorar_ent=None, ancho=0):
    for t in [i / 20 for i in range(1, 20)]:
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        for c in cajas:
            if abs(x - c[0]) < c[2] / 2 + 2 and abs(y - c[1]) < c[3] / 2 + 2:
                return False
    return True


def colocar_atributos(overrides):
    pos = {}
    lineas = puntos_aristas()
    cajas = [(nd["x"], nd["y"], nd["w"], nd["h"]) for nd in NODES.values()]
    orden = sorted(ATTRS, key=lambda e: -len(ATTRS[e]))
    for ent in orden:
        lst = ATTRS[ent]
        n = len(lst)
        libres = set(arcos_libres(ent, 30))
        cx, cy = NODES[ent]["x"], NODES[ent]["y"]
        # ángulos objetivo: repartidos en el arco libre mayor
        lib = sorted(libres)
        inicio = next((a for a in lib if (a - 1) % 360 not in libres), lib[0])
        seq, a = [], inicio
        while a in libres and len(seq) < 360:
            seq.append(a); a = (a + 1) % 360
        for i, item in enumerate(lst):
            nombre, f = item if isinstance(item, tuple) else (item, "")
            w, h = w_text(nombre, 30, 10.8), 44
            obj = seq[min(len(seq) - 1, int((i + 0.5) / n * len(seq)))]
            mejor = None
            for r in range(190, 900, 20):
                for da in range(0, 181, 4):
                    for sgn in ((1, -1) if da else (1,)):
                        ai = (obj + sgn * da) % 360
                        if ai not in libres:
                            continue
                        x = cx + (r + NODES[ent]["w"] / 4) * math.cos(math.radians(ai))
                        y = cy + r * math.sin(math.radians(ai))
                        if any(solapa(x, y, w, h, c) for c in cajas):
                            continue
                        if any(abs(x - px) < w / 2 + 8 and abs(y - py) < h / 2 + 8 for px, py in lineas):
                            continue
                        if not segmento_libre((cx, cy), (x, y), [c for c in cajas if c[:2] != (cx, cy)]):
                            continue
                        costo = r + 1.6 * da
                        if mejor is None or costo < mejor[0]:
                            mejor = (costo, x, y, ai, r)
                if mejor and mejor[0] <= r:   # ya no hay nada más barato más lejos
                    break
            if mejor is None:
                mejor = (0, cx + 300, cy + 300, obj, 300)
            _, x, y, ai, r = mejor
            pos[(ent, i)] = dict(x=x, y=y, t=nombre, f=f, ent=ent, ang=ai, r=r, w=w, h=h, k="A")
            cajas.append((x, y, w, h))
    return pos


# ---------------------------------------------------------------------------
# Geometría auxiliar
# ---------------------------------------------------------------------------
def borde(nodo, hacia, tipo=None):
    """punto del borde del nodo (rect/rombo/elipse) en la dirección de 'hacia'."""
    cx, cy = (nodo["x"], nodo["y"])
    w, h = nodo["w"], nodo["h"]
    dx, dy = hacia[0] - cx, hacia[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    k = nodo["k"]
    if k in ("E", "W"):
        s = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
    elif k in ("R", "I"):
        s = 1 / (abs(dx) / (w / 2) + abs(dy) / (h / 2))
    else:
        s = 1 / math.hypot(dx / (w / 2), dy / (h / 2))
    return cx + dx * s, cy + dy * s


def preparar(overrides):
    for n, nd in NODES.items():
        nd["w"], nd["h"] = size(n)
    attrs = colocar_atributos(overrides)
    # hijos de atributos compuestos (también con búsqueda de espacio libre)
    cajas = [(nd["x"], nd["y"], nd["w"], nd["h"]) for nd in NODES.values()]
    cajas += [(a["x"], a["y"], a["w"], a["h"]) for a in attrs.values()]
    lineas = puntos_aristas()
    hijos = []
    for (ent, i), a in list(attrs.items()):
        orig = ATTRS[ent][i]
        if isinstance(orig, tuple) and isinstance(orig[1], list):
            for j, hnom in enumerate(orig[1]):
                w, h = w_text(hnom, 30, 10.8), 44
                mejor = None
                for r in range(110, 600, 15):
                    for da in range(0, 91, 5):
                        for sgn in ((1, -1) if da else (1,)):
                            ai = (a["ang"] + sgn * da + (j - (len(orig[1]) - 1) / 2) * 25) % 360
                            x = a["x"] + r * math.cos(math.radians(ai))
                            y = a["y"] + r * math.sin(math.radians(ai))
                            if any(solapa(x, y, w, h, c) for c in cajas):
                                continue
                            if any(abs(x - px) < w / 2 + 8 and abs(y - py) < h / 2 + 8 for px, py in lineas):
                                continue
                            if not segmento_libre((a["x"], a["y"]), (x, y), [c for c in cajas if c[:2] != (a["x"], a["y"])]):
                                continue
                            costo = r + 1.2 * da
                            if mejor is None or costo < mejor[0]:
                                mejor = (costo, x, y)
                    if mejor and mejor[0] <= r:
                        break
                if mejor is None:
                    mejor = (0, a["x"] + 150, a["y"] + 100)
                _, x, y = mejor
                hijos.append(dict(x=x, y=y, t=hnom, f="", ent=ent, k="A", w=w, h=h, padre=(ent, i)))
                cajas.append((x, y, w, h))
    return attrs, hijos


def colisiones(attrs, hijos):
    cajas = []
    for n, nd in NODES.items():
        cajas.append((n, nd["x"], nd["y"], nd["w"], nd["h"]))
    for (e, i), a in attrs.items():
        cajas.append((f"{e}.{a['t']}", a["x"], a["y"], a["w"], a["h"]))
    for h in hijos:
        cajas.append((f"{h['ent']}.{h['t']}", h["x"], h["y"], h["w"], h["h"]))
    malos = []
    for i in range(len(cajas)):
        for j in range(i + 1, len(cajas)):
            a, b = cajas[i], cajas[j]
            if abs(a[1] - b[1]) < (a[3] + b[3]) / 2 + 6 and abs(a[2] - b[2]) < (a[4] + b[4]) / 2 + 6:
                malos.append((a[0], b[0]))
    return malos


# ---------------------------------------------------------------------------
# PNG
# ---------------------------------------------------------------------------
SECTORES = {
    "parte1_territorio": dict(
        titulo="Parte 1 · Territorio: región, centro astronómico y zonas de observación",
        nodos=["REGION", "r_alb_rc", "CENTRO", "r_cont", "ZONA"], ctx=[]),
    "parte2_observaciones_fenomenos": dict(
        titulo="Parte 2 · Observaciones y fenómenos astronómicos (especialización parcial y disjunta)",
        nodos=["ZONA", "r_reg", "OBSERV", "r_corr_f", "FENOM", "d_f", "SOLAR", "LUNAR", "ESPACIO"], ctx=["ZONA"]),
    "parte3_actividades_reservas": dict(
        titulo="Parte 3 · Actividades, reservas y evaluaciones",
        nodos=["ZONA", "r_alb_za", "ACTIV", "r_corr_a", "RESERVA", "r_orig", "EVAL", "r_real", "VISIT"], ctx=["ZONA", "VISIT"]),
    "parte4_personal_usuarios": dict(
        titulo="Parte 4 · Personas (especialización total), personal, cuentas y roles",
        nodos=["CENTRO", "r_pert", "TRAB", "r_guia", "ACTIV", "d_p", "PERSONA", "VISIT",
               "r_posee", "CUENTA", "r_asig", "ROL"], ctx=["CENTRO", "ACTIV"]),
}


def dibujar_png(attrs, hijos, ruta, solo=None, contexto=(), titulo=None, leyenda=True):
    solo = set(solo) if solo else set(NODES)
    contexto = set(contexto)
    ents_con_attr = {e for e in solo if e in ATTRS and e not in contexto}
    A = {k: a for k, a in attrs.items() if k[0] in ents_con_attr}
    Hh = [h for h in hijos if h["ent"] in ents_con_attr]
    xs = [NODES[n]["x"] for n in solo] + [a["x"] for a in A.values()] + [h["x"] for h in Hh]
    ys = [NODES[n]["y"] for n in solo] + [a["y"] for a in A.values()] + [h["y"] for h in Hh]
    x0, x1, y0, y1 = min(xs) - 230, max(xs) + 230, min(ys) - 200, max(ys) + (300 if leyenda else 150)
    anchoI = max(12.0, (x1 - x0) / 100)
    fig = plt.figure(figsize=(anchoI, (y1 - y0) / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis("off")
    ax.text(x0 + 40, y0 + 55, titulo or "MERE definitivo - Caso 2: Sistema Integral de Gestión de Centros de Turismo Astronómico",
            fontsize=26 if not titulo else 22, weight="bold", va="center")
    ax.text(x0 + 40, y0 + 108, "TDFI103 Fase 2 · Notación Chen/EER · cardinalidades (mín,máx) = participación de la entidad vecina",
            fontsize=15, color="#444", va="center")

    def linea(p, q, doble=False, z=1):
        if doble:
            dx, dy = q[0] - p[0], q[1] - p[1]
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L * 4, dx / L * 4
            for s_ in (1, -1):
                ax.plot([p[0] + s_ * nx, q[0] + s_ * nx], [p[1] + s_ * ny, q[1] + s_ * ny], color="#333", lw=1.4, zorder=z)
        else:
            ax.plot([p[0], q[0]], [p[1], q[1]], color="#333", lw=1.4, zorder=z)

    for (ent, i), a in A.items():
        nd = NODES[ent]
        p = borde(nd, (a["x"], a["y"])); q = borde(a, (nd["x"], nd["y"]))
        ax.plot([p[0], q[0]], [p[1], q[1]], color="#555", lw=1.0, zorder=1)
    for h in Hh:
        pa = attrs[h["padre"]]
        p = borde(pa, (h["x"], h["y"])); q = borde(h, (pa["x"], pa["y"]))
        ax.plot([p[0], q[0]], [p[1], q[1]], color="#555", lw=1.0, zorder=1)

    for e, r, card, est in EDGES:
        if e not in solo or r not in solo:
            continue
        ne, nr = NODES[e], NODES[r]
        p = borde(ne, (nr["x"], nr["y"])); q = borde(nr, (ne["x"], ne["y"]))
        linea(p, q, doble=(est == "total"))
        t = 0.20
        lx, ly = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1
        ax.text(lx - dy / L * 20, ly + dx / L * 20, card, fontsize=17, weight="bold", color="#8a1c1c",
                ha="center", va="center", zorder=6, bbox=dict(fc="white", ec="none", pad=1.2))
    for sup, d, subs, total in ISA:
        if d not in solo:
            continue
        if sup in solo:
            p = borde(NODES[sup], (NODES[d]["x"], NODES[d]["y"])); q = borde(NODES[d], (NODES[sup]["x"], NODES[sup]["y"]))
            linea(p, q, doble=total)
        for s_ in subs:
            if s_ in solo:
                p = borde(NODES[d], (NODES[s_]["x"], NODES[s_]["y"])); q = borde(NODES[s_], (NODES[d]["x"], NODES[d]["y"]))
                linea(p, q)

    for n in solo:
        nd = NODES[n]
        k, w, h, x, y = nd["k"], nd["w"], nd["h"], nd["x"], nd["y"]
        fc, ec = COLOR[k]
        if n in contexto:
            fc, ec = "#eeeeee", "#999999"
        if k in ("E", "W"):
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=fc, ec=ec, lw=2, zorder=3))
            if k == "W":
                ax.add_patch(Rectangle((x - w / 2 + 6, y - h / 2 + 6), w - 12, h - 12, fc="none", ec=ec, lw=2, zorder=3))
            ax.text(x, y, nd["t"], ha="center", va="center", fontsize=FONT + 1, weight="bold", zorder=4,
                    color="#777" if n in contexto else "black")
        elif k in ("R", "I"):
            pts = [(x, y - h / 2), (x + w / 2, y), (x, y + h / 2), (x - w / 2, y)]
            ax.add_patch(Polygon(pts, fc=fc, ec=ec, lw=2, zorder=3))
            if k == "I":
                pts2 = [(x, y - h / 2 + 8), (x + w / 2 - 14, y), (x, y + h / 2 - 8), (x - w / 2 + 14, y)]
                ax.add_patch(Polygon(pts2, fc="none", ec=ec, lw=2, zorder=3))
            ax.text(x, y, nd["t"], ha="center", va="center", fontsize=FONT - 1.5, zorder=4)
        else:
            ax.add_patch(Ellipse((x, y), w, h, fc=fc, ec=ec, lw=2, zorder=3))
            ax.text(x, y, "d", ha="center", va="center", fontsize=FONT, weight="bold", zorder=4)

    def dib_attr(a):
        f = a["f"]
        fc = "#dae8fc" if f in ("pk", "partial") else "white"
        ax.add_patch(Ellipse((a["x"], a["y"]), a["w"], a["h"], fc=fc, ec="#333", lw=1.4, zorder=3,
                             ls="--" if f == "partial" else "-"))
        ax.text(a["x"], a["y"], a["t"], ha="center", va="center", fontsize=FONT - 3.2, zorder=4,
                weight="bold" if f in ("pk", "partial") else "normal")
        if f in ("pk", "partial"):
            tw = a["w"] - 52
            ax.plot([a["x"] - tw / 2, a["x"] + tw / 2], [a["y"] + 10, a["y"] + 10],
                    color="#111", lw=1.2, ls="-" if f == "pk" else (0, (3, 2)), zorder=5)
    for a in A.values():
        dib_attr(a)
    for h in Hh:
        dib_attr(h)

    if leyenda:
        lx, ly = x0 + 60, y1 - 130
        ancho = min(1900, (x1 - x0) - 120)
        ax.add_patch(Rectangle((lx - 20, ly - 62), ancho, 175, fc="#fafafa", ec="#999", lw=1, zorder=1))
        ax.text(lx, ly - 36, "Leyenda", fontsize=14, weight="bold", va="center")
        ax.text(lx, ly + 2, "Subrayado en negrita = identificador (PK) · discontinuo = clave parcial · gris = entidad de contexto.",
                fontsize=12, va="center")
        ax.text(lx, ly + 34, "Rectángulo/rombo doble = entidad débil / relación identificadora · línea doble = participación total.",
                fontsize=12, va="center")
        ax.text(lx, ly + 66, "d = especialización disjunta (FENOMENO parcial: admite 'no clasificado'; PERSONA total).",
                fontsize=12, va="center")
    fig.savefig(ruta, dpi=100, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# DRAWIO
# ---------------------------------------------------------------------------
def esc(s):
    return html.escape(s, quote=True)


def a_drawio(attrs, hijos, ruta):
    celdas, ids = [], {}
    nid = [2]

    def nuevo():
        nid[0] += 1
        return f"c{nid[0]}"

    def vertice(x, y, w, h, texto, estilo):
        i = nuevo()
        celdas.append(f'<mxCell id="{i}" value="{esc(texto)}" style="{estilo}" vertex="1" parent="1">'
                      f'<mxGeometry x="{x - w / 2:.0f}" y="{y - h / 2:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>')
        return i

    for n, nd in NODES.items():
        k = nd["k"]
        fc, ec = COLOR[k]
        base = f"whiteSpace=wrap;html=1;fillColor={fc};strokeColor={ec};"
        if k == "E":
            est = "rounded=0;" + base + "fontStyle=1;fontSize=13;"
        elif k == "W":
            est = "shape=ext;double=1;rounded=0;" + base + "fontStyle=1;fontSize=13;"
        elif k == "R":
            est = "rhombus;" + base + "fontSize=12;"
        elif k == "I":
            est = "rhombus;double=1;" + base + "fontSize=12;"
        else:
            est = "ellipse;" + base + "fontStyle=1;fontSize=14;"
        ids[n] = vertice(nd["x"], nd["y"], nd["w"], nd["h"], nd["t"], est)

    def estilo_attr(f):
        if f == "pk":
            return "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=5;fontSize=11;"
        if f == "partial":
            return "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=5;dashed=1;fontSize=11;"
        return "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#333333;fontSize=11;"

    aid = {}
    for (ent, i), a in attrs.items():
        aid[(ent, i)] = vertice(a["x"], a["y"], a["w"], a["h"], a["t"], estilo_attr(a["f"]))
    hid = []
    for h in hijos:
        hid.append((vertice(h["x"], h["y"], h["w"], h["h"], h["t"], estilo_attr("")), h))

    def arista(src, tgt, estilo="endArrow=none;html=1;strokeColor=#333333;", etiqueta=None):
        i = nuevo()
        celdas.append(f'<mxCell id="{i}" style="{estilo}" edge="1" parent="1" source="{src}" target="{tgt}">'
                      f'<mxGeometry relative="1" as="geometry"/></mxCell>')
        if etiqueta:
            j = nuevo()
            celdas.append(f'<mxCell id="{j}" value="{esc(etiqueta)}" style="edgeLabel;html=1;align=center;'
                          f'verticalAlign=middle;resizable=0;points=[];fontStyle=1;fontColor=#8a1c1c;fontSize=12;" '
                          f'vertex="1" connectable="0" parent="{i}"><mxGeometry x="-0.55" y="-12" relative="1" as="geometry">'
                          f'<mxPoint as="offset"/></mxGeometry></mxCell>')
        return i

    for (ent, i), a in attrs.items():
        arista(ids[ent], aid[(ent, i)], "endArrow=none;html=1;strokeColor=#555555;")
    for hv, h in hid:
        arista(aid[h["padre"]], hv, "endArrow=none;html=1;strokeColor=#555555;")
    for e, r, card, est in EDGES:
        estilo = "endArrow=none;html=1;strokeColor=#333333;" + ("shape=link;" if est == "total" else "")
        arista(ids[e], ids[r], estilo, card)
    for sup, d, subs, total in ISA:
        arista(ids[sup], ids[d], "endArrow=none;html=1;strokeColor=#333333;" + ("shape=link;" if total else ""))
        for s in subs:
            arista(ids[d], ids[s])

    xs = [nd["x"] for nd in NODES.values()]
    ys = [nd["y"] for nd in NODES.values()]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<mxfile host="app.diagrams.net" version="24.0.0" type="device">\n'
           '  <diagram id="MERE_Caso2_v2" name="MERE definitivo Caso 2">\n'
           f'    <mxGraphModel dx="3000" dy="1800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(max(xs)) + 1000}" pageHeight="{int(max(ys)) + 800}" math="0" shadow="0">\n'
           '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n        '
           + "\n        ".join(celdas) +
           '\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n')
    Path(ruta).write_text(xml, encoding="utf-8")


OVERRIDES = {}

if __name__ == "__main__":
    attrs, hijos = preparar(OVERRIDES)
    malos = colisiones(attrs, hijos)
    print("colisiones:", len(malos))
    for m in malos:
        print("  ", m)
    dibujar_png(attrs, hijos, OUT / "MERE_Caso2_corregido.png")
    for nombre, sec in SECTORES.items():
        dibujar_png(attrs, hijos, OUT / f"MERE_{nombre}.png", solo=sec["nodos"], contexto=sec["ctx"], titulo=sec["titulo"])
    a_drawio(attrs, hijos, OUT / "MERE_Caso2_corregido.drawio")
    print("OK")
