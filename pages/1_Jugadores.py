import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("👤 Jugadores")

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


def texto_seguro(valor, reemplazo="Sin datos"):
    if pd.isna(valor) or valor is None or str(valor).strip() == "":
        return reemplazo

    return str(valor)


def numero_entero_seguro(valor):
    if pd.isna(valor) or valor is None:
        return 0

    return int(valor)


def numero_decimal_seguro(valor):
    if pd.isna(valor) or valor is None:
        return 0.0

    return float(valor)


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    participaciones = leer_tabla_completa("participaciones")
    parejas = leer_tabla_completa("estadisticas_parejas")
    partidos = leer_tabla_completa("partidos")

except Exception as error:
    st.error("No se pudieron leer los datos desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if participaciones.empty:
    st.warning("La tabla participaciones no contiene registros.")
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
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
    "equipo_favorito",
    "rival_mas_frecuente",
    "pj_vs_rival_mas_frecuente",
    "mejor_racha_ganadora",
    "racha_activa"
]

columnas_participaciones = [
    "partido_id",
    "jugador",
    "equipo"
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

columnas_partidos = [
    "id",
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

validaciones = [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("participaciones", participaciones, columnas_participaciones),
    ("estadisticas_parejas", parejas, columnas_parejas),
    ("partidos", partidos, columnas_partidos)
]

for nombre_tabla, dataframe, columnas_requeridas in validaciones:
    faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in dataframe.columns
    ]

    if faltantes:
        st.error(
            f"Faltan columnas en {nombre_tabla}: "
            + ", ".join(faltantes)
        )
        st.stop()


# ==================================================
# PREPARACION DEL HISTORIAL
# ==================================================

partidos["fecha"] = pd.to_datetime(
    partidos["fecha"],
    errors="coerce"
)

partidos["goles_local"] = pd.to_numeric(
    partidos["goles_local"],
    errors="coerce"
)

partidos["goles_visitante"] = pd.to_numeric(
    partidos["goles_visitante"],
    errors="coerce"
)

partidos["resultado_local"] = "E"

partidos.loc[
    partidos["goles_local"] > partidos["goles_visitante"],
    "resultado_local"
] = "G"

partidos.loc[
    partidos["goles_local"] < partidos["goles_visitante"],
    "resultado_local"
] = "P"

participaciones_historial = participaciones.merge(
    partidos[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "resultado_local"
        ]
    ],
    left_on="partido_id",
    right_on="id",
    how="left",
    suffixes=("", "_partido")
)

participaciones_historial["resultado_jugador"] = ""

mask_local = (
    participaciones_historial["equipo"]
    == participaciones_historial["equipo_local"]
)

mask_visitante = (
    participaciones_historial["equipo"]
    == participaciones_historial["equipo_visitante"]
)

participaciones_historial.loc[
    mask_local,
    "resultado_jugador"
] = participaciones_historial["resultado_local"]

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "G"),
    "resultado_jugador"
] = "P"

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "P"),
    "resultado_jugador"
] = "G"

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "E"),
    "resultado_jugador"
] = "E"

participaciones_historial = participaciones_historial[
    participaciones_historial["fecha"].notna()
    & participaciones_historial["resultado_jugador"].isin(["G", "E", "P"])
].copy()


# ==================================================
# NORMALIZACION NUMERICA
# ==================================================

for columna in [
    "PJ",
    "G",
    "E",
    "P",
    "racha_activa",
    "mejor_racha_ganadora",
    "pj_vs_rival_mas_frecuente"
]:
    if columna in jugadores.columns:
        jugadores[columna] = pd.to_numeric(
            jugadores[columna],
            errors="coerce"
        )

jugadores["WinRate"] = pd.to_numeric(
    jugadores["WinRate"],
    errors="coerce"
)

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    parejas[columna] = pd.to_numeric(
        parejas[columna],
        errors="coerce"
    )


# ==================================================
# BUSCADOR
# ==================================================

lista_jugadores = sorted(
    jugadores["jugador"]
    .dropna()
    .astype(str)
    .unique()
)

jugador = st.selectbox(
    "🔎 Buscar jugador",
    lista_jugadores,
    index=None,
    placeholder="Escribí el nombre del jugador..."
)

if jugador is None:
    st.info("Seleccioná un jugador para ver sus estadísticas.")
    st.stop()


# ==================================================
# DATOS DEL JUGADOR
# ==================================================

filas_jugador = jugadores[
    jugadores["jugador"] == jugador
]

if filas_jugador.empty:
    st.warning("No se encontraron datos para el jugador seleccionado.")
    st.stop()

info = filas_jugador.iloc[0]


# ==================================================
# DATOS DE COMPAÑEROS
# ==================================================

companeros_jugador = parejas[
    (parejas["jugador_1"] == jugador)
    | (parejas["jugador_2"] == jugador)
].copy()

if not companeros_jugador.empty:
    companeros_jugador["companero"] = companeros_jugador.apply(
        lambda fila: (
            fila["jugador_2"]
            if fila["jugador_1"] == jugador
            else fila["jugador_1"]
        ),
        axis=1
    )

    companero_frecuente = (
        companeros_jugador
        .sort_values(
            ["PJ", "companero"],
            ascending=[False, True]
        )
        .iloc[0]
    )

    companeros_relevantes = companeros_jugador[
        companeros_jugador["PJ"] >= 30
    ].copy()

    if not companeros_relevantes.empty:
        mejor_companero = (
            companeros_relevantes
            .sort_values(
                ["WinRate", "PJ", "companero"],
                ascending=[False, False, True]
            )
            .iloc[0]
        )

        peor_companero = (
            companeros_relevantes
            .sort_values(
                ["WinRate", "PJ", "companero"],
                ascending=[True, False, True]
            )
            .iloc[0]
        )
    else:
        mejor_companero = companero_frecuente
        peor_companero = companero_frecuente
else:
    companero_frecuente = None
    mejor_companero = None
    peor_companero = None


# ==================================================
# VARIABLES SEGURAS
# ==================================================

racha_activa = numero_entero_seguro(info.get("racha_activa"))
mejor_racha = numero_entero_seguro(info.get("mejor_racha_ganadora"))
pj_rival = numero_entero_seguro(info.get("pj_vs_rival_mas_frecuente"))
tipo_racha_activa = texto_seguro(
    info.get("tipo_racha_activa"),
    "Sin datos"
)


# ==================================================
# HEADER
# ==================================================

st.header(f"🏅 {jugador}")


# ==================================================
# KPIS PRINCIPALES
# ==================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric("PJ", numero_entero_seguro(info.get("PJ")))
c2.metric("Victorias", numero_entero_seguro(info.get("G")))
c3.metric("Derrotas", numero_entero_seguro(info.get("P")))
c4.metric(
    "Win Rate",
    f"{numero_decimal_seguro(info.get('WinRate')):.1f}%"
)

st.divider()


# ==================================================
# KPIS SECUNDARIOS
# ==================================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Racha Activa",
    racha_activa,
    help=f"Tipo de racha: {tipo_racha_activa}"
)

c2.metric("Mejor Racha", mejor_racha)
c3.metric("Empates", numero_entero_seguro(info.get("E")))

st.divider()


# ==================================================
# INFORMACION DESTACADA
# ==================================================

c1, c2 = st.columns(2)

with c1:
    st.info(
        "🏟️ Equipo favorito: "
        f"{texto_seguro(info.get('equipo_favorito'))}"
    )

    if companero_frecuente is not None:
        st.info(
            "🤝 Compañero más frecuente: "
            f"{companero_frecuente['companero']} "
            f"({numero_entero_seguro(companero_frecuente['PJ'])} PJ)"
        )
    else:
        st.info("🤝 Compañero más frecuente: Sin datos")

    if mejor_companero is not None:
        st.info(
            "🏆 Mejor compañero: "
            f"{mejor_companero['companero']} "
            f"({numero_decimal_seguro(mejor_companero['WinRate']):.1f}% WR)"
        )
    else:
        st.info("🏆 Mejor compañero: Sin datos")

with c2:
    st.info(
        "🥊 Rival más frecuente: "
        f"{texto_seguro(info.get('rival_mas_frecuente'))} "
        f"({pj_rival} PJ)"
    )

    if peor_companero is not None:
        st.info(
            "📉 Peor compañero: "
            f"{peor_companero['companero']} "
            f"({numero_decimal_seguro(peor_companero['WinRate']):.1f}% WR)"
        )
    else:
        st.info("📉 Peor compañero: Sin datos")

    st.info(
        f"🔥 Mejor racha histórica: {mejor_racha} victorias"
    )


# ==================================================
# EVOLUCION HISTORICA
# ==================================================

historial = participaciones_historial[
    participaciones_historial["jugador"] == jugador
].copy()

historial["Año"] = historial["fecha"].dt.year

evolucion = (
    historial
    .groupby("Año")
    .agg(
        PJ=("resultado_jugador", "size"),
        PG=(
            "resultado_jugador",
            lambda resultados: (resultados == "G").sum()
        )
    )
    .reset_index()
)

if not evolucion.empty:
    evolucion["WinRate"] = (
        evolucion["PG"]
        / evolucion["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

st.divider()
st.subheader("📈 Evolución histórica")

if evolucion.empty:
    st.info("No hay datos históricos para mostrar.")
else:
    fig = go.Figure()

    fig.add_bar(
        x=evolucion["Año"],
        y=evolucion["PJ"],
        name="Partidos Jugados"
    )

    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"],
            y=evolucion["PG"],
            mode="lines+markers",
            name="Victorias"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"],
            y=evolucion["WinRate"],
            mode="lines+markers",
            name="Win Rate %",
            yaxis="y2"
        )
    )

    fig.update_layout(
        height=550,
        hovermode="x unified",
        xaxis_title="Año",
        yaxis={
            "title": "Partidos / Victorias"
        },
        yaxis2={
            "title": "Win Rate %",
            "overlaying": "y",
            "side": "right"
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1
        }
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==================================================
# ANALISIS DE DUPLA
# ==================================================

st.divider()
st.subheader("🤝 Analizar dupla")

opciones_companeros = sorted(
    jugadores.loc[
        jugadores["jugador"] != jugador,
        "jugador"
    ]
    .dropna()
    .astype(str)
    .unique()
)

companero = st.selectbox(
    "Seleccionar segundo jugador",
    opciones_companeros,
    index=None,
    placeholder="Seleccioná otro jugador..."
)

if companero is None:
    st.info("Seleccioná un segundo jugador para analizar la dupla.")
else:
    dupla = parejas[
        (
            (parejas["jugador_1"] == jugador)
            & (parejas["jugador_2"] == companero)
        )
        |
        (
            (parejas["jugador_2"] == jugador)
            & (parejas["jugador_1"] == companero)
        )
    ]

    if not dupla.empty:
        datos_dupla = dupla.iloc[0]

        st.subheader(f"📊 {jugador} + {companero}")

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "PJ Juntos",
            numero_entero_seguro(datos_dupla["PJ"])
        )
        c2.metric(
            "Victorias",
            numero_entero_seguro(datos_dupla["G"])
        )
        c3.metric(
            "Empates",
            numero_entero_seguro(datos_dupla["E"])
        )
        c4.metric(
            "Derrotas",
            numero_entero_seguro(datos_dupla["P"])
        )
        c5.metric(
            "Win Rate",
            f"{numero_decimal_seguro(datos_dupla['WinRate']):.1f}%"
        )
    else:
        st.warning("No se encontraron partidos juntos.")
