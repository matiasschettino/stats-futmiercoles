import streamlit as st
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("🛡️ Gestión de Backups")

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
# BACKUP
# ==================================================

st.subheader("📦 Crear Backup")

st.info(
    "Genera una copia de seguridad de las tablas master actuales."
)

if st.button("📦 Crear Backup"):

    try:

        # ------------------------------------------
        # JUGADORES MASTER
        # ------------------------------------------

        jugadores_master = (
            supabase
            .table("jugadores_master")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("jugadores_master_backup")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(jugadores_master.data) > 0:

            (
                supabase
                .table("jugadores_master_backup")
                .insert(
                    jugadores_master.data
                )
                .execute()
            )

        # ------------------------------------------
        # EQUIPOS MASTER
        # ------------------------------------------

        equipos_master = (
            supabase
            .table("equipos_master")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("equipos_master_backup")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(equipos_master.data) > 0:

            (
                supabase
                .table("equipos_master_backup")
                .insert(
                    equipos_master.data
                )
                .execute()
            )

        # ------------------------------------------
        # PAREJAS MASTER
        # ------------------------------------------

        parejas_master = (
            supabase
            .table("estadisticas_parejas")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("estadisticas_parejas_backup")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(parejas_master.data) > 0:

            (
                supabase
                .table("estadisticas_parejas_backup")
                .insert(
                    parejas_master.data
                )
                .execute()
            )

        st.success(
            "✅ Backup creado correctamente"
        )

    except Exception as e:

        st.error(
            f"Error creando backup: {e}"
        )

# ==================================================
# RESTAURAR BACKUP
# ==================================================

st.divider()

st.subheader("↩️ Restaurar Backup")

st.warning(
    "Esta acción reemplazará las tablas master actuales por la última copia de seguridad."
)

if st.button(
    "↩️ Restaurar Backup",
    type="primary"
):

    try:

        # ------------------------------------------
        # JUGADORES
        # ------------------------------------------

        jugadores_backup = (
            supabase
            .table("jugadores_master_backup")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("jugadores_master")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(jugadores_backup.data) > 0:

            (
                supabase
                .table("jugadores_master")
                .insert(
                    jugadores_backup.data
                )
                .execute()
            )

        # ------------------------------------------
        # EQUIPOS
        # ------------------------------------------

        equipos_backup = (
            supabase
            .table("equipos_master_backup")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("equipos_master")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(equipos_backup.data) > 0:

            (
                supabase
                .table("equipos_master")
                .insert(
                    equipos_backup.data
                )
                .execute()
            )

        # ------------------------------------------
        # PAREJAS
        # ------------------------------------------

        parejas_backup = (
            supabase
            .table("estadisticas_parejas_backup")
            .select("*")
            .execute()
        )

        (
            supabase
            .table("estadisticas_parejas")
            .delete()
            .neq("id", "")
            .execute()
        )

        if len(parejas_backup.data) > 0:

            (
                supabase
                .table("estadisticas_parejas")
                .insert(
                    parejas_backup.data
                )
                .execute()
            )

        st.success(
            "✅ Backup restaurado correctamente"
        )

    except Exception as e:

        st.error(
            f"Error restaurando backup: {e}"
        )
