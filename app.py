import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Futbol Stats",
    page_icon="⚽",
    layout="wide"
)

jugadores = pd.read_csv(
    "jugadores_master.csv"
)

equipos = pd.read_csv(
    "equipos_master.csv"
)

st.title("⚽ Fútbol Histórico")

col1, col2 = st.columns(2)

col1.metric(
    "Jugadores",
    len(jugadores)
)

col2.metric(
    "Equipos",
    len(equipos)
)

st.subheader(
    "🏆 Top 20 jugadores con más partidos"
)

st.dataframe(
    jugadores
    .sort_values("PJ", ascending=False)
    .head(20)
)
