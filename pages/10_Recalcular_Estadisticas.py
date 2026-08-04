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
# EJECUTAR CHEQUEO
# ==================================================

if st.button("🔄 Ejecutar Chequeo"):

    try:

        partidos_res = (
            supabase
            .table("partidos")
            .select("*")
            .limit(5)
            .execute()
        )

        participaciones_res = (
            supabase
            .table("participaciones")
            .select("*")
            .limit(5)
            .execute()
        )

        partidos_df = pd.DataFrame(
            partidos_res.data
        )

        participaciones_df = pd.DataFrame(
            participaciones_res.data
        )

        st.subheader("PARTIDOS")

        st.write(
            partidos_df.columns.tolist()
        )

        st.dataframe(partidos_df)

        st.subheader("PARTICIPACIONES")

        st.write(
            participaciones_df.columns.tolist()
        )

        st.dataframe(participaciones_df)

    except Exception as e:

        st.exception(e)

        # ==========================================
        # LEER TABLAS
        # ==========================================

        partidos_res = (
            supabase
            .table("partidos")
            .select("*")
            .execute()
        )

        participaciones_res = (
            supabase
            .table("participaciones")
            .select("*")
            .execute()
        )

        master_res = (
            supabase
            .table("jugadores_master")
            .select("*")
            .execute()
        )

        partidos_df = pd.DataFrame(
            partidos_res.data
        )

        participaciones_df = pd.DataFrame(
            participaciones_res.data
        )

        jugadores_master_df = pd.DataFrame(
            master_res.data
        )

        # ==========================================
        # DEBUG
        # ==========================================

        st.subheader("📋 Columnas detectadas")

        st.write(
            "Partidos:",
            partidos_df.columns.tolist()
        )

        st.write(
            "Participaciones:",
            participaciones_df.columns.tolist()
        )

        st.write(
            "Jugadores Master:",
            jugadores_master_df.columns.tolist()
        )

        # ==========================================
        # NORMALIZAR FECHAS
        # ==========================================

        partidos_df["id_partido"] = pd.to_datetime(
            partidos_df["id_partido"]
        )

        participaciones_df["id_partido"] = pd.to_datetime(
            participaciones_df["id_partido"]
        )

        # ==========================================
        # RESULTADO LOCAL
        # ==========================================

        partidos_df["resultado_local"] = "E"

        partidos_df.loc[
            partidos_df["goles_local"]
            >
            partidos_df["goles_visitante"],
            "resultado_local"
        ] = "G"

        partidos_df.loc[
            partidos_df["goles_local"]
            <
            partidos_df["goles_visitante"],
            "resultado_local"
        ] = "P"

        # ==========================================
        # MERGE
        # ==========================================

        participaciones_df = participaciones_df.merge(
            partidos_df[
                [
                    "id_partido",
                    "Local",
                    "Otros",
                    "resultado_local"
                ]
            ],
            on="id_partido",
            how="left"
        )

        # ==========================================
        # RESULTADO JUGADOR
        # ==========================================

        participaciones_df["resultado_jugador"] = ""

        mask_local = (
            participaciones_df["equipo"]
            ==
            participaciones_df["Local"]
        )

        participaciones_df.loc[
            mask_local,
            "resultado_jugador"
        ] = participaciones_df[
            "resultado_local"
        ]

        mask_visitante = (
            participaciones_df["equipo"]
            ==
            participaciones_df["Otros"]
        )

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "G"
            ),
            "resultado_jugador"
        ] = "P"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "P"
            ),
            "resultado_jugador"
        ] = "G"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "E"
            ),
            "resultado_jugador"
        ] = "E"

        # ==========================================
        # ESTADISTICAS JUGADOR
        # ==========================================

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

        # ==========================================
        # COMPARACION
        # ==========================================

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
                how="outer",
                suffixes=(
                    "_nuevo",
                    "_actual"
                )
            )
        )

        comparacion["OK"] = (
            (
                comparacion["PJ_nuevo"]
                ==
                comparacion["PJ_actual"]
            )
            &
            (
                comparacion["G_nuevo"]
                ==
                comparacion["G_actual"]
            )
            &
            (
                comparacion["E_nuevo"]
                ==
                comparacion["E_actual"]
            )
            &
            (
                comparacion["P_nuevo"]
                ==
                comparacion["P_actual"]
            )
            &
            (
                comparacion["WinRate_nuevo"]
                .round(2)
                ==
                comparacion["WinRate_actual"]
                .round(2)
            )
        )

        diferencias = comparacion[
            comparacion["OK"] == False
        ]

        # ==========================================
        # RESULTADOS
        # ==========================================

        st.subheader("📊 Resumen")

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.write(
            f"Jugadores calculados: {len(estadisticas_jugador)}"
        )

        st.write(
            f"Jugadores master: {len(jugadores_master_df)}"
        )

        st.subheader("✅ Validación")

        if len(diferencias) == 0:

            st.success(
                "✅ PJ / G / E / P / WinRate coinciden 100%"
            )

        else:

            st.error(
                f"⚠️ Diferencias encontradas: {len(diferencias)}"
            )

            st.dataframe(
                diferencias
            )

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
