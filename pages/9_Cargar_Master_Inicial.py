import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("📤 Cargar Master Inicial")

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

# ==================================================
# CONEXIÓN
# ==================================================

supabase = get_supabase()

# ==================================================
# LEER CSV
# ==================================================

jugadores_master = pd.read_csv(
    "jugadores_master.csv"
)

equipos_master = pd.read_csv(
    "equipos_master.csv"
)

estadisticas_parejas = pd.read_csv(
    "estadisticas_parejas.csv"
)

# ==================================================
# VALIDACIÓN
# ==================================================

st.subheader("📊 Resumen de archivos")

st.write(
    f"Jugadores Master: {len(jugadores_master)}"
)

st.write(
    f"Equipos Master: {len(equipos_master)}"
)

st.write(
    f"Parejas: {len(estadisticas_parejas)}"
)

st.divider()

st.subheader("🔎 Columnas detectadas")

st.write(
    "Jugadores:",
    jugadores_master.columns.tolist()
)

st.write(
    "Equipos:",
    equipos_master.columns.tolist()
)

st.write(
    "Parejas:",
    estadisticas_parejas.columns.tolist()
)

st.divider()

# ==================================================
# CARGA
# ==================================================

if st.button("📤 Cargar Master Inicial"):

    try:

        # ------------------------------------------
        # JUGADORES
        # ------------------------------------------

