import streamlit as st
import pandas as pd

jugadores = pd.read_csv("jugadores_master.csv")

st.title("🏆 Rankings")

tab1, tab2, tab3 = st.tabs(
    [
        "Más partidos",
        "Más victorias",
        "Mejor Win Rate"
    ]
)

with tab1:

    st.dataframe(
        jugadores
        .sort_values(
            "PJ",
            ascending=False
        )
        .head(20)
    )

with tab2:

    st.dataframe(
        jugadores
        .sort_values(
            "G",
            ascending=False
        )
        .head(20)
    )

with tab3:

    st.dataframe(
        jugadores[
            jugadores["PJ"] >= 50
        ]
        .sort_values(
            "WinRate",
            ascending=False
        )
        .head(20)
    )
