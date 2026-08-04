import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("🔄 Recalcular Estadísticas")

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

supabase = get_supabase()

# ==================================================
# BOTON
# ==================================================

if st.button("🔄 Ejecutar Chequeo"):

    try:

        # ==================================================
        # LECTURA
        # ==================================================

        partidos = (
            supabase
            .table("partidos")
            .select("*")
            .execute()
        )

        participaciones = (
            supabase
            .table("participaciones")
            .select("*")
            .execute()
        )

        jugadores_master = (
            supabase
            .table("jugadores_master")
            .select("*")
            .execute()
        )

        partidos_df = pd.DataFrame(
            partidos.data
        )

        participaciones_df = pd.DataFrame(
            participaciones.data
        )

        jugadores_master_df = pd.DataFrame(
            jugadores_master.data
        )

        # ==================================================
        # ESTADISTICAS BASICAS
        # ==================================================

        estadisticas_jugador = (
            participaciones_df
            .pivot_table(
                index="jugador",
                columns="resultado_jugador",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        # Asegurar columnas

        for col in ["G", "E", "P"]:

            if col not in estadisticas_jugador.columns:

                estadisticas_jugador[col] = 0

        estadisticas_jugador["PJ"] = (
            estadisticas_jugador["G"]
            +
            estadisticas_jugador["E"]
            +
            estadisticas_jugador["P"]
        )

        estadisticas_jugador["WinRate"] = (
            estadisticas_jugador["G"]
            /
            estadisticas_jugador["PJ"]
            *
            100
        ).round(2)

        # ==================================================
        # RESUMEN
        # ==================================================

        st.subheader("📊 Resumen")

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.write(
            f"Jugadores recalculados: {len(estadisticas_jugador)}"
        )

        st.write(
            f"Jugadores master: {len(jugadores_master_df)}"
        )

        # ==================================================
        # COMPARACION
        # ==================================================

        master_cols = [
            "jugador",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate"
        ]

        comparacion = (
            estadisticas_jugador[
                master_cols
            ]
            .merge(
                jugadores_master_df[
                    master_cols
                ],
                on="jugador",
                suffixes=(
                    "_nuevo",
                    "_actual"
                ),
                how="outer"
            )
        )

        comparacion["OK"] = (
            (comparacion["PJ_nuevo"] == comparacion["PJ_actual"])
            &
            (comparacion["G_nuevo"] == comparacion["G_actual"])
            &
            (comparacion["E_nuevo"] == comparacion["E_actual"])
            &
            (comparacion["P_nuevo"] == comparacion["P_actual"])
            &
            (
                comparacion["WinRate_nuevo"].round(2)
                ==
                comparacion["WinRate_actual"].round(2)
            )
        )

        diferencias = comparacion[
            comparacion["OK"] == False
        ]

        # ==================================================
        # RESULTADO
        # ==================================================

        st.subheader("✅ Validación")

        if len(diferencias) == 0:

            st.success(
                "✅ PJ / G / E / P / WinRate coinciden 100% con jugadores_master"
            )

        else:

            st.error(
                f"⚠️ Se encontraron {len(diferencias)} diferencias"
            )

            st.dataframe(
                diferencias
            )

        # ==================================================
        # MUESTRA
        # ==================================================

        st.subheader(
            "👀 Vista previa recalculada"
        )

        st.dataframe(
            estadisticas_jugador
            .sort_values(
                "PJ",
                ascending=False
            )
            .head(30)
        )

    except Exception as e:

        st.error(
            f"Error: {e}"
        )
