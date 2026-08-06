import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("⚽ Equipos")

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


def entero_seguro(valor):
    if valor is None or pd.isna(valor):
        return 0

    return int(valor)


def decimal_seguro(valor):
    if valor is None or pd.isna(valor):
        return 0.0

    return float(valor)


def texto_seguro(valor, reemplazo="Sin datos"):
    if valor is None or pd.isna(valor) or str(valor).strip() == "":
        return reemplazo

    return str(valor)


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    equipos = leer_tabla_completa("equipos_master")
    participaciones = leer_tabla_completa("participaciones")
    partidos = leer_tabla_completa("partidos")

except Exception as error:
    st.error("No se pudieron leer los datos desde Supabase.")
    st.exception(error)
    st.stop()


if equipos.empty:
    st.warning("La tabla equipos_master no contiene registros.")
    st.stop()

if participaciones.empty:
    st.warning("La tabla participaciones no contiene registros.")
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_equipos = [
    "equipo",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate",
    "jugador_mas_presente",
    "pj_jugador_mas_presente",
    "mejor_jugador_historico",
    "pj_mejor_jugador",
    "wr_mejor_jugador"
]

columnas_participaciones = [
    "partido_id",
    "jugador",
    "equipo"
]

columnas_partidos = [
    "id",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

for nombre_tabla, dataframe, columnas_requeridas in [
    ("equipos_master", equipos, columnas_equipos),
    ("participaciones", participaciones, columnas_participaciones),
    ("partidos", partidos, columnas_partidos)
]:
    faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in dataframe.columns
    ]

    if faltantes:
        st.error(
            f"Faltan columnas en {nombre_tabla}: "
            + ", ".join(faltantes)
        )
        st.stop()


# ==================================================
# NORMALIZACION
# ==================================================

for columna in [
    "PJ",
    "G",
    "E",
    "P",
    "pj_jugador_mas_presente",
    "pj_mejor_jugador"
]:
    equipos[columna] = pd.to_numeric(
        equipos[columna],
        errors="coerce"
    )

for columna in [
    "WinRate",
    "wr_mejor_jugador"
]:
    equipos[columna] = pd.to_numeric(
        equipos[columna],
        errors="coerce"
    )

participaciones = participaciones.dropna(
    subset=["jugador", "equipo", "partido_id"]
).copy()

partidos["goles_local"] = pd.to_numeric(
    partidos["goles_local"],
    errors="coerce"
)

partidos["goles_visitante"] = pd.to_numeric(
    partidos["goles_visitante"],
    errors="coerce"
)

partidos["resultado_local"] = "E"

partidos.loc[
    partidos["goles_local"] > partidos["goles_visitante"],
    "resultado_local"
] = "G"

partidos.loc[
    partidos["goles_local"] < partidos["goles_visitante"],
    "resultado_local"
] = "P"

participaciones_resultados = participaciones.merge(
    partidos[
        [
            "id",
            "equipo_local",
            "equipo_visitante",
            "resultado_local"
        ]
    ],
    left_on="partido_id",
    right_on="id",
    how="left",
    suffixes=("", "_partido")
)

participaciones_resultados["resultado_jugador"] = ""

mask_local = (
    participaciones_resultados["equipo"]
    == participaciones_resultados["equipo_local"]
)

mask_visitante = (
    participaciones_resultados["equipo"]
    == participaciones_resultados["equipo_visitante"]
)

participaciones_resultados.loc[
    mask_local,
    "resultado_jugador"
] = participaciones_resultados["resultado_local"]

participaciones_resultados.loc[
    mask_visitante
    & (participaciones_resultados["resultado_local"] == "G"),
    "resultado_jugador"
] = "P"

participaciones_resultados.loc[
    mask_visitante
    & (participaciones_resultados["resultado_local"] == "P"),
    "resultado_jugador"
] = "G"

participaciones_resultados.loc[
    mask_visitante
    & (participaciones_resultados["resultado_local"] == "E"),
    "resultado_jugador"
] = "E"

participaciones_resultados = participaciones_resultados[
    participaciones_resultados["resultado_jugador"].isin(["G", "E", "P"])
].copy()


# ==================================================
# SOLO LOS 5 EQUIPOS CON MAS PARTIDOS
# ==================================================

equipos_top = (
    equipos
    .dropna(subset=["equipo"])
    .sort_values(
        ["PJ", "equipo"],
        ascending=[False, True]
    )
    .head(5)
    .copy()
)

if equipos_top.empty:
    st.warning("No hay equipos disponibles para mostrar.")
    st.stop()


# ==================================================
# SELECTOR
# ==================================================

equipo = st.selectbox(
    "🔎 Seleccionar equipo",
    equipos_top["equipo"].astype(str).tolist(),
    index=None,
    placeholder="Seleccioná un equipo..."
)

if equipo is None:
    st.info("Seleccioná un equipo para ver sus estadísticas.")
    st.stop()

filas_equipo = equipos_top[
    equipos_top["equipo"] == equipo
]

if filas_equipo.empty:
    st.warning("No se encontraron datos para el equipo seleccionado.")
    st.stop()

info = filas_equipo.iloc[0]


# ==================================================
# ENCABEZADO
# ==================================================

st.header(f"⚽ {equipo}")


# ==================================================
# KPIS PRINCIPALES
# ==================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "PJ",
    entero_seguro(info.get("PJ"))
)

c2.metric(
    "Victorias",
    entero_seguro(info.get("G"))
)

c3.metric(
    "Derrotas",
    entero_seguro(info.get("P"))
)

c4.metric(
    "Win Rate",
    f"{decimal_seguro(info.get('WinRate')):.1f}%"
)

st.divider()


# ==================================================
# INFORMACION DESTACADA
# ==================================================

col1, col2 = st.columns(2)

with col1:
    st.info(
        "👑 Jugador más presente: "
        f"{texto_seguro(info.get('jugador_mas_presente'))} "
        f"({entero_seguro(info.get('pj_jugador_mas_presente'))} PJ)"
    )

with col2:
    mejor_jugador = texto_seguro(
        info.get("mejor_jugador_historico")
    )

    if mejor_jugador == "Sin datos":
        st.info(
            "🏆 Mejor jugador histórico: Sin datos "
            "(se requieren al menos 20 partidos)"
        )
    else:
        st.info(
            "🏆 Mejor jugador histórico: "
            f"{mejor_jugador} "
            f"({entero_seguro(info.get('pj_mejor_jugador'))} PJ, "
            f"{decimal_seguro(info.get('wr_mejor_jugador')):.1f}% WR)"
        )

st.divider()


# ==================================================
# RESUMEN
# ==================================================

resumen = pd.DataFrame(
    {
        "Indicador": [
            "Partidos Jugados",
            "Victorias",
            "Empates",
            "Derrotas",
            "Win Rate"
        ],
        "Valor": [
            entero_seguro(info.get("PJ")),
            entero_seguro(info.get("G")),
            entero_seguro(info.get("E")),
            entero_seguro(info.get("P")),
            f"{decimal_seguro(info.get('WinRate')):.1f}%"
        ]
    }
)

st.subheader("📊 Resumen del equipo")

st.dataframe(
    resumen,
    use_container_width=True,
    hide_index=True
)

st.divider()


# ==================================================
# TOP 10 JUGADORES
# ==================================================

top_jugadores = (
    participaciones[
        participaciones["equipo"] == equipo
    ]
    .groupby("jugador")
    .size()
    .reset_index(name="Partidos")
    .sort_values(
        ["Partidos", "jugador"],
        ascending=[False, True]
    )
    .head(10)
    .rename(
        columns={
            "jugador": "Jugador"
        }
    )
)

st.subheader("👥 Top 10 jugadores con más partidos")

if top_jugadores.empty:
    st.info("No hay participaciones registradas para este equipo.")
else:
    st.dataframe(
        top_jugadores,
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ==================================================
# RANKINGS DE JUGADORES DEL EQUIPO
# Minimo 20 partidos
# ==================================================

rendimiento_equipo = (
    participaciones_resultados[
        participaciones_resultados["equipo"] == equipo
    ]
    .pivot_table(
        index="jugador",
        columns="resultado_jugador",
        aggfunc="size",
        fill_value=0
    )
    .reset_index()
)

rendimiento_equipo.columns.name = None

for columna in ["G", "E", "P"]:
    if columna not in rendimiento_equipo.columns:
        rendimiento_equipo[columna] = 0

rendimiento_equipo["PJ"] = (
    rendimiento_equipo["G"]
    + rendimiento_equipo["E"]
    + rendimiento_equipo["P"]
)

rendimiento_equipo["WinRate"] = (
    rendimiento_equipo["G"]
    / rendimiento_equipo["PJ"].replace(0, pd.NA)
    * 100
).round(1).fillna(0)

rendimiento_relevante = rendimiento_equipo[
    rendimiento_equipo["PJ"] >= 20
].copy()

col_ganadores, col_perdedores = st.columns(2)

with col_ganadores:
    st.subheader("🏆 Top 10 más ganadores")

    top_ganadores = (
        rendimiento_relevante
        .sort_values(
            ["WinRate", "PJ", "G", "jugador"],
            ascending=[False, False, False, True]
        )
        .head(10)
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    if top_ganadores.empty:
        st.info(
            "No hay jugadores con al menos 20 partidos en este equipo."
        )
    else:
        st.dataframe(
            top_ganadores,
            use_container_width=True,
            hide_index=True
        )

with col_perdedores:
    st.subheader("📉 Top 10 más perdedores")

    top_perdedores = (
        rendimiento_relevante
        .sort_values(
            ["WinRate", "PJ", "P", "jugador"],
            ascending=[True, False, False, True]
        )
        .head(10)
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .rename(
            columns={
                "jugador": "Jugador",
                "WinRate": "Win Rate %"
            }
        )
    )

    if top_perdedores.empty:
        st.info(
            "No hay jugadores con al menos 20 partidos en este equipo."
        )
    else:
        st.dataframe(
            top_perdedores,
            use_container_width=True,
            hide_index=True
        )

