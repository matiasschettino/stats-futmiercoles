import streamlit as st
import pandas as pd

# ========================
# Carga de datos
# ========================

equipos = pd.read_csv("equipos_master.csv")
participaciones = pd.read_csv("participaciones.csv")

# ========================
# Solo los 5 equipos más utilizados
# ========================

equipos_top = (
    equipos
    .sort_values("PJ", ascending=False)
    .head(5)
)

# ========================
# Título
# ========================

st.title("⚽ Equipos")

# ========================
# Selector
# ========================

equipo = st.selectbox(
    "🔎 Seleccionar equipo",
    equipos_top["equipo"].tolist()
)

info = equipos_top[
    equipos_top["equipo"] == equipo
].iloc[0]

# ========================
# Encabezado
# ========================

st.header(f"⚽ {equipo}")

# ========================
# KPIs principales
# ========================

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
