

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==================================================
# CARGA DE DATOS
# ==================================================

jugadores = pd.read_csv("jugadores_master.csv")
participaciones = pd.read_csv("participaciones.csv")
parejas = pd.read_csv("estadisticas_parejas.csv")

# ==================================================
# TÍTULO
# ==================================================

st.title("👤 Jugadores")

# ==================================================
# BUSCADOR
# ==================================================

jugador = st.selectbox(
    "🔎 Buscar jugador",
    sorted(jugadores["jugador"].unique()),
    index=None,
    placeholder="Escribí el nombre del jugador..."
)

if jugador is None:
    st.info(
        "Seleccioná un jugador para ver sus estadísticas."
    )
    st.stop()

# ==================================================
# DATOS DEL JUGADOR
# ==================================================

info = jugadores[
    jugadores["jugador"] == jugador
].iloc[0]

# ==================================================
# DATOS DE COMPAÑEROS
# ==================================================

companeros_jugador = parejas[
    (parejas["jugador_1"] == jugador)
    |
    (parejas["jugador_2"] == jugador)
].copy()

companeros_jugador["companero"] = companeros_jugador.apply(
    lambda fila:
    fila["jugador_2"]
    if fila["jugador_1"] == jugador
    else fila["jugador_1"],
    axis=1
)

companero_frecuente = (
    companeros_jugador
    .sort_values("PJ", ascending=False)
    .iloc[0]
)

companeros_relevantes = (
    companeros_jugador[
        companeros_jugador["PJ"] >= 30
    ]
)

mejor_companero = (
    companeros_relevantes
    .sort_values(
        "WinRate",
        ascending=False
    )
    .iloc[0]
)

peor_companero = (
    companeros_relevantes
    .sort_values(
        "WinRate",
        ascending=True
    )
    .iloc[0]
)

# ==================================================
# HEADER
# ==================================================

st.header(f"🏅 {jugador}")

# ==================================================
# KPIs PRINCIPALES
# ==================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "PJ",
    int(info["PJ"])
)

c2.metric(
    "Victorias",
    int(info["G"])
)

c3.metric(
    "Derrotas",
    int(info["P"])
)

c4.metric(
    "Win Rate",
    f"{info['WinRate']}%"
)

st.divider()

# ==================================================
# KPIs SECUNDARIOS
# ==================================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Racha Activa",
    int(info["racha_activa"])
)

c2.metric(
    "Mejor Racha",
    int(info["mejor_racha_ganadora"])
)

c3.metric(
    "Empates",
    int(info["E"])
)

st.divider()

# ==================================================
# INFORMACIÓN DESTACADA
# ==================================================

c1, c2 = st.columns(2)

with c1:

    st.info(
        f"🏟️ Equipo favorito: {info['equipo_favorito']}"
    )

    st.info(
        f"🤝 Compañero más frecuente: {companero_frecuente['companero']} ({int(companero_frecuente['PJ'])} PJ)"
    )

    st.info(
        f"🏆 Mejor compañero: {mejor_companero['companero']} ({mejor_companero['WinRate']:.1f}% WR)"
    )

with c2:

    st.info(
        f"🥊 Rival más frecuente: {info['rival_mas_frecuente']}"
    )

    st.info(
        f"📉 Peor compañero: {peor_companero['companero']} ({peor_companero['WinRate']:.1f}% WR)"
    )

    st.info(
        f"🔥 Mejor racha histórica: {int(info['mejor_racha_ganadora'])} victorias"
    )

# ==================================================
# EVOLUCIÓN HISTÓRICA
# ==================================================

participaciones["id_partido"] = pd.to_datetime(
    participaciones["id_partido"]
)

historial = participaciones[
    participaciones["jugador"] == jugador
].copy()

historial["Año"] = (
    historial["id_partido"]
    .dt.year
)

evolucion = (
    historial
    .groupby("Año")
    .agg(
        PJ=("resultado_jugador", "size"),
        PG=(
            "resultado_jugador",
            lambda x: (x == "G").sum()
        )
    )
    .reset_index()
)

evolucion["WinRate"] = (
    evolucion["PG"]
    / evolucion["PJ"]
    * 100
).round(1)

st.divider()

st.subheader(
    "📈 Evolución histórica"
)

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
    yaxis=dict(
        title="Partidos / Victorias"
    ),
    yaxis2=dict(
        title="Win Rate %",
        overlaying="y",
        side="right"
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ==================================================
# ANÁLISIS DE DUPLA
# ==================================================

st.divider()

st.subheader("🤝 Analizar dupla")

companero = st.selectbox(
    "Seleccionar segundo jugador",
    sorted(
        jugadores[
            jugadores["jugador"] != jugador
        ]["jugador"].unique()
    )
)

dupla = parejas[
    (
        (parejas["jugador_1"] == jugador)
        &
        (parejas["jugador_2"] == companero)
    )
    |
    (
        (parejas["jugador_2"] == jugador)
        &
        (parejas["jugador_1"] == companero)
    )
]

if len(dupla) > 0:

    dupla = dupla.iloc[0]

    st.subheader(
        f"📊 {jugador} + {companero}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "PJ Juntos",
        int(dupla["PJ"])
    )

    c2.metric(
        "Victorias",
        int(dupla["G"])
    )

    c3.metric(
        "Empates",
        int(dupla["E"])
    )

    c4.metric(
        "Derrotas",
        int(dupla["P"])
    )

    c5.metric(
        "Win Rate",
        f"{dupla['WinRate']:.1f}%"
    )

else:

    st.warning(
        "No se encontraron partidos juntos."
    )
