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
# FUNCIÓN LIMPIEZA
# ==================================================

def limpiar_dataframe(df):

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    df = df.replace(
        [np.nan, np.inf, -np.inf],
        None
    )

    for col in df.columns:

        try:

            serie = pd.to_numeric(
                df[col],
                errors="ignore"
            )

            if str(serie.dtype).startswith("float"):

                valores = serie.dropna()

                if len(valores) > 0:

                    if (
                        valores
                        .apply(
                            lambda x: float(x).is_integer()
                        )
                        .all()
                    ):

                        df[col] = serie.astype("Int64")

        except Exception:
            pass

    df = df.astype(object)

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

st.divider()

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
# CARGA
# ==================================================

if st.button("📤 Cargar Master Inicial"):

    try:

        # ------------------------------------------
        # JUGADORES
        # ------------------------------------------

        jugadores_df = limpiar_dataframe(
            jugadores_master.copy()
        )

        registros_jugadores = (
            jugadores_df
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

        # ------------------------------------------
        # EQUIPOS
        # ------------------------------------------

        equipos_df = limpiar_dataframe(
            equipos_master.copy()
        )

        registros_equipos = (
            equipos_df
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

        # ------------------------------------------
        # PAREJAS
        # ------------------------------------------

        parejas_df = limpiar_dataframe(
            estadisticas_parejas.copy()
        )

        registros_parejas = (
            parejas_df
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
