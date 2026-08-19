import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("📚 Datos Curiosos")
st.markdown("Récords e hitos históricos de FutMiércoles.")

supabase = get_supabase()

st.markdown(
    """
    <style>
    .curiosity-card {
        background-color: #14304a;
        border-radius: 10px;
        padding: 22px 18px;
        min-height: 200px;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        color: #2D9CFF;
        box-sizing: border-box;
    }
    .curiosity-card-title {
        font-size: 18px;
        line-height: 1.35;
        font-weight: 600;
        margin-bottom: 12px;
    }
    .curiosity-card-main {
        font-size: 18px;
        line-height: 1.35;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .curiosity-card-detail {
        font-size: 18px;
        line-height: 1.35;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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


def numero_formato(valor):
    return f"{entero_seguro(valor):,}".replace(",", ".")


def fecha_formato(valor):
    if pd.isna(valor):
        return "Sin fecha"

    return pd.to_datetime(valor).strftime("%d/%m/%Y")


def partido_texto(fila):
    return (
        f"{texto_seguro(fila.get('equipo_local'))} "
        f"{entero_seguro(fila.get('goles_local'))} - "
        f"{entero_seguro(fila.get('goles_visitante'))} "
        f"{texto_seguro(fila.get('equipo_visitante'))}"
    )


def mostrar_record(titulo, fila, detalle):
    st.info(
        f"{titulo}\n\n"
        f"**{partido_texto(fila)}**\n\n"
        f"📅 {fecha_formato(fila.get('fecha'))} · {detalle}"
    )


def mostrar_tarjeta_igual(titulo, principal, detalle):
    st.markdown(
        f"""
        <div class="curiosity-card">
            <div class="curiosity-card-title">{titulo}</div>
            <div class="curiosity-card-main">{principal}</div>
            <div class="curiosity-card-detail">{detalle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def preparar_partidos(partidos):
    partidos = partidos.copy()

    if "id" not in partidos.columns:
        partidos["id"] = range(1, len(partidos) + 1)

    partidos["fecha"] = pd.to_datetime(partidos["fecha"], errors="coerce")
    partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
    partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")

    partidos = partidos.dropna(
        subset=[
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante"
        ]
    ).copy()

    partidos["goles_local"] = partidos["goles_local"].astype(int)
    partidos["goles_visitante"] = partidos["goles_visitante"].astype(int)

    partidos["goles_totales"] = partidos["goles_local"] + partidos["goles_visitante"]
    partidos["diferencia_goles"] = (
        partidos["goles_local"] - partidos["goles_visitante"]
    ).abs()

    partidos["resultado_local"] = "E"
    partidos.loc[
        partidos["goles_local"] > partidos["goles_visitante"],
        "resultado_local"
    ] = "G"
    partidos.loc[
        partidos["goles_local"] < partidos["goles_visitante"],
        "resultado_local"
    ] = "P"

    partidos["resultado_sin_localia"] = partidos.apply(
        lambda fila: (
            f"{max(fila['goles_local'], fila['goles_visitante'])}-"
            f"{min(fila['goles_local'], fila['goles_visitante'])}"
        ),
        axis=1
    )

    partidos["Año"] = partidos["fecha"].dt.year
    partidos["Mes"] = partidos["fecha"].dt.month
    partidos["Mes nombre"] = partidos["fecha"].dt.strftime("%m")

    return partidos


def preparar_participaciones(participaciones, partidos):
    participaciones = participaciones.dropna(
        subset=["partido_id", "jugador", "equipo"]
    ).copy()

    historial = participaciones.merge(
        partidos[
            [
                "id",
                "fecha",
                "equipo_local",
                "equipo_visitante",
                "resultado_local",
                "goles_totales",
                "diferencia_goles"
            ]
        ],
        left_on="partido_id",
        right_on="id",
        how="left",
        suffixes=("", "_partido")
    )

    historial["resultado_jugador"] = ""

    mask_local = historial["equipo"] == historial["equipo_local"]
    mask_visitante = historial["equipo"] == historial["equipo_visitante"]

    historial.loc[mask_local, "resultado_jugador"] = historial["resultado_local"]
    historial.loc[
        mask_visitante & (historial["resultado_local"] == "G"),
        "resultado_jugador"
    ] = "P"
    historial.loc[
        mask_visitante & (historial["resultado_local"] == "P"),
        "resultado_jugador"
    ] = "G"
    historial.loc[
        mask_visitante & (historial["resultado_local"] == "E"),
        "resultado_jugador"
    ] = "E"

    historial = historial[
        historial["resultado_jugador"].isin(["G", "E", "P"])
    ].copy()

    return historial


def top_jugadores_por_condicion(historial, condicion, total_partidos, columna_nombre):
    datos = historial[condicion].copy()

    if datos.empty or total_partidos == 0:
        return pd.DataFrame()

    ranking = (
        datos
        .groupby("jugador")
        .size()
        .reset_index(name="Participaciones")
        .sort_values(["Participaciones", "jugador"], ascending=[False, True])
        .head(3)
        .rename(columns={"jugador": "Jugador"})
    )

    ranking[columna_nombre] = (
        ranking["Participaciones"] / total_partidos * 100
    ).round(1)

    return ranking


def preparar_tabla_top3(dataframe, columna_porcentaje):
    if dataframe.empty:
        return pd.DataFrame()

    tabla = dataframe.copy()
    tabla["% sobre total"] = tabla[columna_porcentaje].map(lambda valor: f"{valor:.1f}%")

    return tabla[["Jugador", "Participaciones", "% sobre total"]]


def construir_grafico_goles_por_anio(partidos):
    goles_anio = (
        partidos
        .groupby("Año", as_index=False)
        .agg(
            Partidos=("id", "size"),
            Promedio_goles=("goles_totales", "mean")
        )
    )

    goles_anio["Promedio_goles"] = goles_anio["Promedio_goles"].round(2)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=goles_anio["Año"],
            y=goles_anio["Promedio_goles"],
            name="Goles por partido",
            marker_color="#38BDF8",
            hovertemplate="Año: %{x}<br>Goles/partido: %{y:.2f}<extra></extra>"
        )
    )

    fig.update_layout(
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        xaxis={"title": "Año", "tickmode": "linear", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis={"title": "Promedio de goles por partido", "gridcolor": "rgba(255,255,255,0.12)"},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"},
        margin={"l": 50, "r": 30, "t": 40, "b": 50}
    )

    return fig


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    partidos = leer_tabla_completa("partidos")
    participaciones = leer_tabla_completa("participaciones")
except Exception as error:
    st.error("No se pudieron leer los datos desde Supabase.")
    st.exception(error)
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
    st.stop()

if participaciones.empty:
    st.warning("La tabla participaciones no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_partidos = [
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]
columnas_participaciones = [
    "partido_id",
    "jugador",
    "equipo"
]

for nombre_tabla, dataframe, columnas_requeridas in [
    ("partidos", partidos, columnas_partidos),
    ("participaciones", participaciones, columnas_participaciones)
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
# LIMPIEZA Y CAMPOS CALCULADOS
# ==================================================

partidos = preparar_partidos(partidos)

if partidos.empty:
    st.warning("No existen partidos con información completa de fecha, equipos y goles.")
    st.stop()

historial = preparar_participaciones(participaciones, partidos)


# ==================================================
# INDICADORES GENERALES
# ==================================================

total_partidos = len(partidos)
total_goles = int(partidos["goles_totales"].sum())
promedio_goles = partidos["goles_totales"].mean()
empates = int((partidos["resultado_local"] == "E").sum())
porcentaje_empates = empates / total_partidos * 100 if total_partidos else 0
promedio_diferencia = partidos["diferencia_goles"].mean()
primer_partido = partidos.loc[partidos["fecha"].idxmin()]
ultimo_partido = partidos.loc[partidos["fecha"].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de partidos", numero_formato(total_partidos))
c2.metric("Total de goles", numero_formato(total_goles))
c3.metric("Promedio de goles", f"{promedio_goles:.2f}")
c4.metric("% de empates", f"{porcentaje_empates:.1f}%")

c5, c6, c7 = st.columns(3)
c5.metric("Primer partido", fecha_formato(primer_partido["fecha"]))
c6.metric("Último partido", fecha_formato(ultimo_partido["fecha"]))
c7.metric("Prom. diferencia de goles", f"{promedio_diferencia:.2f}")

st.divider()


# ==================================================
# RECORDS PRINCIPALES
# ==================================================

mas_goles = partidos.loc[partidos["goles_totales"].idxmax()]
menos_goles = partidos.loc[partidos["goles_totales"].idxmin()]
mayor_goleada = partidos.loc[partidos["diferencia_goles"].idxmax()]
empates_df = partidos[partidos["resultado_local"] == "E"].copy()

col1, col2, col3 = st.columns(3)
with col1:
    mostrar_record(
        "🔥 Partido con más goles",
        mas_goles,
        f"{entero_seguro(mas_goles['goles_totales'])} goles"
    )
with col2:
    mostrar_record(
        "🧤 Partido con menos goles",
        menos_goles,
        f"{entero_seguro(menos_goles['goles_totales'])} goles"
    )
with col3:
    mostrar_record(
        "💥 Mayor goleada",
        mayor_goleada,
        f"{entero_seguro(mayor_goleada['diferencia_goles'])} goles de diferencia"
    )

col4, col5, col6 = st.columns(3)

if not empates_df.empty:
    empate_mas_goles = empates_df.loc[empates_df["goles_totales"].idxmax()]
    empate_menos_goles = empates_df.loc[empates_df["goles_totales"].idxmin()]

    with col4:
        mostrar_record(
            "🤝 Empate con más goles",
            empate_mas_goles,
            f"{entero_seguro(empate_mas_goles['goles_totales'])} goles"
        )
    with col5:
        mostrar_record(
            "🧊 Empate con menos goles",
            empate_menos_goles,
            f"{entero_seguro(empate_menos_goles['goles_totales'])} goles"
        )
else:
    with col4:
        st.info("🤝 Empate con más goles\n\nSin empates registrados.")
    with col5:
        st.info("🧊 Empate con menos goles\n\nSin empates registrados.")

resultado_mas_comun = (
    partidos
    .groupby("resultado_sin_localia")
    .size()
    .reset_index(name="Veces")
    .sort_values(["Veces", "resultado_sin_localia"], ascending=[False, True])
    .iloc[0]
)

with col6:
    st.info(
        "🔢 Resultado más común\n\n"
        f"**{resultado_mas_comun['resultado_sin_localia']}**\n\n"
        f"{entero_seguro(resultado_mas_comun['Veces'])} veces"
    )

st.divider()


# ==================================================
# TOP JUGADORES EN PARTIDOS ESPECIALES
# ==================================================

umbral_goleada = 5
partidos_goleada = partidos[partidos["diferencia_goles"] >= umbral_goleada]
partidos_cerrados = partidos[partidos["diferencia_goles"] <= 1]
total_goleadas = len(partidos_goleada)
total_partidos_cerrados = len(partidos_cerrados)

st.subheader("👤 Jugadores en partidos especiales")
st.caption(
    "Se considera goleada a un partido definido por 5 o más goles de diferencia. "
    "Se considera partido cerrado a un partido empatado o definido por 1 gol de diferencia. "
    "Las derrotas amplias son derrotas por 5 o más goles de diferencia."
)

col_top1, col_top2, col_top3 = st.columns(3)

with col_top1:
    st.subheader("💥 Goleadas ganadas")
    top_goleadas = top_jugadores_por_condicion(
        historial,
        (historial["resultado_jugador"] == "G")
        & (historial["diferencia_goles"] >= umbral_goleada),
        total_goleadas,
        "% de goleadas"
    )
    mostrar_top = preparar_tabla_top3(top_goleadas, "% de goleadas")
    if mostrar_top.empty:
        st.info("No hay registros.")
    else:
        st.dataframe(mostrar_top, use_container_width=True, hide_index=True, height=175)

with col_top2:
    st.subheader("⚖️ Partidos cerrados")
    top_cerrados = top_jugadores_por_condicion(
        historial,
        historial["diferencia_goles"] <= 1,
        total_partidos_cerrados,
        "% de cerrados"
    )
    mostrar_top = preparar_tabla_top3(top_cerrados, "% de cerrados")
    if mostrar_top.empty:
        st.info("No hay registros.")
    else:
        st.dataframe(mostrar_top, use_container_width=True, hide_index=True, height=175)

with col_top3:
    st.subheader("😬 Derrotas amplias")
    top_derrotas = top_jugadores_por_condicion(
        historial,
        (historial["resultado_jugador"] == "P")
        & (historial["diferencia_goles"] >= umbral_goleada),
        total_goleadas,
        "% de derrotas amplias"
    )
    mostrar_top = preparar_tabla_top3(top_derrotas, "% de derrotas amplias")
    if mostrar_top.empty:
        st.info("No hay registros.")
    else:
        st.dataframe(mostrar_top, use_container_width=True, hide_index=True, height=175)

st.divider()


# ==================================================
# GRAFICO DE GOLES POR ANIO
# ==================================================

st.subheader("📊 Goles por partido por año")
st.plotly_chart(
    construir_grafico_goles_por_anio(partidos),
    use_container_width=True
)

st.divider()


# ==================================================
# CALENDARIO
# ==================================================

st.subheader("📆 Curiosidades por mes")

resumen_meses = (
    partidos
    .groupby("Mes", as_index=False)
    .agg(
        Partidos=("id", "size"),
        Goles=("goles_totales", "sum"),
        Promedio_goles=("goles_totales", "mean")
    )
)
resumen_meses["Promedio_goles"] = resumen_meses["Promedio_goles"].round(2)

mes_mas_partidos = resumen_meses.sort_values(["Partidos", "Mes"], ascending=[False, True]).iloc[0]
mes_menos_partidos = resumen_meses.sort_values(["Partidos", "Mes"], ascending=[True, True]).iloc[0]
mes_mayor_promedio = resumen_meses.sort_values(["Promedio_goles", "Partidos"], ascending=[False, False]).iloc[0]
mes_menor_promedio = resumen_meses.sort_values(["Promedio_goles", "Partidos"], ascending=[True, False]).iloc[0]

m1, m2, m3, m4 = st.columns(4)
with m1:
    mostrar_tarjeta_igual(
        "📅 Mes con más partidos",
        f"Mes {entero_seguro(mes_mas_partidos['Mes'])}",
        f"{entero_seguro(mes_mas_partidos['Partidos'])} partidos"
    )
with m2:
    mostrar_tarjeta_igual(
        "🧊 Mes con menos partidos",
        f"Mes {entero_seguro(mes_menos_partidos['Mes'])}",
        f"{entero_seguro(mes_menos_partidos['Partidos'])} partidos"
    )
with m3:
    mostrar_tarjeta_igual(
        "🔥 Mejor promedio de goles",
        f"Mes {entero_seguro(mes_mayor_promedio['Mes'])}",
        f"{decimal_seguro(mes_mayor_promedio['Promedio_goles']):.2f} goles/partido"
    )
with m4:
    mostrar_tarjeta_igual(
        "🧤 Menor promedio de goles",
        f"Mes {entero_seguro(mes_menor_promedio['Mes'])}",
        f"{decimal_seguro(mes_menor_promedio['Promedio_goles']):.2f} goles/partido"
    )
