import streamlit as st
import pandas as pd

from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

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

st.success("✅ Acceso autorizado")

supabase = get_supabase()

# ==================================================
# BOTON
# ==================================================

if st.button("🔄 Ejecutar Chequeo"):

    try:

        # ==========================================
        # LECTURA
        # ==========================================

        partidos_df = pd.DataFrame(
            supabase
            .table("partidos")
            .select("*")
            .execute()
            .data
        )

        participaciones_df = pd.DataFrame(
            supabase
            .table("participaciones")
            .select("*")
            .execute()
            .data
        )

        jugadores_master_df = pd.DataFrame(
            supabase
            .table("jugadores_master")
            .select("*")
            .execute()
            .data
        )

        # ==========================================
        # VALIDACIONES
        # ==========================================

        st.subheader("📊 Datos leídos")

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.write(
            f"Jugadores Master: {len(jugadores_master_df)}"
        )

        # ==========================================
        # RESULTADO LOCAL
        # =========
