import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("📚 Datos Curiosos")
st.markdown("Récords e hitos históricos de FutMiércoles.")

supabase = get_supabase()


# ==================================================
# FUNCIONES
# ==================================================

def leer_tabla_completa(tabla):
    registros = []
    desde = 0
    lote = 1000

    while True:
        respuesta = (
            supabase
            .table(tabla)
            .select("*")
            .range(desde, desde + lote - 1)
            .execute()
        )

        if not respuesta.data:
            break

        registros.extend(respuesta.data)

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(registros)


# ==================================================
# ACTUALIZACION MANUAL
# ==================================================

if st.button("🔄 Actualizar datos"):
    st.rerun()


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    partidos = leer_tabla_completa("partidos")
except Exception as error:
    st.error("No se pudieron leer los partidos desde Supabase.")
    st.exception(error)
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_requeridas = [
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

columnas_faltantes = [
    columna
    for columna in columnas_requeridas
    if columna not in partidos.columns
]

if columnas_faltantes:
    st.error(
        "Faltan columnas necesarias en la tabla partidos: "
        + ", ".join(columnas_faltantes)
    )
    st.stop()


# ==================================================
# LIMPIEZA
# ==================================================

partidos["fecha"] = pd.to_datetime(
    partidos["fecha"],
    errors="coerce"
)

partidos["goles_local"] = pd.to_numeric(
    partidos["goles_local"],
    errors="coerce"
)

partidos["goles_visitante"] = pd.to_numeric(
    partidos["goles_visitante"],
    errors="coerce"
)

partidos = partidos.dropna(
    subset=[
        "fecha",
        "equipo_local",
        "equipo_visitante",
        "goles_local",
        "goles_visitante"
    ]
).copy()

if partidos.empty:
    st.warning(
        "No existen partidos con información completa de fecha, equipos y goles."
    )
    st.stop()


# ==================================================
# CAMPOS CALCULADOS
# ==================================================

partidos["goles_totales"] = (
    partidos["goles_local"]
    + partidos["goles_visitante"]
)

partidos["diferencia_goles"] = (
    partidos["goles_local"]
    - partidos["goles_visitante"]
).abs()


# ==================================================
# RECORDS
# ==================================================

mas_goles = partidos.loc[
    partidos["goles_totales"].idxmax()
]

menos_goles = partidos.loc[
    partidos["goles_totales"].idxmin()
]

mayor_diferencia = partidos.loc[
    partidos["diferencia_goles"].idxmax()
]

primer_partido = partidos.loc[
    partidos["fecha"].idxmin()
]

ultimo_partido = partidos.loc[
    partidos["fecha"].idxmax()
]


# ==================================================
# KPIS
# ==================================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Partidos Históricos",
    f"{len(partidos):,}".replace(",", ".")
)

c2.metric(
    "Primer Partido",
    primer_partido["fecha"].strftime("%d/%m/%Y")
)

c3.metric(
    "Último Partido",
    ultimo_partido["fecha"].strftime("%d/%m/%Y")
)

st.divider()


# ==================================================
# PARTIDO CON MAS GOLES
# ==================================================

st.subheader("🔥 Partido con más goles")

st.success(
    f"{mas_goles['equipo_local']} "
    f"{int(mas_goles['goles_local'])} - "
    f"{int(mas_goles['goles_visitante'])} "
    f"{mas_goles['equipo_visitante']}"
)

st.write(
    f"📅 Fecha: {mas_goles['fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    f"⚽ Total de goles: {int(mas_goles['goles_totales'])}"
)

st.divider()


# ==================================================
# PARTIDO CON MENOS GOLES
# ==================================================

st.subheader("🧤 Partido con menos goles")

st.info(
    f"{menos_goles['equipo_local']} "
    f"{int(menos_goles['goles_local'])} - "
    f"{int(menos_goles['goles_visitante'])} "
    f"{menos_goles['equipo_visitante']}"
)

st.write(
    f"📅 Fecha: {menos_goles['fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    f"⚽ Total de goles: {int(menos_goles['goles_totales'])}"
)

st.divider()


# ==================================================
# MAYOR GOLEADA
# ==================================================

st.subheader("💥 Mayor diferencia de goles")

st.warning(
    f"{mayor_diferencia['equipo_local']} "
    f"{int(mayor_diferencia['goles_local'])} - "
    f"{int(mayor_diferencia['goles_visitante'])} "
    f"{mayor_diferencia['equipo_visitante']}"
)

st.write(
    f"📅 Fecha: {mayor_diferencia['fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    "📊 Diferencia: "
    f"{int(mayor_diferencia['diferencia_goles'])} goles"
)

st.divider()


# ==================================================
# ULTIMOS PARTIDOS
# ==================================================

st.subheader("🕒 Últimos partidos cargados")

ultimos_partidos = (
    partidos[
        [
            "fecha",
            "equipo_local",
            "goles_local",
            "goles_visitante",
            "equipo_visitante"
        ]
    ]
    .sort_values("fecha", ascending=False)
    .head(10)
    .copy()
)

ultimos_partidos["fecha"] = (
    ultimos_partidos["fecha"]
    .dt.strftime("%d/%m/%Y")
)

ultimos_partidos = ultimos_partidos.rename(
    columns={
        "fecha": "Fecha",
        "equipo_local": "Local",
        "goles_local": "GL",
        "goles_visitante": "GV",
        "equipo_visitante": "Visitante"
    }
)

st.dataframe(
    ultimos_partidos,
    use_container_width=True,
    hide_index=True
)

st.divider()


# ==================================================
# TABLA RESUMEN
# ==================================================

st.subheader("🏆 Resumen de récords")

resumen = pd.DataFrame(
    {
        "Récord": [
            "Partido con más goles",
            "Partido con menos goles",
            "Mayor diferencia de goles"
        ],
        "Partido": [
            (
                f"{mas_goles['equipo_local']} "
                f"{int(mas_goles['goles_local'])} - "
                f"{int(mas_goles['goles_visitante'])} "
                f"{mas_goles['equipo_visitante']}"
            ),
            (
                f"{menos_goles['equipo_local']} "
                f"{int(menos_goles['goles_local'])} - "
                f"{int(menos_goles['goles_visitante'])} "
                f"{menos_goles['equipo_visitante']}"
            ),
            (
                f"{mayor_diferencia['equipo_local']} "
                f"{int(mayor_diferencia['goles_local'])} - "
                f"{int(mayor_diferencia['goles_visitante'])} "
                f"{mayor_diferencia['equipo_visitante']}"
            )
        ],
        "Valor": [
            int(mas_goles["goles_totales"]),
            int(menos_goles["goles_totales"]),
            int(mayor_diferencia["diferencia_goles"])
        ],
        "Fecha": [
            mas_goles["fecha"].strftime("%d/%m/%Y"),
            menos_goles["fecha"].strftime("%d/%m/%Y"),
            mayor_diferencia["fecha"].strftime("%d/%m/%Y")
        ]
    }
)

st.dataframe(
    resumen,
    use_container_width=True,
    hide_index=True
)
