import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

st.title("📥 Importar Históricos")

supabase = get_supabase()

participaciones = pd.read_csv(
    "participaciones.csv"
)

jugadores_historicos = sorted(
    participaciones["jugador"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

equipos_historicos = sorted(
    participaciones["equipo"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

st.write(
    f"Jugadores encontrados: {len(jugadores_historicos)}"
)

st.write(
    f"Equipos encontrados: {len(equipos_historicos)}"
)

if st.button("Importar Jugadores"):

    actuales = (
        supabase
        .table("jugadores")
        .select("jugador")
        .execute()
    )

    existentes = {
        x["jugador"].strip().upper()
        for x in actuales.data
    }

    nuevos = 0

    for jugador in jugadores_historicos:

        nombre = jugador.strip()

        if nombre.upper() not in existentes:

            supabase.table(
                "jugadores"
            ).insert(
                {
                    "jugador": nombre
                }
            ).execute()

            nuevos += 1

    st.success(
        f"{nuevos} jugadores importados"
    )

if st.button("Importar Equipos"):

    actuales = (
        supabase
        .table("equipos")
        .select("equipo")
        .execute()
    )

    existentes = {
        x["equipo"].strip().upper()
        for x in actuales.data
    }

    nuevos = 0

    for equipo in equipos_historicos:

        nombre = equipo.strip()

        if nombre.upper() not in existentes:

            supabase.table(
                "equipos"
            ).insert(
                {
                    "equipo": nombre
                }
            ).execute()

            nuevos += 1

    st.success(
        f"{nuevos} equipos importados"
    )
