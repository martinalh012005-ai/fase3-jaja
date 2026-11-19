"""Funcionalidad 3 (parte administrativa) - gestión de cuentas y roles. Solo rol con permiso 'usuarios'."""
import streamlit as st

import auth
from db import consulta, intentar


def render():
    auth.requiere("usuarios")
    st.header("👥 Usuarios y roles")
    yo = auth.usuario_actual()

    st.subheader("Roles y permisos")
    roles = consulta("SELECT id_rol, nombre, descripcion, permisos, activo FROM rol ORDER BY id_rol")
    st.dataframe(roles, width="stretch", hide_index=True)

    st.subheader("Cuentas")
    cuentas = consulta("""SELECT c.id_cuenta, c.nombre_usuario AS usuario, CONCAT(p.nombre_pila, ' ', p.ap_paterno) AS trabajador,
                                 t.cargo, ce.nombre AS centro, r.nombre AS rol, c.activa
                          FROM cuenta_usuario c
                          JOIN persona p ON p.id_persona = c.id_trabajador
                          JOIN trabajador t ON t.id_persona = c.id_trabajador
                          JOIN centro_astronomico ce ON ce.id_centro = t.id_centro
                          JOIN rol r ON r.id_rol = c.id_rol ORDER BY c.nombre_usuario""")
    filtro = st.multiselect("Filtrar por rol", roles["nombre"].tolist(), default=roles["nombre"].tolist())
    st.dataframe(cuentas[cuentas["rol"].isin(filtro)], width="stretch", hide_index=True)

    st.subheader("Modificar una cuenta")
    etiquetas = {int(r.id_cuenta): f"{r.usuario} — {r.trabajador} ({r.rol})" for r in cuentas.itertuples()}
    sel = st.selectbox("Cuenta", list(etiquetas), format_func=etiquetas.get)
    fila = cuentas[cuentas["id_cuenta"] == sel].iloc[0]
    mapa_roles = dict(zip(roles["id_rol"], roles["nombre"]))
    ids = list(mapa_roles)
    actual = int(roles[roles["nombre"] == fila["rol"]].iloc[0]["id_rol"])
    c1, c2 = st.columns(2)
    nuevo_rol = c1.selectbox("Rol", ids, index=ids.index(actual), format_func=mapa_roles.get)
    activa = c2.checkbox("Cuenta activa", value=bool(fila["activa"]))
    propia = int(sel) == yo["id_cuenta"]
    if propia:
        st.caption("Es su propia cuenta: no puede desactivarla ni cambiar su rol (evita bloquearse).")
    if st.button("Guardar cambios de la cuenta", disabled=propia):
        if intentar([("UPDATE cuenta_usuario SET id_rol = :r, activa = :a WHERE id_cuenta = :c",
                      {"r": int(nuevo_rol), "a": int(activa), "c": int(sel)})], ok="Cuenta actualizada."):
            st.rerun()
