import streamlit as st
import pandas as pd
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

st.subheader("📊 Resumen")

st.write(
    f"Jugadores master: {len(jugadores_master)}"
)

st.write(
    f"Equipos master: {len(equipos_master)}"
)

st.write(
    f"Parejas: {len(estadisticas_parejas)}"
)

st.divider()

# ==================================================
# CARGAR
# ==================================================

if st.button("📤 Cargar Master Inicial"):

    try:

        # ------------------------------------------
        # JUGADORES MASTER
        # ------------------------------------------

        jugadores_master = (
            jugadores_master
            .where(
                pd.notnull(jugadores_master),
                None
            )
        )

        registros_jugadores = (
            jugadores_master
            .to_dict("records")
        )

        if len(registros_jugadores) > 0:

            (
                supabase
                .table("jugadores_master")
                .insert(
                    registros_jugadores
                )
                .execute()
            )

        # ------------------------------------------
        # EQUIPOS MASTER
        # ------------------------------------------

        equipos_master = (
            equipos_master
            .where(
                pd.notnull(equipos_master),
                None
            )
        )

        registros_equipos = (
            equipos_master
            .to_dict("records")
        )

        if len(registros_equipos) > 0:

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

        estadisticas_parejas = (
            estadisticas_parejas
            .where(
                pd.notnull(
                    estadisticas_parejas
                ),
                None
            )
        )

        registros_parejas = (
            estadisticas_parejas
            .to_dict("records")
        )

        if len(registros_parejas) > 0:

            (
                supabase
                .table(
                    "estadisticas_parejas"
                )
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
