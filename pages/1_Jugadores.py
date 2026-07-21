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
# TITULO
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
# HEADER
# ==================================================

st.header(f"🏅 {jugador}")

# ==================================================
# KPIS PRINCIPALES
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


