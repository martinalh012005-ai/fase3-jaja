"""Autenticación y control de acceso por rol.
Las contraseñas se almacenan como PBKDF2-SHA256: pbkdf2_sha256$iteraciones$sal$hash"""
import hashlib
import hmac

import streamlit as st

from db import consulta

PAGINAS_POR_PERMISO = {
    "reservas": "Registrar reserva",
    "crud_centros": "Centros astronómicos",
    "crud_fenomenos": "Fenómenos astronómicos",
    "dashboard": "Dashboard",
    "usuarios": "Usuarios y roles",
}


def verificar_password(password, almacenado):
    try:
        esquema, iteraciones, sal, esperado = almacenado.split("$")
        if esquema != "pbkdf2_sha256":
            return False
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), int(iteraciones))
        return hmac.compare_digest(h.hex(), esperado)
    except (ValueError, AttributeError):
        return False


def autenticar(usuario, password):
    """Devuelve (usuario_dict | None, mensaje_error | None)."""
    df = consulta(
        """SELECT c.id_cuenta, c.nombre_usuario, c.contrasena_hash, c.activa,
                  r.nombre AS rol, r.permisos, r.activo AS rol_activo,
                  CONCAT(p.nombre_pila, ' ', p.ap_paterno) AS nombre
           FROM cuenta_usuario c
           JOIN rol r     ON r.id_rol = c.id_rol
           JOIN persona p ON p.id_persona = c.id_trabajador
           WHERE c.nombre_usuario = :u""", {"u": usuario.strip()})
    # mismo mensaje para usuario inexistente o contraseña errónea
    if df.empty or not verificar_password(password, df.loc[0, "contrasena_hash"]):
        return None, "Usuario o contraseña incorrectos."
    f = df.iloc[0]
    if not f["activa"] or not f["rol_activo"]:
        return None, "La cuenta o su rol están desactivados. Contacte al administrador."
    permisos = {p.strip() for p in f["permisos"].split(",") if p.strip()}
    return dict(id_cuenta=int(f["id_cuenta"]), usuario=f["nombre_usuario"], nombre=f["nombre"],
                rol=f["rol"], permisos=permisos), None


def usuario_actual():
    return st.session_state.get("user")


def requiere(permiso):
    """Barrera de acceso real: se invoca al inicio de cada página."""
    u = usuario_actual()
    if not u or permiso not in u["permisos"]:
        st.error("🔒 Su rol no tiene permiso para usar esta funcionalidad.")
        st.stop()


def cerrar_sesion():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
