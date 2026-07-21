import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("🔒 Administración")

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
# CONEXIÓN SUPABASE
# ==================================================

supabase = get_supabase()

# ==================================================
# CARGA DE DATOS
# ==================================================

equipos = (
    supabase
    .table("equipos")
    .select("*")
    .execute()
)

jugadores = (
    supabase
    .table("jugadores")
    .select("*")
    .execute()
)

equipos_df = pd.DataFrame(equipos.data)
jugadores_df = pd.DataFrame(jugadores.data)

lista_equipos = []

if not equipos_df.empty:

    lista_equipos = sorted(
        equipos_df["equipo"]
        .dropna()
        .tolist()
    )

lista_jugadores = []

if not jugadores_df.empty:

    lista_jugadores = sorted(
        jugadores_df["jugador"]
        .dropna()
        .tolist()
    )

# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "⚽ Equipos",
        "👤 Jugadores",
        "🏆 Cargar Partido",
        "📋 Partidos"
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

    nuevo_equipo = st.text_input(
        "Nuevo equipo"
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
                "Equipo guardado"
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

    nuevo_jugador = st.text_input(
        "Nuevo jugador"
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
                "Jugador guardado"
            )

            st.rerun()

# ==================================================
# CARGAR PARTIDO
# ==================================================

with tab3:

    st.subheader("🏆 Nuevo Partido")

    fecha = st.date_input(
        "Fecha del partido"
    )

    col1, col2 = st.columns(2)

    with col1:

        equipo_local = st.selectbox(
            "Equipo Local",
            lista_equipos,
            key="equipo_local"
        )

        goles_local = st.number_input(
            "Goles Local",
            min_value=0,
            value=0,
            step=1
        )

        jugadores_local = st.multiselect(
            "Jugadores Local",
            lista_jugadores,
            key="jugadores_local"
        )

    with col2:

        equipo_visitante = st.selectbox(
            "Equipo Visitante",
            lista_equipos,
            index=1 if len(lista_equipos) > 1 else 0,
            key="equipo_visitante"
        )

        goles_visitante = st.number_input(
            "Goles Visitante",
            min_value=0,
            value=0,
            step=1
        )

        jugadores_visitante = st.multiselect(
            "Jugadores Visitante",
            lista_jugadores,
            key="jugadores_visitante"
        )

    st.divider()

    if st.button("Guardar Partido"):

        if equipo_local == equipo_visitante:

            st.error(
                "Los equipos deben ser distintos."
            )

            st.stop()

        if len(jugadores_local) == 0:

            st.error(
                "Seleccioná jugadores para el equipo local."
            )

            st.stop()

        if len(jugadores_visitante) == 0:

            st.error(
                "Seleccioná jugadores para el equipo visitante."
            )

            st.stop()

        repetidos = (
            set(jugadores_local)
            &
            set(jugadores_visitante)
        )

        if len(repetidos) > 0:

            st.error(
                f"Hay jugadores repetidos: {', '.join(repetidos)}"
            )

            st.stop()

        partido = (
            supabase
            .table("partidos")
            .insert(
                {
                    "fecha": str(fecha),
                    "equipo_local": equipo_local,
                    "goles_local": goles_local,
                    "equipo_visitante": equipo_visitante,
                    "goles_visitante": goles_visitante
                }
            )
            .execute()
        )

        partido_id = partido.data[0]["id"]

        registros = []

        for jugador in jugadores_local:

            registros.append(
                {
                    "partido_id": partido_id,
                    "jugador": jugador,
                    "equipo": equipo_local
                }
            )

        for jugador in jugadores_visitante:

            registros.append(
                {
                    "partido_id": partido_id,
                    "jugador": jugador,
                    "equipo": equipo_visitante
                }
            )

        (
            supabase
            .table("participaciones")
            .insert(registros)
            .execute()
        )

        st.success(
            "✅ Partido guardado correctamente"
        )

        st.balloons()

# ==================================================
# PARTIDOS CARGADOS
# ==================================================

with tab4:

    st.subheader("📋 Partidos cargados")

    partidos = (
        supabase
        .table("partidos")
        .select("*")
        .execute()
    )

    partidos_df = pd.DataFrame(
        partidos.data
    )

    if partidos_df.empty:

        st.info(
            "No hay partidos cargados."
        )

    else:

        partidos_df["fecha"] = pd.to_datetime(
            partidos_df["fecha"]
        )

        partidos_df = (
            partidos_df
            .sort_values(
                "fecha",
                ascending=False
            )
        )

        fecha_min = partidos_df["fecha"].min().date()
        fecha_max = partidos_df["fecha"].max().date()

        col1, col2 = st.columns(2)

        with col1:

            fecha_desde = st.date_input(
                "Desde",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max
            )

        with col2:

            fecha_hasta = st.date_input(
                "Hasta",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max
            )

        partidos_filtrados = partidos_df[
            (
                partidos_df["fecha"].dt.date
                >= fecha_desde
            )
            &
            (
                partidos_df["fecha"].dt.date
                <= fecha_hasta
            )
        ].copy()

        st.dataframe(
            partidos_filtrados[
                [
                    "fecha",
                    "equipo_local",
                    "goles_local",
                    "goles_visitante",
                    "equipo_visitante"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        if partidos_filtrados.empty:

            st.warning(
                "No hay partidos para ese rango de fechas."
            )

        else:

            partidos_filtrados["descripcion"] = (
                partidos_filtrados["fecha"]
                .dt.strftime("%d/%m/%Y")
                + " | "
                + partidos_filtrados["equipo_local"]
                + " "
                + partidos_filtrados["goles_local"].astype(str)
                + " - "
                + partidos_filtrados["goles_visitante"].astype(str)
                + " "
                + partidos_filtrados["equipo_visitante"]
            )

            st.divider()

            partido_seleccionado = st.selectbox(
                "Seleccionar partido",
                partidos_filtrados["descripcion"]
            )

            partido = partidos_filtrados[
                partidos_filtrados["descripcion"]
                ==
                partido_seleccionado
            ].iloc[0]

            partido_id = partido["id"]

            st.subheader("⚽ Detalle del partido")

            st.write(
                f"**{partido['equipo_local']} "
                f"{int(partido['goles_local'])} - "
                f"{int(partido['goles_visitante'])} "
                f"{partido['equipo_visitante']}**"
            )

            st.write(
                f"📅 {partido['fecha'].strftime('%d/%m/%Y')}"
            )

            participaciones = (
                supabase
                .table("participaciones")
                .select("*")
                .eq(
                    "partido_id",
                    partido_id
                )
                .execute()
            )

            participaciones_df = pd.DataFrame(
                participaciones.data
            )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"### {partido['equipo_local']}"
                )

                jugadores_local = (
                    participaciones_df[
                        participaciones_df["equipo"]
                        ==
                        partido["equipo_local"]
                    ]["jugador"]
                    .tolist()
                )

                for jugador in jugadores_local:

                    st.write(
                        f"• {jugador}"
                    )

            with col2:

                st.markdown(
                    f"### {partido['equipo_visitante']}"
                )

                jugadores_visitante = (
                    participaciones_df[
                        participaciones_df["equipo"]
                        ==
                        partido["equipo_visitante"]
                    ]["jugador"]
                    .tolist()
                )

                for jugador in jugadores_visitante:

                    st.write(
                        f"• {jugador}"
                    )

            st.divider()

            if st.button(
                "🗑️ Eliminar partido seleccionado",
                type="primary"
            ):

                (
                    supabase
                    .table("participaciones")
                    .delete()
                    .eq(
                        "partido_id",
                        partido_id
                    )
                    .execute()
                )

                (
                    supabase
                    .table("partidos")
                    .delete()
                    .eq(
                        "id",
                        partido_id
                    )
                    .execute()
                )

                st.success(
                    "✅ Partido eliminado correctamente"
                )

                st.rerun()
