import streamlit as st
import pandas as pd

equipos = pd.read_csv("equipos_master.csv")

st.title("⚽ Equipos")

equipo = st.selectbox(
    "Seleccionar equipo",
    sorted(equipos["equipo"].unique())
)

info = equipos[
    equipos["equipo"] == equipo
].iloc[0]

c1, c2, c3 = st.columns(3)

c1.metric("PJ", int(info["PJ"]))
c2.metric("Victorias", int(info["G"]))
c3.metric("Win Rate", f"{info['WinRate']}%")

st.divider()

st.write(
    f"**Jugador más presente:** {info['jugador_mas_presente']}"
)

st.write(
    f"**Mejor jugador histórico:** {info['mejor_jugador_historico']}"
)
