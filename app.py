import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION DE PAGINA
# ==================================================

st.set_page_config(
    page_title="Stats FutMiércoles",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Stats FutMiércoles")
st.markdown(
    "Estadísticas históricas de los partidos desde 2007."
)

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


def mostrar_entero(valor):
    if valor is None or pd.isna(valor):
        return 0

    return int(valor)


def mostrar_decimal(valor):
    if valor is None or pd.isna(valor):
        return 0.0

    return float(valor)


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    equipos = leer_tabla_completa("equipos_master")
    partidos = leer_tabla_completa("partidos")

except Exception as error:
    st.error("No se pudieron cargar los datos desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if equipos.empty:
    st.warning("La tabla equipos_master no contiene registros.")
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_jugadores = [
    "jugador",
    "PJ",
    "G",
    "WinRate"
]

columnas_equipos = [
    "equipo",
    "G",
    "PJ",
    "WinRate"
]

columnas_partidos = [
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

for nombre_tabla, dataframe, columnas_requeridas in [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("equipos_master", equipos, columnas_equipos),
    ("partidos", partidos, columnas_partidos)
]:
    columnas_faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in dataframe.columns
    ]

    if columnas_faltantes:
        st.error(
            f"Faltan columnas en {nombre_tabla}: "
            + ", ".join(columnas_faltantes)
        )
        st.stop()


# ==================================================
# LIMPIEZA Y NORMALIZACION
# ==================================================

for columna in ["PJ", "G", "WinRate"]:
    jugadores[columna] = pd.to_numeric(
        jugadores[columna],
        errors="coerce"
    )

for columna in ["G", "PJ", "WinRate"]:
    equipos[columna] = pd.to_numeric(
        equipos[columna],
        errors="coerce"
    )

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

jugadores = jugadores.dropna(
    subset=["jugador"]
).copy()

equipos = equipos.dropna(
    subset=["equipo"]
).copy()

partidos_validos = partidos.dropna(
    subset=[
        "fecha",
        "equipo_local",
        "equipo_visitante",
        "goles_local",
        "goles_visitante"
    ]
).copy()

# Por compatibilidad con los históricos, excluye registros marcados
# explícitamente como partidos fallidos o no jugados.
marcas_invalidas = "PARTIDO FALLIDO|NO SE JUGO|NO SE JUGÓ"

partidos_validos = partidos_validos[
    ~partidos_validos["equipo_local"]
    .astype(str)
    .str.contains(
        marcas_invalidas,
        case=False,
        na=False
    )
    &
    ~partidos_validos["equipo_visitante"]
    .astype(str)
    .str.contains(
        marcas_invalidas,
        case=False,
        na=False
    )
].copy()

if partidos_validos.empty:
    st.warning("No hay partidos válidos para mostrar.")
    st.stop()


# ==================================================
# INDICADORES PRINCIPALES
# ==================================================

ultimo_partido = partidos_validos["fecha"].max()

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Jugadores",
    len(jugadores)
)

c2.metric(
    "Equipos",
    len(equipos)
)

c3.metric(
    "Partidos Históricos",
    f"{len(partidos_validos):,}".replace(",", ".")
)

c4.metric(
    "Último Partido",
    ultimo_partido.strftime("%d/%m/%Y")
)

st.divider()


# ==================================================
# RANKINGS PRINCIPALES
# ==================================================

col_jugadores, col_equipos = st.columns(2)

with col_jugadores:
    st.subheader("🏆 Top 10 jugadores con más partidos")

    top_jugadores = (
        jugadores
        .sort_values(
            ["PJ", "G", "jugador"],
            ascending=[False, False, True]
        )
        [["jugador", "PJ", "WinRate"]]
        .head(10)
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    st.dataframe(
        top_jugadores,
        use_container_width=True,
        hide_index=True
    )

with col_equipos:
    st.subheader("⚽ Equipos más ganadores")

    top_equipos = (
        equipos
        .sort_values(
            ["G", "PJ", "WinRate", "equipo"],
            ascending=[False, False, False, True]
        )
        [["equipo", "G", "PJ", "WinRate"]]
        .head(10)
        .rename(
            columns={
                "equipo": "Equipo",
                "WinRate": "Win Rate %"
            }
        )
    )

    st.dataframe(
        top_equipos,
        use_container_width=True,
        hide_index=True
    )

st.divider()


# ==================================================
# ULTIMO PARTIDO CARGADO
# ==================================================

ultimo_registro = (
    partidos_validos
    .sort_values("fecha", ascending=False)
    .iloc[0]
)

st.subheader("🕒 Último partido cargado")

st.info(
    f"{ultimo_registro['equipo_local']} "
    f"{mostrar_entero(ultimo_registro['goles_local'])} - "
    f"{mostrar_entero(ultimo_registro['goles_visitante'])} "
    f"{ultimo_registro['equipo_visitante']} | "
    f"{ultimo_registro['fecha'].strftime('%d/%m/%Y')}"
)
