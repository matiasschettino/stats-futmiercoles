import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Stats FutMiércoles",
    page_icon="⚽",
    layout="wide"
)

jugadores = pd.read_csv("jugadores_master.csv")
equipos = pd.read_csv("equipos_master.csv")


st.title("⚽ Stats FutMiércoles")

st.markdown(
    "Estadísticas históricas de los partidos desde 2007."
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Jugadores",
    len(jugadores)
)

c2.metric(
    "Equipos",
    len(equipos)
)

c3.metric(
    "Partidos Jugados",
    int(jugadores["PJ"].max())
)

st.divider()

st.subheader("🏆 Top 10 jugadores con más partidos")

st.dataframe(
    jugadores
    .sort_values("PJ", ascending=False)
    [["jugador", "PJ", "WinRate"]]
    .head(10),
    use_container_width=True
)

st.subheader("⚽ Equipos más ganadores")

st.dataframe(
    equipos
    .sort_values("G", ascending=False)
    [["equipo", "G", "PJ", "WinRate"]]
    .head(10),
    use_container_width=True
)

#check

st.divider()

partidos = pd.read_csv(
    "partidos.csv"
)

st.subheader("Debug")

st.write(
    "Filas partidos.csv:",
    len(partidos)
)

st.write(
    "PJ máximo jugadores:",
    jugadores["PJ"].max()
)
