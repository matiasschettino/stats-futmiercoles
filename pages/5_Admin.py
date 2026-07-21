import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("🔒 Administración")

usuario = st.text_input(
    "Usuario"
)

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
# CONEXIÓN SUPABASE
# ==================================================

supabase = get_supabase()

# ==================================================
# CARGAR DATOS
# ==================================================

equipos = (
    supabase
    .table("equipos")
    .select("*")
    .execute()
)

equipos_df = pd.DataFrame(equipos.data)

jugadores = (
    supabase
    .table("jugadores")
    .select("*")
    .execute()
)

jugadores_df = pd.DataFrame(jugadores.data)

# ==================================================
# TABS
# ==================================================

tab1, tab2 = st.tabs(
    [
        "⚽ Equipos",
        "👤 Jugadores"
    ]
)

# ==================================================
# EQUIPOS
# ==================================================

with tab1:

    st.subheader("Equipos registrados")

    if not equipos_df.empty:

        st.dataframe(
            equipos_df[["equipo"]],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("➕ Nuevo equipo")

    nuevo_equipo = st.text_input(
        "Nombre del equipo"
    )

    if st.button("Guardar Equipo"):

        if nuevo_equipo.strip() == "":
            st.error(
                "Ingresá un nombre válido"
            )

        else:

            supabase.table(
                "equipos"
            ).insert(
                {
                    "equipo": nuevo_equipo.strip()
                }
            ).execute()

            st.success(
                "Equipo guardado correctamente"
            )

            st.rerun()

# ==================================================
# JUGADORES
# ==================================================

with tab2:

    st.subheader("Jugadores registrados")

    if not jugadores_df.empty:

        st.dataframe(
            jugadores_df[["jugador"]],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("➕ Nuevo jugador")

    nuevo_jugador = st.text_input(
        "Nombre del jugador"
    )

    if st.button("Guardar Jugador"):

        if nuevo_jugador.strip() == "":

            st.error(
                "Ingresá un nombre válido"
            )

        else:

            supabase.table(
                "jugadores"
            ).insert(
                {
                    "jugador": nuevo_jugador.strip()
                }
            ).execute()

            st.success(
                "Jugador guardado correctamente"
            )

            st.rerun()
