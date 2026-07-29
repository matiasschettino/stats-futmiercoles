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
# FUNCIONES
# ==================================================

def vaciar_tabla(nombre_tabla):

    filas = (
        supabase
        .table(nombre_tabla)
        .select("id")
        .execute()
    )

    if filas.data:

        ids = [
            fila["id"]
            for fila in filas.data
        ]

        (
            supabase
            .table(nombre_tabla)
            .delete()
            .in_("id", ids)
            .execute()
        )


def limpiar_ids(registros):

    registros_limpios = []

    for registro in registros:

        nuevo = registro.copy()

        if "id" in nuevo:
            del nuevo["id"]

        registros_limpios.append(nuevo)

    return registros_limpios

# ==================================================
# CREAR BACKUP
# ==================================================

st.subheader("📦 Crear Backup")

if st.button("📦 Crear Backup"):

    try:

        # -----------------------------
        # JUGADORES
        # -----------------------------

        jugadores = (
            supabase
            .table("jugadores_master")
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "jugadores_master_backup"
        )

        registros = limpiar_ids(
            jugadores.data
        )

        if registros:

            (
                supabase
                .table(
                    "jugadores_master_backup"
                )
                .insert(registros)
                .execute()
            )

        # -----------------------------
        # EQUIPOS
        # -----------------------------

        equipos = (
            supabase
            .table("equipos_master")
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "equipos_master_backup"
        )

        registros = limpiar_ids(
            equipos.data
        )

        if registros:

            (
                supabase
                .table(
                    "equipos_master_backup"
                )
                .insert(registros)
                .execute()
            )

        # -----------------------------
        # PAREJAS
        # -----------------------------

        parejas = (
            supabase
            .table("estadisticas_parejas")
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "estadisticas_parejas_backup"
        )

        registros = limpiar_ids(
            parejas.data
        )

        if registros:

            (
                supabase
                .table(
                    "estadisticas_parejas_backup"
                )
                .insert(registros)
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
    "Esta acción reemplazará las tablas master actuales por el backup."
)

if st.button(
    "↩️ Restaurar Backup",
    type="primary"
):

    try:

        # -----------------------------
        # JUGADORES
        # -----------------------------

        jugadores_backup = (
            supabase
            .table(
                "jugadores_master_backup"
            )
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "jugadores_master"
        )

        registros = limpiar_ids(
            jugadores_backup.data
        )

        if registros:

            (
                supabase
                .table(
                    "jugadores_master"
                )
                .insert(registros)
                .execute()
            )

        # -----------------------------
        # EQUIPOS
        # -----------------------------

        equipos_backup = (
            supabase
            .table(
                "equipos_master_backup"
            )
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "equipos_master"
        )

        registros = limpiar_ids(
            equipos_backup.data
        )

        if registros:

            (
                supabase
                .table(
                    "equipos_master"
                )
                .insert(registros)
                .execute()
            )

        # -----------------------------
        # PAREJAS
        # -----------------------------

        parejas_backup = (
            supabase
            .table(
                "estadisticas_parejas_backup"
            )
            .select("*")
            .execute()
        )

        vaciar_tabla(
            "estadisticas_parejas"
        )

        registros = limpiar_ids(
            parejas_backup.data
        )

        if registros:

            (
                supabase
                .table(
                    "estadisticas_parejas"
                )
                .insert(registros)
                .execute()
            )

        st.success(
            "✅ Backup restaurado correctamente"
        )

    except Exception as e:

        st.error(
            f"Error restaurando backup: {e}"
        )
