"""Funcionalidad 4 - Dashboard: 3 preguntas de la Fase 1 + 1 pregunta propuesta por el equipo.
Las consultas son propias del PMV (no reutilizan las vistas/procedimientos de la evidencia SQL)."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import auth
from db import consulta_cache

COLORES = {"SOLAR": "#f5a623", "LUNAR": "#8fa3bf", "ESPACIO_PROFUNDO": "#6c4fd6", "NO_CLASIFICADO": "#b0b0b0"}


def _centros():
    return consulta_cache("SELECT id_centro, nombre FROM centro_astronomico ORDER BY nombre")


def _rango_fechas():
    r = consulta_cache("SELECT MIN(fecha) AS a, MAX(fecha) AS b FROM actividad_observacion WHERE estado = 'REALIZADA'")
    return pd.to_datetime(r.loc[0, "a"]).date(), pd.to_datetime(r.loc[0, "b"]).date()


def _filtro_centros(clave):
    c = _centros()
    nombres = dict(zip(c["id_centro"], c["nombre"]))
    sel = st.multiselect("Centros", list(nombres), format_func=nombres.get, key=f"{clave}_centros",
                         placeholder="Todos los centros")
    return [int(i) for i in (sel or nombres)], nombres


def _filtro_periodo(clave):
    a, b = _rango_fechas()
    rango = st.date_input("Período", value=(a, b), min_value=a, max_value=b, key=f"{clave}_periodo")
    if isinstance(rango, tuple) and len(rango) == 2:
        return rango
    return a, b


def _q1():
    st.subheader("1 · ¿Qué zonas de observación reciben más visitantes?")
    st.caption("Visitantes que asistieron efectivamente a actividades realizadas, por zona. Filtros: centro y período.")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        centros, _ = _filtro_centros("q1")
    with c2:
        ini, fin = _filtro_periodo("q1")
    with c3:
        top = st.slider("Top zonas", 5, 30, 12, key="q1_top")
    df = consulta_cache(
        """SELECT c.nombre AS centro, z.nombre AS zona, COUNT(DISTINCT a.id_actividad) AS actividades,
                  SUM(r.asistencia_efectiva) AS visitantes
           FROM reserva r
           JOIN actividad_observacion a ON a.id_actividad = r.id_actividad
           JOIN zona_observacion z      ON z.id_zona = a.id_zona
           JOIN centro_astronomico c    ON c.id_centro = z.id_centro
           WHERE r.estado = 'CONFIRMADA' AND a.estado = 'REALIZADA'
             AND a.fecha BETWEEN :ini AND :fin AND c.id_centro IN :centros
           GROUP BY c.id_centro, c.nombre, z.id_zona, z.nombre
           HAVING visitantes > 0
           ORDER BY visitantes DESC LIMIT :top""",
        {"ini": ini, "fin": fin, "centros": centros, "top": int(top)}, listas=("centros",))
    if df.empty:
        st.info("Sin datos para los filtros elegidos.")
        return
    df["zona_centro"] = df["zona"] + " · " + df["centro"]
    fig = px.bar(df.sort_values("visitantes"), x="visitantes", y="zona_centro", color="centro", orientation="h",
                 labels={"visitantes": "Visitantes asistentes", "zona_centro": ""}, text="visitantes")
    fig.update_layout(height=max(380, 34 * len(df)), legend_title_text="Centro", margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    with st.expander("Ver tabla"):
        st.dataframe(df.drop(columns="zona_centro"), width="stretch", hide_index=True)


def _q2():
    st.subheader("2 · ¿Cómo se distribuyen los fenómenos entre solares, lunares y de espacio profundo?")
    st.caption("Composición por clasificación según los registros de observación. Filtros: centro y zona.")
    c1, c2 = st.columns(2)
    with c1:
        centros, _ = _filtro_centros("q2")
    z = consulta_cache("SELECT id_zona, nombre FROM zona_observacion WHERE id_centro IN :c ORDER BY nombre",
                       {"c": centros}, listas=("c",))
    nombres_z = dict(zip(z["id_zona"], z["nombre"]))
    with c2:
        zsel = st.multiselect("Zonas", list(nombres_z), format_func=nombres_z.get, key="q2_zonas", placeholder="Todas las zonas")
    zonas = [int(i) for i in (zsel or nombres_z)] or [0]
    c3, c4 = st.columns(2)
    metrica = c3.radio("Medir por", ["Registros de observación", "Fenómenos distintos"], horizontal=True, key="q2_m")
    con_nc = c4.checkbox("Incluir 'no clasificados'", value=False, key="q2_nc")
    df = consulta_cache(
        """SELECT f.tipo_clasificacion AS clasificacion, COUNT(DISTINCT f.id_fenomeno) AS fenomenos,
                  COUNT(o.id_observacion) AS registros
           FROM observacion o JOIN fenomeno_astronomico f ON f.id_fenomeno = o.id_fenomeno
           WHERE o.id_zona IN :z GROUP BY f.tipo_clasificacion""", {"z": zonas}, listas=("z",))
    if not con_nc:
        df = df[df["clasificacion"] != "NO_CLASIFICADO"]
    if df.empty:
        st.info("Sin datos para los filtros elegidos.")
        return
    col = "registros" if metrica.startswith("Registros") else "fenomenos"
    fig = px.pie(df, names="clasificacion", values=col, hole=0.45, color="clasificacion", color_discrete_map=COLORES)
    fig.update_traces(textinfo="percent+value")
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
    a, b = st.columns([3, 2])
    a.plotly_chart(fig, width="stretch")
    df["proporcion_%"] = (100 * df[col] / df[col].sum()).round(1)
    b.dataframe(df, width="stretch", hide_index=True)


def _q3():
    st.subheader("3 · ¿Existe relación entre los asistentes a una actividad y su evaluación promedio?")
    st.caption("Cada punto es una actividad realizada. Tamaño = cantidad de evaluaciones. Filtros: centro y zona.")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        centros, _ = _filtro_centros("q3")
    z = consulta_cache("SELECT id_zona, nombre FROM zona_observacion WHERE id_centro IN :c ORDER BY nombre",
                       {"c": centros}, listas=("c",))
    nombres_z = dict(zip(z["id_zona"], z["nombre"]))
    with c2:
        zsel = st.multiselect("Zonas", list(nombres_z), format_func=nombres_z.get, key="q3_zonas", placeholder="Todas las zonas")
    with c3:
        minev = st.slider("Mín. evaluaciones", 1, 10, 2, key="q3_min")
    zonas = [int(i) for i in (zsel or nombres_z)] or [0]
    df = consulta_cache(
        """SELECT a.cod_actividad, a.nombre AS actividad, c.nombre AS centro, z.nombre AS zona,
                  SUM(r.asistencia_efectiva) AS asistentes, COUNT(e.id_evaluacion) AS evaluaciones,
                  ROUND(AVG(e.calificacion), 2) AS evaluacion_promedio
           FROM actividad_observacion a
           JOIN zona_observacion z   ON z.id_zona = a.id_zona
           JOIN centro_astronomico c ON c.id_centro = z.id_centro
           JOIN reserva r            ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
           JOIN evaluacion e         ON e.id_reserva = r.id_reserva
           WHERE a.estado = 'REALIZADA' AND z.id_zona IN :z
           GROUP BY a.id_actividad, a.cod_actividad, a.nombre, c.nombre, z.nombre
           HAVING COUNT(e.id_evaluacion) >= :m""", {"z": zonas, "m": int(minev)}, listas=("z",))
    if len(df) < 2:
        st.info("No hay suficientes actividades para los filtros elegidos.")
        return
    df["asistentes"] = df["asistentes"].astype(float)
    df["evaluacion_promedio"] = df["evaluacion_promedio"].astype(float)
    fig = px.scatter(df, x="asistentes", y="evaluacion_promedio", color="centro", size="evaluaciones",
                     hover_data=["cod_actividad", "actividad", "zona"],
                     labels={"asistentes": "Asistentes", "evaluacion_promedio": "Evaluación promedio (1-5)"})
    m, n = np.polyfit(df["asistentes"], df["evaluacion_promedio"], 1)
    xs = np.linspace(df["asistentes"].min(), df["asistentes"].max(), 20)
    fig.add_trace(go.Scatter(x=xs, y=m * xs + n, mode="lines", name="Tendencia lineal", line=dict(color="#444", dash="dash")))
    fig.update_yaxes(range=[1, 5.2])
    fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    r = df["asistentes"].corr(df["evaluacion_promedio"])
    sentido = "negativa" if r < -0.1 else "positiva" if r > 0.1 else "prácticamente nula"
    st.info(f"Correlación de Pearson: **{r:.2f}** ({sentido}) sobre {len(df)} actividades. "
            f"Pendiente: {m:+.3f} puntos de evaluación por asistente adicional.")
    st.dataframe(df.sort_values("asistentes", ascending=False), width="stretch", hide_index=True)


def _q4():
    st.subheader("4 · (Propuesta del equipo) ¿Qué modalidades generan más ingresos y qué tan ocupadas están mes a mes?")
    with st.expander("Justificación y decisión de negocio que apoya", expanded=False):
        st.markdown(
            "**Pregunta nueva:** no repite las tres anteriores (que miran visitantes por zona, tipos de fenómeno y satisfacción); "
            "esta mira la **rentabilidad y el uso de la oferta**.  \n"
            "**Definiciones:** ingreso = valor de la actividad × asistentes efectivos; ocupación = asistentes / capacidad de la actividad.  \n"
            "**Decisión que apoya:** qué modalidades ampliar (más fechas o cupos), cuáles ajustar de precio o reprogramar, "
            "y en qué meses reforzar al personal y los guías. Una modalidad con alta ocupación y alto ingreso es candidata a crecer; "
            "una con baja ocupación en ciertos meses es candidata a promociones o a reducir oferta.")
    c1, c2 = st.columns(2)
    with c1:
        centros, _ = _filtro_centros("q4")
    with c2:
        ini, fin = _filtro_periodo("q4")
    mods = consulta_cache("SELECT DISTINCT modalidad FROM actividad_observacion ORDER BY modalidad")["modalidad"].tolist()
    msel = st.multiselect("Modalidades", mods, default=mods, key="q4_mod")
    df = consulta_cache(
        """SELECT mes, modalidad, COUNT(*) AS actividades, SUM(asistentes) AS asistentes,
                  SUM(capacidad) AS capacidad, SUM(ingresos) AS ingresos
           FROM (SELECT a.id_actividad, DATE_FORMAT(a.fecha, '%Y-%m') AS mes, a.modalidad, a.capacidad,
                        COALESCE(SUM(r.asistencia_efectiva), 0) AS asistentes,
                        COALESCE(SUM(r.asistencia_efectiva), 0) * a.valor AS ingresos
                 FROM actividad_observacion a
                 JOIN zona_observacion z ON z.id_zona = a.id_zona
                 LEFT JOIN reserva r ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
                 WHERE a.estado = 'REALIZADA' AND a.fecha BETWEEN :ini AND :fin
                   AND z.id_centro IN :centros AND a.modalidad IN :mods
                 GROUP BY a.id_actividad, a.fecha, a.modalidad, a.capacidad, a.valor) t
           GROUP BY mes, modalidad ORDER BY mes, modalidad""",
        {"ini": ini, "fin": fin, "centros": centros, "mods": msel or mods}, listas=("centros", "mods"))
    if df.empty:
        st.info("Sin datos para los filtros elegidos.")
        return
    for c in ("asistentes", "capacidad", "ingresos"):
        df[c] = df[c].astype(float)
    df["ocupacion_%"] = (100 * df["asistentes"] / df["capacidad"]).round(1)
    a, b = st.columns(2)
    f1 = px.bar(df, x="mes", y="ingresos", color="modalidad", barmode="stack",
                labels={"ingresos": "Ingresos (CLP)", "mes": "Mes"}, title="Ingresos por mes y modalidad")
    f1.update_layout(height=420, margin=dict(l=0, r=0, t=40, b=0))
    a.plotly_chart(f1, width="stretch")
    res = df.groupby("modalidad").agg(actividades=("actividades", "sum"), asistentes=("asistentes", "sum"),
                                       capacidad=("capacidad", "sum"), ingresos=("ingresos", "sum")).reset_index()
    res["ocupacion_%"] = (100 * res["asistentes"] / res["capacidad"]).round(1)
    f2 = px.bar(res.sort_values("ocupacion_%"), x="ocupacion_%", y="modalidad", orientation="h", color="ingresos",
                color_continuous_scale="Viridis", text="ocupacion_%", title="Ocupación por modalidad (color = ingresos)",
                labels={"ocupacion_%": "Ocupación (%)", "ingresos": "Ingresos"})
    f2.update_layout(height=420, margin=dict(l=0, r=0, t=40, b=0))
    b.plotly_chart(f2, width="stretch")
    st.dataframe(res.sort_values("ingresos", ascending=False), width="stretch", hide_index=True)


def render():
    auth.requiere("dashboard")
    st.header("📊 Dashboard")
    t1, t2, t3, t4 = st.tabs(["1 · Zonas con más visitantes", "2 · Tipos de fenómenos",
                              "3 · Asistentes vs. evaluación", "4 · Ingresos y ocupación (propuesta)"])
    with t1:
        _q1()
    with t2:
        _q2()
    with t3:
        _q3()
    with t4:
        _q4()
