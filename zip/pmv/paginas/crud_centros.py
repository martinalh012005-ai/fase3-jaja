"""Funcionalidad 2a - CRUD de la tabla maestra CENTRO_ASTRONOMICO (con desactivación lógica)."""
from datetime import date

import streamlit as st

import auth
from db import consulta, intentar

ESTADOS = ["OPERATIVO", "MANTENIMIENTO", "CERRADO"]
CERTIFICACIONES = ["BASICA", "INTERMEDIA", "AVANZADA", "EXCELENCIA"]


def _form(prefijo, regiones, datos=None):
    """Formulario común de creación/modificación. Devuelve (enviado, valores)."""
    d = datos or {}
    mapa_r = dict(zip(regiones["id_region"], regiones["nombre_oficial"]))
    ids = list(mapa_r)
    c1, c2 = st.columns(2)
    with c1:
        nombre = st.text_input("Nombre", value=d.get("nombre", ""), max_chars=100, key=f"{prefijo}_nombre")
        region = st.selectbox("Región", ids, format_func=mapa_r.get,
                              index=ids.index(d["id_region"]) if d.get("id_region") in ids else 0, key=f"{prefijo}_region")
        inaug = st.date_input("Fecha de inauguración", value=d.get("fecha_inauguracion", date(2020, 1, 1)),
                              min_value=date(1900, 1, 1), max_value=date(2100, 12, 31), key=f"{prefijo}_inaug")
        altitud = st.number_input("Altitud (m s. n. m.)", min_value=0, max_value=9000, value=int(d.get("altitud", 1000)), key=f"{prefijo}_alt")
        cap = st.number_input("Capacidad máxima diaria", min_value=1, max_value=100000, value=int(d.get("capacidad_max_diaria", 100)), key=f"{prefijo}_cap")
    with c2:
        lat = st.number_input("Latitud", min_value=-90.0, max_value=90.0, value=float(d.get("latitud", -30.0)), format="%.6f", key=f"{prefijo}_lat")
        lon = st.number_input("Longitud", min_value=-180.0, max_value=180.0, value=float(d.get("longitud", -70.5)), format="%.6f", key=f"{prefijo}_lon")
        pres = st.number_input("Presupuesto anual (CLP)", min_value=0.0, value=float(d.get("presupuesto_anual", 50_000_000)), step=1_000_000.0, key=f"{prefijo}_pres")
        estado = st.selectbox("Estado operativo", ESTADOS, index=ESTADOS.index(d.get("estado_operativo", "OPERATIVO")), key=f"{prefijo}_estado")
        cert = st.selectbox("Nivel de certificación", CERTIFICACIONES,
                            index=CERTIFICACIONES.index(d.get("nivel_certificacion", "BASICA")), key=f"{prefijo}_cert")
    valores = dict(nombre=nombre.strip(), id_region=int(region), fecha_inauguracion=inaug, altitud=int(altitud),
                   latitud=lat, longitud=lon, capacidad_max_diaria=int(cap), presupuesto_anual=pres,
                   estado_operativo=estado, nivel_certificacion=cert)
    return valores


def _valido(v):
    if len(v["nombre"]) < 3:
        st.error("El nombre debe tener al menos 3 caracteres.")
        return False
    return True


def render():
    auth.requiere("crud_centros")
    st.header("🏛️ Centros astronómicos")
    regiones = consulta("SELECT id_region, nombre_oficial FROM region ORDER BY nombre_oficial")
    t_consulta, t_crear, t_mod, t_estado = st.tabs(["Consultar", "Crear", "Modificar", "Desactivar / eliminar"])

    with t_consulta:
        c1, c2 = st.columns(2)
        solo_activos = c1.checkbox("Solo centros activos", value=False)
        estado = c2.multiselect("Estado operativo", ESTADOS, default=ESTADOS)
        df = consulta("""SELECT c.id_centro, c.nombre, r.nombre_oficial AS region, c.estado_operativo, c.nivel_certificacion,
                                c.altitud, c.capacidad_max_diaria, c.presupuesto_anual, c.activo,
                                (SELECT COUNT(*) FROM zona_observacion z WHERE z.id_centro = c.id_centro) AS zonas
                         FROM centro_astronomico c JOIN region r ON r.id_region = c.id_region
                         ORDER BY c.nombre""")
        if solo_activos:
            df = df[df["activo"] == 1]
        df = df[df["estado_operativo"].isin(estado)]
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption(f"{len(df)} centros")

    with t_crear:
        with st.form("crear_centro"):
            v = _form("nuevo", regiones)
            if st.form_submit_button("Crear centro", type="primary") and _valido(v):
                intentar([("""INSERT INTO centro_astronomico (id_region, nombre, fecha_inauguracion, altitud, latitud, longitud,
                                     capacidad_max_diaria, presupuesto_anual, estado_operativo, nivel_certificacion, activo)
                              VALUES (:id_region, :nombre, :fecha_inauguracion, :altitud, :latitud, :longitud,
                                      :capacidad_max_diaria, :presupuesto_anual, :estado_operativo, :nivel_certificacion, 1)""", v)],
                         ok="Centro creado.")

    centros = consulta("SELECT * FROM centro_astronomico ORDER BY nombre")
    nombres = dict(zip(centros["id_centro"], centros["nombre"]))

    with t_mod:
        if centros.empty:
            st.info("No hay centros.")
        else:
            sel = st.selectbox("Centro a modificar", list(nombres), format_func=nombres.get, key="mod_sel")
            fila = centros[centros["id_centro"] == sel].iloc[0].to_dict()
            with st.form(f"mod_centro_{sel}"):
                v = _form(f"mod{sel}", regiones, fila)
                if st.form_submit_button("Guardar cambios", type="primary") and _valido(v):
                    v["id"] = int(sel)
                    intentar([("""UPDATE centro_astronomico SET id_region=:id_region, nombre=:nombre, fecha_inauguracion=:fecha_inauguracion,
                                  altitud=:altitud, latitud=:latitud, longitud=:longitud, capacidad_max_diaria=:capacidad_max_diaria,
                                  presupuesto_anual=:presupuesto_anual, estado_operativo=:estado_operativo,
                                  nivel_certificacion=:nivel_certificacion WHERE id_centro=:id""", v)],
                             ok="Centro actualizado.")

    with t_estado:
        if centros.empty:
            st.info("No hay centros.")
        else:
            sel = st.selectbox("Centro", list(nombres), format_func=nombres.get, key="est_sel")
            activo = int(centros[centros["id_centro"] == sel].iloc[0]["activo"])
            st.write("Estado actual: " + ("🟢 **activo**" if activo else "⚪ **desactivado**"))
            if st.button("Desactivar" if activo else "Reactivar", key="btn_toggle_centro"):
                if intentar([("UPDATE centro_astronomico SET activo = :a WHERE id_centro = :i", {"a": 0 if activo else 1, "i": int(sel)})],
                            ok="Estado actualizado."):
                    st.rerun()
            st.divider()
            st.markdown("**Eliminación física** (solo posible si el centro no tiene datos relacionados; "
                        "en caso contrario use la desactivación lógica).")
            ok = st.checkbox("Confirmo que deseo eliminar definitivamente este centro", key="conf_del_centro")
            if st.button("Eliminar definitivamente", disabled=not ok, key="btn_del_centro"):
                if intentar([("DELETE FROM centro_astronomico WHERE id_centro = :i", {"i": int(sel)})], ok="Centro eliminado."):
                    st.rerun()
