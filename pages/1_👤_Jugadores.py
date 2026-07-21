import streamlit as st
import pandas as pd

jugadores = pd.read_csv("jugadores_master.csv")

st.title("👤 Jugadores")

jugador = st.selectbox(
    "Seleccionar jugador",
    sorted(jugadores["jugador"].unique())
)

info = jugadores[
    jugadores["jugador"] == jugador
].iloc[0]

c1, c2, c3 = st.columns(3)

c1.metric("PJ", int(info["PJ"]))
c2.metric("PG", int(info["G"]))
c3.metric("Win Rate", f"{info['WinRate']}%")

st.divider()

st.subheader("Información general")

st.write(
    f"**Equipo favorito:** {info['equipo_favorito']}"
)

st.write(
    f"**Mejor compañero:** {info['mejor_companero']}"
)

st.write(
    f"**Rival más frecuente:** {info['rival_mas_frecuente']}"
)

st.write(
    f"**Racha activa:** {info['racha_activa']}"
)

st.write(
    f"**Mejor racha histórica:** {info['mejor_racha_ganadora']}"
)
