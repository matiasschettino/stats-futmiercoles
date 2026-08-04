import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

st.title("🔄 Recalcular Estadísticas")

usuario = st.text_input("Usuario")

password = st.text_input(
    "Contraseña",
    type="password"
)

if (
    usuario != st.secrets["ADMIN_USER"]
    or
    password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning("Acceso restringido")
    st.stop()

supabase = get_supabase()

if st.button("🔄 Recalcular"):

    try:

        partidos = (
            supabase
            .table("partidos")
            .select("*")
            .execute()
        )

        participaciones = (
            supabase
            .table("participaciones")
            .select("*")
            .execute()
        )

        partidos_df = pd.DataFrame(
            partidos.data
        )

        participaciones_df = pd.DataFrame(
            participaciones.data
        )

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.success(
            "✅ Datos leídos correctamente"
        )

    except Exception as e:

        st.error(
            f"Error: {e}"
        )
