"""Funcionalidad 2b - CRUD de la tabla maestra FENOMENO_ASTRONOMICO con sus subtipos
(especialización parcial y disjunta: SOLAR / LUNAR / ESPACIO_PROFUNDO / NO_CLASIFICADO)."""
from datetime import date

import pandas as pd
import streamlit as st

import auth
from db import consulta, intentar

TIPOS = ["SOLAR", "LUNAR", "ESPACIO_PROFUNDO", "NO_CLASIFICADO"]
FASES = ["Luna nueva", "Creciente", "Cuarto creciente", "Luna llena", "Menguante", "Cuarto menguante"]
TABLA_SUBTIPO = {"SOLAR": "fenomeno_solar", "LUNAR": "fenomeno_lunar", "ESPACIO_PROFUNDO": "fenomeno_espacio_profundo"}


def _campos_base(prefijo, d=None):
    d = d or {}
    nombre = st.text_input("Nombre", value=d.get("nombre", ""), max_chars=120, key=f"{prefijo}_nombre")
    desc = st.text_area("Descripción", value=d.get("descripcion", ""), max_chars=400, key=f"{prefijo}_desc")
    c1, c2, c3 = st.columns(3)
    freq = c1.text_input("Frecuencia estimada", value=d.get("frecuencia_estimada", "Anual"), max_chars=60, key=f"{prefijo}_freq")
    interes = c2.slider("Interés científico", 1, 5, int(d.get("nivel_interes_cientifico", 3)), key=f"{prefijo}_int")
    sin_fecha = c3.checkbox("Sin fecha de primera observación", value=d.get("fecha_primera_observacion") is None and bool(d), key=f"{prefijo}_sf")
    fecha = None if sin_fecha else c3.date_input("Primera observación documentada",
                                                 value=d.get("fecha_primera_observacion") or date(1900, 1, 1),
                                                 min_value=date(1000, 1, 1), max_value=date.today(), key=f"{prefijo}_fpo")
    return dict(nombre=nombre.strip(), descripcion=desc.strip(), frecuencia_estimada=freq.strip(),
                nivel_interes_cientifico=int(interes), fecha_primera_observacion=fecha)


def _campos_subtipo(tipo, prefijo, d=None):
    d = d or {}
    if tipo == "SOLAR":
        a = st.text_input("Tipo de evento (eclipse, llamarada, mancha solar…)", value=d.get("tipo_evento", ""), max_chars=40, key=f"{prefijo}_s1")
        b = st.number_input("Duración estimada (min)", min_value=1, value=int(d.get("duracion_estimada_min", 30)), key=f"{prefijo}_s2")
        c = st.slider("Nivel de intensidad", 1, 5, int(d.get("nivel_intensidad", 3)), key=f"{prefijo}_s3")
        return dict(tipo_evento=a.strip(), duracion_estimada_min=int(b), nivel_intensidad=int(c))
    if tipo == "LUNAR":
        a = st.selectbox("Fase lunar", FASES, index=FASES.index(d["fase_lunar"]) if d.get("fase_lunar") in FASES else 3, key=f"{prefijo}_l1")
        b = st.text_input("Tipo de evento (eclipse, superluna, ocultación…)", value=d.get("tipo_evento", ""), max_chars=40, key=f"{prefijo}_l2")
        c = st.slider("Visibilidad (%)", 0.0, 100.0, float(d.get("visibilidad_porcentaje", 80.0)), key=f"{prefijo}_l3")
        return dict(fase_lunar=a, tipo_evento=b.strip(), visibilidad_porcentaje=float(c))
    if tipo == "ESPACIO_PROFUNDO":
        a = st.text_input("Tipo de objeto (galaxia, nebulosa, cúmulo…)", value=d.get("tipo_objeto", ""), max_chars=40, key=f"{prefijo}_e1")
        b = st.number_input("Distancia (años luz)", min_value=0.01, value=float(d.get("distancia_anios_luz", 1000.0)), key=f"{prefijo}_e2")
        c = st.number_input("Magnitud aparente", min_value=-30.0, max_value=30.0, value=float(d.get("magnitud_aparente", 5.0)), key=f"{prefijo}_e3")
        return dict(tipo_objeto=a.strip(), distancia_anios_luz=float(b), magnitud_aparente=float(c))
    st.caption("Los fenómenos no clasificados no tienen atributos de subtipo.")
    return {}


def _valido(base, sub):
    if len(base["nombre"]) < 3:
        st.error("El nombre debe tener al menos 3 caracteres.")
        return False
    if not base["descripcion"]:
        st.error("La descripción es obligatoria.")
        return False
    if any(isinstance(v, str) and not v for v in sub.values()):
        st.error("Complete los campos del subtipo.")
        return False
    return True


def render():
    auth.requiere("crud_fenomenos")
    st.header("🌌 Fenómenos astronómicos")
    t_consulta, t_crear, t_mod, t_estado = st.tabs(["Consultar", "Crear", "Modificar", "Desactivar / eliminar"])

    with t_consulta:
        c1, c2 = st.columns(2)
        tipos = c1.multiselect("Clasificación", TIPOS, default=TIPOS)
        solo_activos = c2.checkbox("Solo activos", value=False)
        df = consulta("""SELECT f.id_fenomeno, f.nombre, f.tipo_clasificacion AS clasificacion,
                                COALESCE(s.tipo_evento, l.tipo_evento, ep.tipo_objeto) AS subtipo,
                                f.nivel_interes_cientifico AS interes, f.frecuencia_estimada, f.activo,
                                (SELECT COUNT(*) FROM observacion o WHERE o.id_fenomeno = f.id_fenomeno) AS registros
                         FROM fenomeno_astronomico f
                         LEFT JOIN fenomeno_solar s ON s.id_fenomeno = f.id_fenomeno
                         LEFT JOIN fenomeno_lunar l ON l.id_fenomeno = f.id_fenomeno
                         LEFT JOIN fenomeno_espacio_profundo ep ON ep.id_fenomeno = f.id_fenomeno
                         ORDER BY f.nombre""")
        df = df[df["clasificacion"].isin(tipos)]
        if solo_activos:
            df = df[df["activo"] == 1]
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption(f"{len(df)} fenómenos")

    with t_crear:
        tipo = st.selectbox("Clasificación del fenómeno", TIPOS, key="nuevo_tipo")
        with st.form("crear_fenomeno"):
            base = _campos_base("nf")
            sub = _campos_subtipo(tipo, "nf")
            if st.form_submit_button("Crear fenómeno", type="primary") and _valido(base, sub):
                base["tipo"] = tipo
                sentencias = [("""INSERT INTO fenomeno_astronomico (nombre, descripcion, fecha_primera_observacion, frecuencia_estimada,
                                          nivel_interes_cientifico, tipo_clasificacion, activo)
                                  VALUES (:nombre, :descripcion, :fecha_primera_observacion, :frecuencia_estimada,
                                          :nivel_interes_cientifico, :tipo, 1)""", base)]
                if tipo != "NO_CLASIFICADO":
                    cols = ", ".join(sub)
                    vals = ", ".join(f":{k}" for k in sub)
                    sentencias.append((f"INSERT INTO {TABLA_SUBTIPO[tipo]} (id_fenomeno, {cols}) VALUES (LAST_INSERT_ID(), {vals})", sub))
                intentar(sentencias, ok="Fenómeno creado.")

    todos = consulta("SELECT id_fenomeno, nombre, tipo_clasificacion, activo FROM fenomeno_astronomico ORDER BY nombre")
    nombres = {int(r.id_fenomeno): f"{r.nombre} ({r.tipo_clasificacion})" for r in todos.itertuples()}

    with t_mod:
        sel = st.selectbox("Fenómeno a modificar", list(nombres), format_func=nombres.get, key="mod_f_sel")
        base_db = consulta("SELECT * FROM fenomeno_astronomico WHERE id_fenomeno = :i", {"i": int(sel)}).iloc[0].to_dict()
        base_db = {k: (None if pd.isna(v) else v) for k, v in base_db.items()}
        tipo = base_db["tipo_clasificacion"]
        sub_db = {}
        if tipo in TABLA_SUBTIPO:
            sub_db = consulta(f"SELECT * FROM {TABLA_SUBTIPO[tipo]} WHERE id_fenomeno = :i", {"i": int(sel)}).iloc[0].to_dict()
        st.caption(f"Clasificación: **{tipo}** (no se puede cambiar; cree un fenómeno nuevo si corresponde otra clasificación).")
        with st.form(f"mod_fenomeno_{sel}"):
            base = _campos_base(f"mf{sel}", base_db)
            sub = _campos_subtipo(tipo, f"mf{sel}", sub_db)
            if st.form_submit_button("Guardar cambios", type="primary") and _valido(base, sub):
                base["i"] = int(sel)
                sentencias = [("""UPDATE fenomeno_astronomico SET nombre=:nombre, descripcion=:descripcion,
                                  fecha_primera_observacion=:fecha_primera_observacion, frecuencia_estimada=:frecuencia_estimada,
                                  nivel_interes_cientifico=:nivel_interes_cientifico WHERE id_fenomeno=:i""", base)]
                if sub:
                    sets = ", ".join(f"{k}=:{k}" for k in sub)
                    sentencias.append((f"UPDATE {TABLA_SUBTIPO[tipo]} SET {sets} WHERE id_fenomeno=:i", {**sub, "i": int(sel)}))
                intentar(sentencias, ok="Fenómeno actualizado.")

    with t_estado:
        sel = st.selectbox("Fenómeno", list(nombres), format_func=nombres.get, key="est_f_sel")
        activo = int(todos[todos["id_fenomeno"] == sel].iloc[0]["activo"])
        st.write("Estado actual: " + ("🟢 **activo**" if activo else "⚪ **desactivado**"))
        if st.button("Desactivar" if activo else "Reactivar", key="btn_toggle_fen"):
            if intentar([("UPDATE fenomeno_astronomico SET activo = :a WHERE id_fenomeno = :i", {"a": 0 if activo else 1, "i": int(sel)})],
                        ok="Estado actualizado."):
                st.rerun()
        st.divider()
        st.markdown("**Eliminación física** (solo si no tiene registros de observación; si los tiene, el motor la rechaza y debe desactivarlo).")
        ok = st.checkbox("Confirmo que deseo eliminar definitivamente este fenómeno", key="conf_del_fen")
        if st.button("Eliminar definitivamente", disabled=not ok, key="btn_del_fen"):
            tipo_sel = todos[todos["id_fenomeno"] == sel].iloc[0]["tipo_clasificacion"]
            sentencias = []
            if tipo_sel in TABLA_SUBTIPO:
                sentencias.append((f"DELETE FROM {TABLA_SUBTIPO[tipo_sel]} WHERE id_fenomeno = :i", {"i": int(sel)}))
            sentencias.append(("DELETE FROM fenomeno_astronomico WHERE id_fenomeno = :i", {"i": int(sel)}))
            if intentar(sentencias, ok="Fenómeno eliminado."):
                st.rerun()
