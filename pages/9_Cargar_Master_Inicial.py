import streamlit as st
import pandas as pd
import numpy as np
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("📤 Cargar Master Inicial")

usuario = st.text_input("Usuario")

password = st.text_input(
    "Contraseña",
    type="password"
)

if (
    usuario != st.secrets["ADMIN_USER"]
    or
    password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning("Acceso restringido")
    st.stop()

st.success("✅ Acceso autorizado")

# ==================================================
# CONEXIÓN
# ==================================================

supabase = get_supabase()

# ==================================================
# LEER CSV
# ==================================================

jugadores_master = pd.read_csv(
    "jugadores_master.csv"
)

equipos_master = pd.read_csv(
    "equipos_master.csv"
)

estadisticas_parejas = pd.read_csv(
    "estadisticas_parejas.csv"
)

# ==================================================
# INFO
# ==================================================

st.subheader("📊 Resumen")

st.write(
    f"Jugadores Master: {len(jugadores_master)}"
)

st.write(
    f"Equipos Master: {len(equipos_master)}"
)

st.write(
    f"Parejas: {len(estadisticas_parejas)}"
)

st.divider()

# ==================================================
# DEBUG
# ==================================================

st.subheader("🔎 Columnas detectadas")

st.write(
    "Jugadores:",
    jugadores_master.columns.tolist()
)

st.write(
    "Equipos:",
    equipos_master.columns.tolist()
)

st.write(
    "Parejas:",
    estadisticas_parejas.columns.tolist()
)

# ==================================================
# BOTÓN CARGA
# ==================================================

if st.button("📤 Cargar Master Inicial"):

    try:

        # ==================================================
        # JUGADORES
        # ==================================================

        if "id" in jugadores_master.columns:

            jugadores_master = (
                jugadores_master
                .drop(columns=["id"])
            )

        jugadores_master = (
            jugadores_master
            .replace(
                [np.nan, np.inf, -np.inf],
                None
            )
        )

        registros_jugadores = (
            jugadores_master
            .to_dict("records")
        )

        if registros_jugadores:

            (
                supabase
                .table("jugadores_master")
                .insert(
                    registros_jugadores
                )
                .execute()
            )

        # ==================================================
        # EQUIPOS
        # ==================================================

        if "id" in equipos_master.columns:

            equipos_master = (
                equipos_master
                .drop(columns=["id"])
            )

        equipos_master = (
            equipos_master
            .replace(
                [np.nan, np.inf, -np.inf],
                None
            )
        )

        registros_equipos = (
            equipos_master
            .to_dict("records")
        )

        if registros_equipos:

            (
                supabase
                .table("equipos_master")
                .insert(
                    registros_equipos
                )
                .execute()
            )

        # ==================================================
        # PAREJAS
        # ==================================================

        if "id" in estadisticas_parejas.columns:

            estadisticas_parejas = (
                estadisticas_parejas
                .drop(columns=["id"])
            )

        estadisticas_parejas = (
            estadisticas_parejas
            .replace(
                [np.nan, np.inf, -np.inf],
                None
            )
        )

        registros_parejas = (
            estadisticas_parejas
            .to_dict("records")
        )

        if registros_parejas:

            (
                supabase
                .table("estadisticas_parejas")
                .insert(
                    registros_parejas
                )
                .execute()
            )

        st.success(
            "✅ Master inicial cargado correctamente"
        )

    except Exception as e:

        st.error(
            f"Error: {e}"
        )
