"""Funcionalidad 1 - Formulario transaccional: registrar la reserva de un visitante en una actividad."""
import streamlit as st

import auth
from db import consulta, intentar


def render():
    auth.requiere("reservas")
    st.header("📝 Registrar reserva")
    st.caption("Seleccione centro, zona, actividad y visitante existentes. El motor valida cupos, duplicados y estado de la actividad.")

    centros = consulta("""SELECT id_centro, nombre FROM centro_astronomico
                          WHERE activo = 1 AND estado_operativo = 'OPERATIVO' ORDER BY nombre""")
    if centros.empty:
        st.warning("No hay centros operativos.")
        return
    mapa_c = dict(zip(centros["id_centro"], centros["nombre"]))
    id_centro = st.selectbox("Centro astronómico", list(mapa_c), format_func=mapa_c.get)

    zonas = consulta("SELECT id_zona, nombre FROM zona_observacion WHERE id_centro = :c ORDER BY nombre", {"c": int(id_centro)})
    mapa_z = {0: "Todas las zonas", **dict(zip(zonas["id_zona"], zonas["nombre"]))}
    id_zona = st.selectbox("Zona de observación", list(mapa_z), format_func=mapa_z.get)

    acts = consulta(
        """SELECT a.id_actividad, a.cod_actividad, a.nombre, a.fecha, a.horario, a.valor, a.capacidad,
                  z.nombre AS zona, a.capacidad - COUNT(r.id_reserva) AS cupos
           FROM actividad_observacion a
           JOIN zona_observacion z ON z.id_zona = a.id_zona
           LEFT JOIN reserva r ON r.id_actividad = a.id_actividad AND r.estado = 'CONFIRMADA'
           WHERE z.id_centro = :c AND a.estado = 'PROGRAMADA' AND (:z = 0 OR z.id_zona = :z)
           GROUP BY a.id_actividad, a.cod_actividad, a.nombre, a.fecha, a.horario, a.valor, a.capacidad, z.nombre
           HAVING cupos > 0
           ORDER BY a.fecha, a.horario""", {"c": int(id_centro), "z": int(id_zona)})
    if acts.empty:
        st.info("No hay actividades programadas con cupos disponibles para esa selección.")
        return
    etiqueta_a = {int(r.id_actividad): f"{r.cod_actividad} · {r.nombre} · {r.fecha} {str(r.horario)[-8:-3]} · {r.zona} · ${r.valor:,.0f} · {int(r.cupos)} cupos"
                  for r in acts.itertuples()}
    visit = consulta("""SELECT v.id_persona, CONCAT(p.nombre_pila, ' ', p.ap_paterno, ' ', COALESCE(p.ap_materno, '')) AS nombre, p.email
                        FROM visitante v JOIN persona p ON p.id_persona = v.id_persona ORDER BY p.ap_paterno, p.nombre_pila""")
    etiqueta_v = {int(r.id_persona): f"{r.nombre.strip()} — {r.email}" for r in visit.itertuples()}

    with st.form("form_reserva", clear_on_submit=True):
        id_act = st.selectbox("Actividad (solo programadas con cupos)", list(etiqueta_a), format_func=etiqueta_a.get)
        id_vis = st.selectbox("Visitante", list(etiqueta_v), format_func=etiqueta_v.get)
        obs = st.text_area("Observaciones (opcional)", max_chars=255)
        enviar = st.form_submit_button("Confirmar reserva", type="primary")

    if enviar:
        dup = consulta("SELECT 1 FROM reserva WHERE id_visitante = :v AND id_actividad = :a",
                       {"v": int(id_vis), "a": int(id_act)})
        if not dup.empty:
            st.error("Ese visitante ya tiene una reserva para esta actividad.")
        else:
            intentar([("""INSERT INTO reserva (id_visitante, id_actividad, fecha_reserva, estado, asistencia_efectiva, observaciones)
                          VALUES (:v, :a, NOW(), 'CONFIRMADA', 0, :o)""",
                       {"v": int(id_vis), "a": int(id_act), "o": obs.strip() or None})],
                     ok="✅ Reserva confirmada.")

    st.subheader("Reservas de la actividad seleccionada")
    sel = st.selectbox("Ver reservas de", list(etiqueta_a), format_func=etiqueta_a.get, key="ver_reservas")
    df = consulta("""SELECT r.id_reserva, CONCAT(p.nombre_pila, ' ', p.ap_paterno) AS visitante, r.estado, r.fecha_reserva, r.observaciones
                     FROM reserva r JOIN persona p ON p.id_persona = r.id_visitante
                     WHERE r.id_actividad = :a ORDER BY r.fecha_reserva DESC""", {"a": int(sel)})
    st.dataframe(df, width="stretch", hide_index=True)

    with st.expander("Cancelar una reserva"):
        activas = df[df["estado"] == "CONFIRMADA"]
        if activas.empty:
            st.caption("No hay reservas confirmadas en esta actividad.")
        else:
            id_r = st.selectbox("Reserva", activas["id_reserva"].tolist(),
                                format_func=lambda i: f"#{i} · {activas.set_index('id_reserva').loc[i, 'visitante']}")
            if st.button("Cancelar reserva"):
                if intentar([("UPDATE reserva SET estado = 'CANCELADA' WHERE id_reserva = :r", {"r": int(id_r)})],
                            ok="Reserva cancelada."):
                    st.rerun()
