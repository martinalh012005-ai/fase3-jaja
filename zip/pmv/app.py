"""PMV - Sistema Integral de Gestión de Centros de Turismo Astronómico (TDFI103 Fase 2, Caso 2)
Punto de entrada: login + navegación según los permisos del rol."""
import streamlit as st

import auth
from paginas import crud_centros, crud_fenomenos, dashboard, reserva, usuarios

st.set_page_config(page_title="Centros de Turismo Astronómico", page_icon="🔭", layout="wide")

PAGINAS = {
    "reservas": ("Registrar reserva", reserva.render),
    "crud_centros": ("Centros astronómicos", crud_centros.render),
    "crud_fenomenos": ("Fenómenos astronómicos", crud_fenomenos.render),
    "dashboard": ("Dashboard", dashboard.render),
    "usuarios": ("Usuarios y roles", usuarios.render),
}


def pantalla_login():
    st.title("🔭 Centros de Turismo Astronómico")
    st.caption("Sistema integral de gestión · TDFI103 Fase 2 · Caso 2")
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        with st.form("login"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            enviar = st.form_submit_button("Ingresar", width="stretch")
        if enviar:
            if not usuario or not clave:
                st.warning("Ingrese usuario y contraseña.")
            else:
                u, error = auth.autenticar(usuario, clave)
                if error:
                    st.error(error)
                else:
                    st.session_state["user"] = u
                    st.rerun()
        with st.expander("Cuentas de demostración"):
            st.markdown("`admin` (ADMINISTRADOR) · `operador` (OPERADOR) · `analista` (ANALISTA)  \n"
                        "Contraseña de todas: `Astro2026!`")


def main():
    u = auth.usuario_actual()
    if not u:
        pantalla_login()
        return
    permitidas = [(clave, nombre, fn) for clave, (nombre, fn) in PAGINAS.items() if clave in u["permisos"]]
    with st.sidebar:
        st.markdown(f"### 🔭 Menú\n**{u['nombre']}**  \nRol: `{u['rol']}`")
        if not permitidas:
            st.warning("Su rol no tiene funcionalidades asignadas.")
        seleccion = st.radio("Navegación", [n for _, n, _ in permitidas], label_visibility="collapsed") if permitidas else None
        st.divider()
        if st.button("Cerrar sesión", width="stretch"):
            auth.cerrar_sesion()
            st.rerun()
    for clave, nombre, fn in permitidas:
        if nombre == seleccion:
            fn()


main()
