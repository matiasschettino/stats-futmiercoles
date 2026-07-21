import streamlit as st
import pandas as pd

# ========================
# Carga de datos
# ========================

equipos = pd.read_csv("equipos_master.csv")
participaciones = pd.read_csv("participaciones.csv")

# ========================
# Solo los 5 equipos con más partidos
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
    "Derrotas",
    int(info["P"])
)

c4.metric(
    "Win Rate",
    f"{info['WinRate']}%"
)

st.divider()

# ========================
# Información destacada
# ========================

col1, col2 = st.columns(2)

with col1:

    st.info(
        f"👑 Jugador más presente: {info['jugador_mas_presente']}"
    )

with col2:

    st.info(
        f"🏆 Mejor jugador histórico: {info['mejor_jugador_historico']}"
    )

st.divider()

# ========================
# Resumen
# ========================

resumen = pd.DataFrame({
    "Indicador": [
        "Partidos Jugados",
        "Victorias",
        "Empates",
        "Derrotas",
        "Win Rate"
    ],
    "Valor": [
        int(info["PJ"]),
        int(info["G"]),
        int(info["E"]),
        int(info["P"]),
        f"{info['WinRate']}%"
    ]
})

st.subheader("📊 Resumen del equipo")

st.dataframe(
    resumen,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ========================
# Top 10 jugadores
# ========================

top_jugadores = (
    participaciones[
        participaciones["equipo"] == equipo
    ]
    .groupby("jugador")
    .size()
    .reset_index(name="Partidos")
    .sort_values(
        "Partidos",
        ascending=False
    )
    .head(10)
)

st.subheader("👥 Top 10 jugadores con más partidos")

st.dataframe(
    top_jugadores,
    use_container_width=True,
    hide_index=True
)
