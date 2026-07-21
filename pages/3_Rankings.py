import streamlit as st
import pandas as pd

# =====================================
# CARGA DE DATOS
# =====================================

jugadores = pd.read_csv("jugadores_master.csv")
equipos = pd.read_csv("equipos_master.csv")
parejas = pd.read_csv("estadisticas_parejas.csv")

# =====================================
# TÍTULO
# =====================================

st.title("🏆 Rankings")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "🏃 Más partidos",
        "🥇 Más victorias",
        "📈 Mejor Win Rate",
        "🔥 Rachas activas",
        "⚽ Equipos",
        "🤝 Mejores duplas"
    ]
)

# =====================================
# MÁS PARTIDOS
# =====================================

with tab1:

    st.subheader("Top 20 jugadores con más partidos")

    ranking = (
        jugadores
        .sort_values(
            "PJ",
            ascending=False
        )
        [["jugador", "PJ", "WinRate"]]
        .head(20)
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

# =====================================
# MÁS VICTORIAS
# =====================================

with tab2:

    st.subheader("Top 20 jugadores con más victorias")

    ranking = (
        jugadores
        .sort_values(
            "G",
            ascending=False
        )
        [["jugador", "G", "PJ", "WinRate"]]
        .head(20)
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

# =====================================
# MEJOR WIN RATE
# =====================================

with tab3:

    st.subheader(
        "Top 20 Win Rate (mínimo 50 partidos)"
    )

    ranking = (
        jugadores[
            jugadores["PJ"] >= 50
        ]
        .sort_values(
            "WinRate",
            ascending=False
        )
        [["jugador", "PJ", "WinRate"]]
        .head(20)
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

# =====================================
# RACHAS ACTIVAS
# =====================================

with tab4:

    st.subheader("Top 20 rachas activas")

    ranking = (
        jugadores
        .sort_values(
            "racha_activa",
            ascending=False
        )
        [["jugador", "racha_activa", "WinRate"]]
        .head(20)
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

# =====================================
# EQUIPOS MÁS GANADORES
# =====================================

with tab5:

    st.subheader("Equipos más ganadores")

    ranking = (
        equipos
        .sort_values(
            "G",
            ascending=False
        )
        [["equipo", "G", "PJ", "WinRate"]]
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )

# =====================================
# MEJORES DUPLAS
# =====================================

with tab6:

    st.subheader(
        "Mejores duplas históricas (mínimo 50 partidos juntos)"
    )

    ranking = (
        parejas[
            parejas["PJ"] >= 50
        ]
        .sort_values(
            "WinRate",
            ascending=False
        )
        [[
            "jugador_1",
            "jugador_2",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate"
        ]]
        .head(30)
    )

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )
