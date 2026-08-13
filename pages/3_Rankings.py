import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("🏆 Rankings")

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
            .range(desde, desde + lote - 1)
            .execute()
        )

        if not respuesta.data:
            break

        registros.extend(respuesta.data)

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(registros)


def mostrar_ranking(dataframe, alto=420):
    if dataframe.empty:
        st.info("No hay registros que cumplan los requisitos del ranking.")
    else:
        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
            height=alto
        )


def formatear_fechas(dataframe, columnas):
    dataframe = dataframe.copy()

    for columna in columnas:
        if columna in dataframe.columns:
            dataframe[columna] = (
                pd.to_datetime(
                    dataframe[columna],
                    errors="coerce"
                )
                .dt.strftime("%d/%m/%Y")
            )

    return dataframe


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    equipos = leer_tabla_completa("equipos_master")
    parejas = leer_tabla_completa("estadisticas_parejas")

except Exception as error:
    st.error("No se pudieron leer los rankings desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if equipos.empty:
    st.warning("La tabla equipos_master no contiene registros.")
    st.stop()

if parejas.empty:
    st.warning("La tabla estadisticas_parejas no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_jugadores = [
    "jugador",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate",
    "racha_activa",
    "tipo_racha_activa",
    "mejor_racha_ganadora",
    "racha_desde",
    "racha_hasta",
    "peor_racha_perdedora",
    "peor_racha_desde",
    "peor_racha_hasta"
]

columnas_equipos = [
    "equipo",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
]

columnas_parejas = [
    "jugador_1",
    "jugador_2",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
]

for nombre_tabla, dataframe, columnas_requeridas in [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("equipos_master", equipos, columnas_equipos),
    ("estadisticas_parejas", parejas, columnas_parejas)
]:
    columnas_faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in dataframe.columns
    ]

    if columnas_faltantes:
        st.error(
            f"Faltan columnas en {nombre_tabla}: "
            + ", ".join(columnas_faltantes)
        )
        st.stop()


# ==================================================
# NORMALIZACION NUMERICA Y FECHAS
# ==================================================

for columna in [
    "PJ",
    "G",
    "E",
    "P",
    "racha_activa",
    "mejor_racha_ganadora",
    "peor_racha_perdedora"
]:
    jugadores[columna] = pd.to_numeric(
        jugadores[columna],
        errors="coerce"
    )

jugadores["WinRate"] = pd.to_numeric(
    jugadores["WinRate"],
    errors="coerce"
)

for columna in [
    "racha_desde",
    "racha_hasta",
    "peor_racha_desde",
    "peor_racha_hasta"
]:
    jugadores[columna] = pd.to_datetime(
        jugadores[columna],
        errors="coerce"
    )

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    equipos[columna] = pd.to_numeric(
        equipos[columna],
        errors="coerce"
    )

    parejas[columna] = pd.to_numeric(
        parejas[columna],
        errors="coerce"
    )

jugadores = jugadores.dropna(subset=["jugador"]).copy()
equipos = equipos.dropna(subset=["equipo"]).copy()
parejas = parejas.dropna(subset=["jugador_1", "jugador_2"]).copy()


# ==================================================
# PESTANAS
# ==================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "🏃 Más partidos",
        "🥇 Más victorias",
        "📈 Mejor Win Rate",
        "🔥 Rachas actuales",
        "🏆 Rachas históricas",
        "⚽ Equipos",
        "🤝 Mejores duplas"
    ]
)


# ==================================================
# MAS PARTIDOS
# ==================================================

with tab1:
    st.subheader("Top 20 jugadores con más partidos")

    ranking = (
        jugadores
        .sort_values(
            ["PJ", "G", "jugador"],
            ascending=[False, False, True]
        )
        [["jugador", "PJ", "WinRate"]]
        .head(20)
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    mostrar_ranking(ranking)


# ==================================================
# MAS VICTORIAS
# ==================================================

with tab2:
    st.subheader("Top 20 jugadores con más victorias")

    ranking = (
        jugadores
        .sort_values(
            ["G", "PJ", "WinRate", "jugador"],
            ascending=[False, False, False, True]
        )
        [["jugador", "G", "PJ", "WinRate"]]
        .head(20)
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    mostrar_ranking(ranking)


# ==================================================
# MEJOR WIN RATE
# ==================================================

with tab3:
    st.subheader("Top 20 Win Rate (mínimo 50 partidos)")

    ranking = (
        jugadores[
            jugadores["PJ"] >= 50
        ]
        .sort_values(
            ["WinRate", "PJ", "G", "jugador"],
            ascending=[False, False, False, True]
        )
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .head(20)
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    mostrar_ranking(ranking)


# ==================================================
# RACHAS ACTUALES
# ==================================================

with tab4:
    st.subheader("🔥 Rachas actuales")

    rachas_validas = jugadores[
        jugadores["racha_activa"].notna()
        & (jugadores["racha_activa"] > 0)
        & (jugadores["tipo_racha_activa"] != "Inactivo")
    ].copy()

    rachas_positivas = rachas_validas[
        rachas_validas["tipo_racha_activa"] == "G"
    ].copy()

    rachas_negativas = rachas_validas[
        rachas_validas["tipo_racha_activa"] == "P"
    ].copy()

    rachas_empates = rachas_validas[
        rachas_validas["tipo_racha_activa"] == "E"
    ].copy()

    lider_positivo = (
        rachas_positivas
        .sort_values(
            ["racha_activa", "WinRate", "PJ", "jugador"],
            ascending=[False, False, False, True]
        )
        .head(1)
    )

    lider_negativo = (
        rachas_negativas
        .sort_values(
            ["racha_activa", "WinRate", "PJ", "jugador"],
            ascending=[False, True, False, True]
        )
        .head(1)
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Jugadores en racha positiva",
        len(rachas_positivas)
    )

    k2.metric(
        "Jugadores en racha negativa",
        len(rachas_negativas)
    )

    k3.metric(
        "Mayor racha positiva actual",
        (
            int(lider_positivo.iloc[0]["racha_activa"])
            if not lider_positivo.empty
            else 0
        ),
        help=(
            f"Jugador: {lider_positivo.iloc[0]['jugador']}"
            if not lider_positivo.empty
            else "No hay rachas positivas activas"
        )
    )

    k4.metric(
        "Mayor racha negativa actual",
        (
            int(lider_negativo.iloc[0]["racha_activa"])
            if not lider_negativo.empty
            else 0
        ),
        help=(
            f"Jugador: {lider_negativo.iloc[0]['jugador']}"
            if not lider_negativo.empty
            else "No hay rachas negativas activas"
        )
    )

    if not rachas_empates.empty:
        st.caption(
            f"Además, hay {len(rachas_empates)} jugador(es) "
            "con una racha activa de empates."
        )

    st.divider()

    st.subheader("🔥 Rachas positivas actuales")

    ranking_positivo = (
        rachas_positivas
        .sort_values(
            ["racha_activa", "WinRate", "PJ", "jugador"],
            ascending=[False, False, False, True]
        )
        [
            [
                "jugador",
                "racha_activa",
                "PJ",
                "G",
                "WinRate"
            ]
        ]
        .rename(
            columns={
                "jugador": "Jugador",
                "racha_activa": "Victorias consecutivas actuales",
                "WinRate": "Win Rate %"
            }
        )
        .head(20)
    )

    mostrar_ranking(ranking_positivo, alto=360)

    st.subheader("📉 Rachas negativas actuales")

    ranking_negativo = (
        rachas_negativas
        .sort_values(
            ["racha_activa", "WinRate", "PJ", "jugador"],
            ascending=[False, True, False, True]
        )
        [
            [
                "jugador",
                "racha_activa",
                "PJ",
                "P",
                "WinRate"
            ]
        ]
        .rename(
            columns={
                "jugador": "Jugador",
                "racha_activa": "Derrotas consecutivas actuales",
                "WinRate": "Win Rate %"
            }
        )
        .head(20)
    )

    mostrar_ranking(ranking_negativo, alto=360)


# ==================================================
# RACHAS HISTORICAS
# ==================================================

with tab5:
    st.subheader("🏆 Rachas históricas")
    st.caption(
        "Ranking histórico de las mejores series positivas y negativas, "
        "incluyendo el período exacto en el que ocurrieron."
    )

    mejores_rachas_historicas = jugadores[
        jugadores["mejor_racha_ganadora"].notna()
        & (jugadores["mejor_racha_ganadora"] > 0)
    ].copy()

    ranking_mejores_rachas = (
        mejores_rachas_historicas
        .sort_values(
            [
                "mejor_racha_ganadora",
                "WinRate",
                "PJ",
                "jugador"
            ],
            ascending=[False, False, False, True]
        )
        [
            [
                "jugador",
                "mejor_racha_ganadora",
                "racha_desde",
                "racha_hasta",
                "PJ",
                "G",
                "WinRate"
            ]
        ]
        .head(10)
        .rename(
            columns={
                "jugador": "Jugador",
                "mejor_racha_ganadora": "Victorias consecutivas",
                "racha_desde": "Desde",
                "racha_hasta": "Hasta",
                "PJ": "Partidos totales",
                "G": "Victorias totales",
                "WinRate": "Win Rate %"
            }
        )
    )

    ranking_mejores_rachas = formatear_fechas(
        ranking_mejores_rachas,
        ["Desde", "Hasta"]
    )

    if not ranking_mejores_rachas.empty:
        ranking_mejores_rachas.insert(
            0,
            "#",
            range(1, len(ranking_mejores_rachas) + 1)
        )

    st.subheader("🏆 Top 10 mejores rachas históricas positivas")
    mostrar_ranking(ranking_mejores_rachas, alto=420)

    st.divider()

    peores_rachas_historicas = jugadores[
        jugadores["peor_racha_perdedora"].notna()
        & (jugadores["peor_racha_perdedora"] > 0)
    ].copy()

    ranking_peores_rachas = (
        peores_rachas_historicas
        .sort_values(
            [
                "peor_racha_perdedora",
                "WinRate",
                "PJ",
                "jugador"
            ],
            ascending=[False, True, False, True]
        )
        [
            [
                "jugador",
                "peor_racha_perdedora",
                "peor_racha_desde",
                "peor_racha_hasta",
                "PJ",
                "P",
                "WinRate"
            ]
        ]
        .head(10)
        .rename(
            columns={
                "jugador": "Jugador",
                "peor_racha_perdedora": "Derrotas consecutivas",
                "peor_racha_desde": "Desde",
                "peor_racha_hasta": "Hasta",
                "PJ": "Partidos totales",
                "P": "Derrotas totales",
                "WinRate": "Win Rate %"
            }
        )
    )

    ranking_peores_rachas = formatear_fechas(
        ranking_peores_rachas,
        ["Desde", "Hasta"]
    )

    if not ranking_peores_rachas.empty:
        ranking_peores_rachas.insert(
            0,
            "#",
            range(1, len(ranking_peores_rachas) + 1)
        )

    st.subheader("📉 Top 10 mejores rachas históricas negativas")
    mostrar_ranking(ranking_peores_rachas, alto=420)


# ==================================================
# EQUIPOS MAS GANADORES
# ==================================================

with tab6:
    st.subheader("Equipos más ganadores")

    ranking = (
        equipos
        .sort_values(
            ["G", "PJ", "WinRate", "equipo"],
            ascending=[False, False, False, True]
        )
        [["equipo", "G", "E", "P", "PJ", "WinRate"]]
        .rename(
            columns={
                "equipo": "Equipo",
                "WinRate": "Win Rate %"
            }
        )
    )

    mostrar_ranking(ranking)


# ==================================================
# MEJORES DUPLAS
# ==================================================

with tab7:
    st.subheader(
        "Mejores duplas históricas (mínimo 50 partidos juntos)"
    )

    ranking = (
        parejas[
            parejas["PJ"] >= 50
        ]
        .sort_values(
            [
                "WinRate",
                "PJ",
                "G",
                "jugador_1",
                "jugador_2"
            ],
            ascending=[False, False, False, True, True]
        )
        [
            [
                "jugador_1",
                "jugador_2",
                "PJ",
                "G",
                "E",
                "P",
                "WinRate"
            ]
        ]
        .head(30)
        .rename(
            columns={
                "jugador_1": "Jugador 1",
                "jugador_2": "Jugador 2",
                "WinRate": "Win Rate %"
            }
        )
    )

    mostrar_ranking(ranking)
