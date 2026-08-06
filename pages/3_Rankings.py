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


def mostrar_ranking(dataframe):
    if dataframe.empty:
        st.info("No hay registros que cumplan los requisitos del ranking.")
    else:
        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True
        )


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
    "tipo_racha_activa"
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
# NORMALIZACION NUMERICA
# ==================================================

for columna in ["PJ", "G", "E", "P", "racha_activa"]:
    jugadores[columna] = pd.to_numeric(
        jugadores[columna],
        errors="coerce"
    )

jugadores["WinRate"] = pd.to_numeric(
    jugadores["WinRate"],
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "🏃 Más partidos",
        "🥇 Más victorias",
        "📈 Mejor Win Rate",
        "🔥 Rachas activas",
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
# RACHAS ACTIVAS
# ==================================================

with tab4:
    st.subheader("Top 20 rachas activas")

    rachas_validas = jugadores[
        jugadores["racha_activa"].notna()
        & (jugadores["tipo_racha_activa"] != "Inactivo")
    ].copy()

    ranking = (
        rachas_validas
        .sort_values(
            ["racha_activa", "WinRate", "PJ", "jugador"],
            ascending=[False, False, False, True],
            na_position="last"
        )
        [
            [
                "jugador",
                "tipo_racha_activa",
                "racha_activa",
                "PJ",
                "WinRate"
            ]
        ]
        .rename(
            columns={
                "jugador": "Jugador",
                "tipo_racha_activa": "Tipo",
                "racha_activa": "Racha",
                "WinRate": "Win Rate %"
            }
        )
        .head(20)
    )

    mostrar_ranking(ranking)


# ==================================================
# EQUIPOS MAS GANADORES
# ==================================================

with tab5:
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

with tab6:
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
