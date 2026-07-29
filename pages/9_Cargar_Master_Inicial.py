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
# CONEXION
# ==================================================

supabase = get_supabase()

# ==================================================
# FUNCION LIMPIEZA
# ==================================================

def limpiar_dataframe(df):

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    df = df.replace(
        [np.nan, np.inf, -np.inf],
        None
    )

    columnas_enteras = [
        "PJ",
        "G",
        "E",
        "P",
        "partidos_equipo_favorito",
        "pj_mejor_companero",
        "pj_vs_rival_mas_frecuente",
        "mejor_racha_ganadora",
        "racha_activa",
        "pj_jugador_mas_presente",
        "pj_mejor_jugador"
    ]

    for col in columnas_enteras:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

            df[col] = (
                df[col]
                .fillna(0)
                .astype(int)
            )

    return df

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

# ==================================================
# BOTON CARGA
# ==================================================

if st.button("📤 Cargar Master Inicial"):

    try:

        # ------------------------------------------
        # JUGADORES
        # ------------------------------------------

        jugadores_df = limpiar_dataframe(
            jugadores_master.copy()
        )

        st.write("Tipos jugadores")
        st.write(jugadores_df.dtypes)

        registros_jugadores = (
            jugadores_df
            .to_dict("records")
        )

        (
            supabase
            .table("jugadores_master")
            .insert(registros_jugadores)
            .execute()
        )

        # ------------------------------------------
        # EQUIPOS
        # ------------------------------------------

        equipos_df = limpiar_dataframe(
            equipos_master.copy()
        )

        st.write("Tipos equipos")
        st.write(equipos_df.dtypes)

        registros_equipos = (
            equipos_df
            .to_dict("records")
        )

        (
            supabase
            .table("equipos_master")
            .insert(registros_equipos)
            .execute()
        )

        # ------------------------------------------
        # PAREJAS
        # ------------------------------------------

        parejas_df = limpiar_dataframe(
            estadisticas_parejas.copy()
        )

        st.write("Tipos parejas")
        st.write(parejas_df.dtypes)

        registros_parejas = (
            parejas_df
            .to_dict("records")
        )

        (
            supabase
            .table("estadisticas_parejas")
            .insert(registros_parejas)
            .execute()
        )

        st.success(
            "✅ Master inicial cargado correctamente"
        )

    except Exception as e:

        st.error(
            f"Error: {e}"
        )
