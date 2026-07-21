import streamlit as st
import pandas as pd

# ========================
# Carga de datos
# ========================

jugadores = pd.read_csv("jugadores_master.csv")

# ========================
# Título
# ========================

st.title("👤 Jugadores")

# ========================
# Buscador
# ========================

jugador = st.selectbox(
    "🔎 Buscar jugador",
    sorted(jugadores["jugador"].unique()),
    index=None,
    placeholder="Escribí el nombre del jugador..."
)

if jugador is None:
    st.info("Seleccioná un jugador para ver sus estadísticas.")
    st.stop()

# ========================
# Datos del jugador
# ========================

info = jugadores[
    jugadores["jugador"] == jugador
].iloc[0]

# ========================
# Encabezado
# ========================

st.header(f"🏅 {jugador}")

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
# Segunda fila de KPIs
# ========================

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

# ========================
# Información destacada
# ========================

c1, c2 = st.columns(2)

with c1:

    st.info(
        f"🏟️ Equipo favorito: **{info['equipo_favorito']}**"
    )

    st.info(
        f"🤝 Mejor compañero: **{info['mejor_companero']}**"
    )

with c2:

    st.info(
        f"🥊 Rival más frecuente: **{info['rival_mas_frecuente']}**"
    )

    st.info(
        f"🔥 Mejor racha histórica: **{info['mejor_racha_ganadora']} victorias**"
    )

st.divider()

# ========================
# Resumen estadístico
# ========================

st.subheader("📊 Resumen")

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

st.dataframe(
    resumen,
    use_container_width=True,
    hide_index=True
)
