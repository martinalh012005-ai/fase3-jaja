"""Acceso a MySQL con SQLAlchemy + PyMySQL (misma base del proyecto)."""
import os

import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.exc import DBAPIError


@st.cache_resource
def get_engine():
    url = "mysql+pymysql://{u}:{p}@{h}:{port}/{db}?charset=utf8mb4".format(
        u=os.getenv("DB_USER", "root"),
        p=os.getenv("DB_PASSWORD", "root"),
        h=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "3306"),
        db=os.getenv("DB_NAME", "turismo_astronomico"),
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def consulta(sql, params=None, listas=()):
    """SELECT -> DataFrame. 'listas' = nombres de parámetros que son listas (IN :x)."""
    stmt = text(sql)
    for nombre in listas:
        stmt = stmt.bindparams(bindparam(nombre, expanding=True))
    with get_engine().connect() as cx:
        return pd.read_sql(stmt, cx, params=params or {})


@st.cache_data(ttl=30, show_spinner=False)
def consulta_cache(sql, params=None, listas=()):
    return consulta(sql, params, listas)


def ejecutar(sentencias):
    """Ejecuta una o varias sentencias en UNA transacción (todo o nada).
    'sentencias' = [(sql, params), ...]. Devuelve el lastrowid de la primera."""
    primero = None
    with get_engine().begin() as cx:
        for i, (sql, params) in enumerate(sentencias):
            res = cx.execute(text(sql), params or {})
            if i == 0:
                primero = res.lastrowid
    consulta_cache.clear()
    return primero


def mensaje_error(exc):
    """Traduce errores del motor (CHECK, UNIQUE, FK, triggers) a un mensaje claro."""
    orig = getattr(exc, "orig", None)
    if orig is not None and getattr(orig, "args", None):
        codigo = orig.args[0] if isinstance(orig.args[0], int) else None
        detalle = str(orig.args[1]) if len(orig.args) > 1 else str(orig)
        if codigo == 1644:                       # SIGNAL de triggers
            return detalle
        if codigo == 1062:
            return "Ya existe un registro con ese valor único (duplicado)."
        if codigo in (1451, 1217):
            return "No se puede eliminar: el registro tiene datos relacionados. Use la desactivación lógica."
        if codigo in (1452, 1216):
            return "La referencia indicada no existe (clave foránea)."
        if codigo == 3819:
            return "Un valor incumple una restricción del modelo (CHECK): " + detalle.split("'")[-2] if "'" in detalle else detalle
        if codigo == 1048:
            return "Falta un campo obligatorio."
        return detalle
    return str(exc)


def intentar(sentencias, ok="Operación realizada."):
    """Ejecuta y muestra el resultado en pantalla. Devuelve True si tuvo éxito."""
    try:
        ejecutar(sentencias)
        st.success(ok)
        return True
    except DBAPIError as e:
        st.error(mensaje_error(e))
    except Exception as e:  # noqa: BLE001
        st.error(f"Error inesperado: {e}")
    return False
