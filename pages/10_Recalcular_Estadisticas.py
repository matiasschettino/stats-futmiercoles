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

st.success("✅ Acceso autorizado")

# ==================================================
# CONEXIÓN
# ==================================================

supabase = get_supabase()

# ==================================================
# FUNCIONES
# ==================================================

def leer_tabla_completa(tabla):

    registros = []

    desde = 0
    lote = 1000

    while True:

        respuesta = (
            supabase
            .table(tabla)
            .select("*")
            .range(
                desde,
                desde + lote - 1
            )
            .execute()
        )

        if not respuesta.data:
            break

        registros.extend(
            respuesta.data
        )

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(registros)

# ==================================================
# BOTÓN
# ==================================================

if st.button("🔄 Ejecutar Chequeo"):

    try:

        # ==========================================
        # LECTURA COMPLETA
        # ==========================================

        partidos_df = leer_tabla_completa(
            "partidos"
        )

        participaciones_df = leer_tabla_completa(
            "participaciones"
        )

        jugadores_master_df = leer_tabla_completa(
            "jugadores_master"
        )

        # ==========================================
        # INFO
        # ==========================================

        st.subheader("📊 Datos leídos")

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.write(
            f"Jugadores Master: {len(jugadores_master_df)}"
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
                    "id",
                    "equipo_local",
                    "equipo_visitante",
                    "resultado_local"
                ]
            ],
            left_on="partido_id",
            right_on="id",
            how="left",
            suffixes=(
                "",
                "_partido"
            )
        )

        # ==========================================
        # RESULTADO JUGADOR
        # ==========================================

        participaciones_df[
            "resultado_jugador"
        ] = ""

        mask_local = (
            participaciones_df["equipo"]
            ==
            participaciones_df["equipo_local"]
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
            participaciones_df["equipo_visitante"]
        )

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ]
                == "G"
            ),
            "resultado_jugador"
        ] = "P"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ]
                == "P"
            ),
            "resultado_jugador"
        ] = "G"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ]
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
            * 100
        ).round(2)

        # ==========================================
# EQUIPO FAVORITO
# ==========================================

partidos_por_equipo = (
    participaciones_df
    .groupby(
        ["jugador", "equipo"]
    )
    .size()
    .reset_index(name="partidos")
)

partidos_por_equipo = (
    partidos_por_equipo
    .sort_values(
        ["jugador", "partidos"],
        ascending=[True, False]
    )
)

equipo_favorito = (
    partidos_por_equipo
    .groupby("jugador")
    .first()
    .reset_index()
)

equipo_favorito = equipo_favorito.rename(
    columns={
        "equipo": "equipo_favorito",
        "partidos": "partidos_equipo_favorito"
    }
)

estadisticas_jugador = estadisticas_jugador.merge(
    equipo_favorito[
        [
            "jugador",
            "equipo_favorito",
            "partidos_equipo_favorito"
        ]
    ],
    on="jugador",
    how="left"
)


comparacion_favorito = (
    estadisticas_jugador[
        [
            "jugador",
            "equipo_favorito",
            "partidos_equipo_favorito"
        ]
    ]
    .merge(
        jugadores_master_df[
            [
                "jugador",
                "equipo_favorito",
                "partidos_equipo_favorito"
            ]
        ],
        on="jugador",
        suffixes=(
            "_nuevo",
            "_actual"
        )
    )
)

diferencias_favorito = comparacion_favorito[
    (
        comparacion_favorito[
            "equipo_favorito_nuevo"
        ]
        !=
        comparacion_favorito[
            "equipo_favorito_actual"
        ]
    )
    |
    (
        comparacion_favorito[
            "partidos_equipo_favorito_nuevo"
        ]
        !=
        comparacion_favorito[
            "partidos_equipo_favorito_actual"
        ]
    )
]

st.subheader(
    "🏆 Equipo Favorito"
)

st.write(
    f"Diferencias encontradas: {len(diferencias_favorito)}"
)

if len(diferencias_favorito):

    st.dataframe(
        diferencias_favorito
    )
        
        
        # ==========================================
        # COMPARACION
        # ==========================================

        columnas = [
            "jugador",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate"
        ]

        comparacion = (
            estadisticas_jugador[
                columnas
            ]
            .merge(
                jugadores_master_df[
                    columnas
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
                comparacion[
                    "WinRate_nuevo"
                ].round(2)
                ==
                comparacion[
                    "WinRate_actual"
                ].round(2)
            )
        )

        diferencias = comparacion[
            comparacion["OK"] == False
        ]

        # ==========================================
        # RESULTADOS
        # ==========================================

        st.subheader("✅ Resultado")

        if len(diferencias) == 0:

            st.success(
                "✅ PJ / G / E / P / WinRate coinciden 100%"
            )

        else:

            st.error(
                f"⚠️ Se detectaron {len(diferencias)} diferencias"
            )

            st.dataframe(
                diferencias
            )

        # ==========================================
        # PREVIEW
        # ==========================================

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

        st.exception(e)
