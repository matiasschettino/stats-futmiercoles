import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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


def emoji_equipo(equipo):
    equipo_texto = texto_seguro(equipo, "").lower()

    if "pesca" in equipo_texto or "pescas" in equipo_texto:
        return "🐟"

    if "dealer" in equipo_texto or "dealers" in equipo_texto:
        return "🚗"

    if "biologo" in equipo_texto or "biólogo" in equipo_texto:
        return "🦠"

    if "dhl" in equipo_texto:
        return "📦"

    return "⚽"


def filtrar_por_periodo(dataframe, periodo, columna_fecha="fecha"):
    if dataframe.empty or periodo == "Histórico" or columna_fecha not in dataframe.columns:
        return dataframe.copy()

    df = dataframe.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha], errors="coerce")
    fecha_maxima = df[columna_fecha].max()

    if pd.isna(fecha_maxima):
        return df.copy()

    if periodo == "Últimos 12 meses":
        fecha_minima = fecha_maxima - pd.Timedelta(days=365)
        return df[df[columna_fecha] >= fecha_minima].copy()

    if periodo == "Últimos 3 años":
        fecha_minima = fecha_maxima - pd.Timedelta(days=365 * 3)
        return df[df[columna_fecha] >= fecha_minima].copy()

    if periodo == "Desde 2020":
        return df[df[columna_fecha].dt.year >= 2020].copy()

    return df.copy()


def resultados_equipo_desde_partidos(partidos_df):
    local = partidos_df[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante",
            "resultado_local"
        ]
    ].copy()
    local["equipo"] = local["equipo_local"]
    local["equipo_rival"] = local["equipo_visitante"]
    local["resultado_equipo"] = local["resultado_local"]
    local["goles_equipo"] = local["goles_local"]
    local["goles_rival"] = local["goles_visitante"]

    visitante = partidos_df[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante",
            "resultado_local"
        ]
    ].copy()
    visitante["equipo"] = visitante["equipo_visitante"]
    visitante["equipo_rival"] = visitante["equipo_local"]
    visitante["resultado_equipo"] = visitante["resultado_local"].map(
        {
            "G": "P",
            "P": "G",
            "E": "E"
        }
    )
    visitante["goles_equipo"] = visitante["goles_visitante"]
    visitante["goles_rival"] = visitante["goles_local"]

    resultados = pd.concat(
        [local, visitante],
        ignore_index=True
    )

    resultados = resultados[
        resultados["equipo"].notna()
        & resultados["resultado_equipo"].isin(["G", "E", "P"])
    ].copy()

    return resultados


def calcular_kpis_equipo(resultados_equipo):
    pj = len(resultados_equipo)
    g = int((resultados_equipo["resultado_equipo"] == "G").sum())
    e = int((resultados_equipo["resultado_equipo"] == "E").sum())
    p = int((resultados_equipo["resultado_equipo"] == "P").sum())
    wr = round(g / pj * 100, 2) if pj else 0

    return {
        "PJ": pj,
        "G": g,
        "E": e,
        "P": p,
        "WinRate": wr
    }


def construir_chips_forma(resultados_equipo, cantidad=8):
    ultimos = (
        resultados_equipo
        .sort_values(["fecha", "id"], ascending=[False, False])
        .head(cantidad)
        .copy()
    )

    if ultimos.empty:
        return ""

    colores = {
        "G": "#22C55E",
        "E": "#FACC15",
        "P": "#EF4444"
    }

    chips = []

    for resultado in ultimos["resultado_equipo"].tolist():
        chips.append(
            "<span style='display:inline-flex; align-items:center; justify-content:center; "
            "width:30px; height:30px; margin:2px; border-radius:999px; "
            f"background:{colores.get(resultado, '#64748B')}; color:#0B1120; "
            "font-weight:800; font-size:14px;'>"
            f"{resultado}</span>"
        )

    return "".join(chips)


def construir_grafico_distribucion(kpis):
    fig = go.Figure()

    valores = [
        entero_seguro(kpis.get("G")),
        entero_seguro(kpis.get("E")),
        entero_seguro(kpis.get("P"))
    ]
    nombres = ["Victorias", "Empates", "Derrotas"]
    colores = ["#22C55E", "#FACC15", "#EF4444"]

    fig.add_trace(
        go.Bar(
            y=["Resultados"],
            x=[valores[0]],
            name=nombres[0],
            orientation="h",
            marker_color=colores[0],
            text=[valores[0]],
            textposition="inside",
            hovertemplate="<b>Victorias</b><br>Cantidad: %{x}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            y=["Resultados"],
            x=[valores[1]],
            name=nombres[1],
            orientation="h",
            marker_color=colores[1],
            text=[valores[1]],
            textposition="inside",
            hovertemplate="<b>Empates</b><br>Cantidad: %{x}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Bar(
            y=["Resultados"],
            x=[valores[2]],
            name=nombres[2],
            orientation="h",
            marker_color=colores[2],
            text=[valores[2]],
            textposition="inside",
            hovertemplate="<b>Derrotas</b><br>Cantidad: %{x}<extra></extra>"
        )
    )

    fig.update_layout(
        height=250,
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        xaxis={"title": "Partidos", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis={"showticklabels": False},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.05, "xanchor": "center", "x": 0.5},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"},
        margin={"l": 20, "r": 20, "t": 70, "b": 40}
    )

    return fig


def construir_evolucion_equipo(resultados_equipo):
    if resultados_equipo.empty or "fecha" not in resultados_equipo.columns:
        return pd.DataFrame()

    df = resultados_equipo.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])

    if df.empty:
        return pd.DataFrame()

    df["Año"] = df["fecha"].dt.year

    evolucion = (
        df
        .groupby("Año")
        .agg(
            PJ=("resultado_equipo", "size"),
            G=("resultado_equipo", lambda x: (x == "G").sum()),
            E=("resultado_equipo", lambda x: (x == "E").sum()),
            P=("resultado_equipo", lambda x: (x == "P").sum())
        )
        .reset_index()
    )

    evolucion["WinRate"] = (
        evolucion["G"]
        / evolucion["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return evolucion


def construir_grafico_evolucion(evolucion):
    fig = go.Figure()

    fig.add_bar(
        x=evolucion["Año"],
        y=evolucion["PJ"],
        name="Partidos jugados",
        marker_color="#38BDF8",
        hovertemplate="Año: %{x}<br>PJ: %{y}<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"],
            y=evolucion["G"],
            mode="lines+markers",
            name="Victorias",
            line={"color": "#22C55E", "width": 3},
            marker={"size": 8},
            hovertemplate="Año: %{x}<br>Victorias: %{y}<extra></extra>"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"],
            y=evolucion["WinRate"],
            mode="lines+markers",
            name="Win Rate %",
            yaxis="y2",
            line={"color": "#FACC15", "width": 3},
            marker={"size": 8},
            hovertemplate="Año: %{x}<br>WR: %{y:.1f}%<extra></extra>"
        )
    )

    fig.update_layout(
        height=520,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        xaxis={"title": "Año", "tickmode": "linear", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis={"title": "Partidos / Victorias", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis2={"title": "Win Rate %", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"}
    )

    return fig


def construir_ultimos_partidos(resultados_equipo):
    ultimos = (
        resultados_equipo
        .sort_values(["fecha", "id"], ascending=[False, False])
        .head(10)
        .copy()
    )

    if ultimos.empty:
        return pd.DataFrame()

    tabla = pd.DataFrame(
        {
            "Fecha": ultimos["fecha"].dt.strftime("%d/%m/%Y") if "fecha" in ultimos.columns else ultimos["id"],
            "Rival": ultimos["equipo_rival"],
            "Resultado": ultimos["resultado_equipo"],
            "Marcador": ultimos.apply(
                lambda fila: (
                    f"{entero_seguro(fila.get('goles_equipo'))}-{entero_seguro(fila.get('goles_rival'))}"
                    if pd.notna(fila.get("goles_equipo")) and pd.notna(fila.get("goles_rival"))
                    else "Sin datos"
                ),
                axis=1
            )
        }
    )

    return tabla


def calcular_rankings_equipo(equipos_df, equipo):
    base = equipos_df.copy()

    def ranking(columna, ascendente=False):
        datos = base.copy()
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce").fillna(0)
        ranking_serie = datos[columna].rank(method="min", ascending=ascendente)
        valor = ranking_serie[datos["equipo"] == equipo]

        if valor.empty or pd.isna(valor.iloc[0]):
            return None

        return int(valor.iloc[0])

    return {
        "Ranking PJ": ranking("PJ"),
        "Ranking victorias": ranking("G"),
        "Ranking Win Rate": ranking("WinRate"),
        "Ranking derrotas": ranking("P")
    }


def calcular_mejores_anios_equipo(evolucion):
    if evolucion.empty:
        return None

    anio_mas_pj = evolucion.sort_values(["PJ", "Año"], ascending=[False, True]).iloc[0]
    anio_mas_victorias = evolucion.sort_values(["G", "Año"], ascending=[False, True]).iloc[0]
    candidatos_wr = evolucion[evolucion["PJ"] >= 5].copy()

    if candidatos_wr.empty:
        anio_mejor_wr = evolucion.sort_values(["WinRate", "PJ", "Año"], ascending=[False, False, True]).iloc[0]
    else:
        anio_mejor_wr = candidatos_wr.sort_values(["WinRate", "PJ", "Año"], ascending=[False, False, True]).iloc[0]

    return anio_mas_pj, anio_mas_victorias, anio_mejor_wr


def calcular_rendimiento_jugadores(participaciones_resultados, equipo):
    rendimiento = (
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

    rendimiento.columns.name = None

    for columna in ["G", "E", "P"]:
        if columna not in rendimiento.columns:
            rendimiento[columna] = 0

    if rendimiento.empty:
        return rendimiento

    rendimiento["PJ"] = rendimiento["G"] + rendimiento["E"] + rendimiento["P"]
    rendimiento["WinRate"] = (
        rendimiento["G"]
        / rendimiento["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return rendimiento


def construir_top_jugadores_completo(rendimiento_equipo):
    if rendimiento_equipo.empty:
        return pd.DataFrame()

    return (
        rendimiento_equipo
        .sort_values(["PJ", "WinRate", "jugador"], ascending=[False, False, True])
        .head(10)
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
    )


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

if "fecha" not in partidos.columns:
    partidos["fecha"] = pd.NaT

partidos["fecha"] = pd.to_datetime(partidos["fecha"], errors="coerce")

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

for columna in ["WinRate", "wr_mejor_jugador"]:
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
            "fecha",
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
mask_local = participaciones_resultados["equipo"] == participaciones_resultados["equipo_local"]
mask_visitante = participaciones_resultados["equipo"] == participaciones_resultados["equipo_visitante"]
participaciones_resultados.loc[mask_local, "resultado_jugador"] = participaciones_resultados["resultado_local"]
participaciones_resultados.loc[
    mask_visitante & (participaciones_resultados["resultado_local"] == "G"),
    "resultado_jugador"
] = "P"
participaciones_resultados.loc[
    mask_visitante & (participaciones_resultados["resultado_local"] == "P"),
    "resultado_jugador"
] = "G"
participaciones_resultados.loc[
    mask_visitante & (participaciones_resultados["resultado_local"] == "E"),
    "resultado_jugador"
] = "E"
participaciones_resultados = participaciones_resultados[
    participaciones_resultados["resultado_jugador"].isin(["G", "E", "P"])
].copy()

resultados_equipos = resultados_equipo_desde_partidos(partidos)


# ==================================================
# SOLO LOS 5 EQUIPOS CON MAS PARTIDOS
# ==================================================

equipos_top = (
    equipos
    .dropna(subset=["equipo"])
    .sort_values(["PJ", "equipo"], ascending=[False, True])
    .head(5)
    .copy()
)

if equipos_top.empty:
    st.warning("No hay equipos disponibles para mostrar.")
    st.stop()


# ==================================================
# SELECTOR Y PERIODO
# ==================================================

equipo = st.selectbox(
    "🔎 Seleccionar equipo",
    equipos_top["equipo"].astype(str).tolist(),
    index=None,
    placeholder="Seleccioná un equipo..."
)

periodo = st.selectbox(
    "Período",
    [
        "Histórico",
        "Últimos 12 meses",
        "Últimos 3 años",
        "Desde 2020"
    ],
    index=0
)

if equipo is None:
    st.info("Seleccioná un equipo para ver sus estadísticas.")
    st.stop()

filas_equipo = equipos_top[equipos_top["equipo"] == equipo]

if filas_equipo.empty:
    st.warning("No se encontraron datos para el equipo seleccionado.")
    st.stop()

info = filas_equipo.iloc[0]

resultados_equipo_todos = resultados_equipos[
    resultados_equipos["equipo"] == equipo
].copy()
resultados_equipo_periodo = filtrar_por_periodo(resultados_equipo_todos, periodo)

if periodo == "Histórico":
    kpis_equipo = {
        "PJ": entero_seguro(info.get("PJ")),
        "G": entero_seguro(info.get("G")),
        "E": entero_seguro(info.get("E")),
        "P": entero_seguro(info.get("P")),
        "WinRate": decimal_seguro(info.get("WinRate"))
    }
else:
    kpis_equipo = calcular_kpis_equipo(resultados_equipo_periodo)

participaciones_periodo = filtrar_por_periodo(participaciones_resultados, periodo)


# ==================================================
# ENCABEZADO
# ==================================================

header_col, forma_col = st.columns([2, 1])

with header_col:
    st.header(f"{emoji_equipo(equipo)} {equipo}")
    st.caption("Referencias: 🐟 Pescas · 🚗 Dealers · 🦠 Biólogos · 📦 DHL")

with forma_col:
    chips = construir_chips_forma(resultados_equipo_periodo)
    if chips:
        st.caption("Forma reciente")
        st.markdown(chips, unsafe_allow_html=True)


# ==================================================
# KPIS PRINCIPALES
# ==================================================

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("PJ", entero_seguro(kpis_equipo.get("PJ")))
c2.metric("Victorias", entero_seguro(kpis_equipo.get("G")))
c3.metric("Empates", entero_seguro(kpis_equipo.get("E")))
c4.metric("Derrotas", entero_seguro(kpis_equipo.get("P")))
c5.metric("Win Rate", f"{decimal_seguro(kpis_equipo.get('WinRate')):.1f}%")


# ==================================================
# RANKING HISTORICO
# ==================================================

if periodo == "Histórico":
    rankings = calcular_rankings_equipo(equipos, equipo)
    st.divider()
    st.subheader("🏛️ Posiciones históricas")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Ranking PJ", f"#{rankings['Ranking PJ']}")
    r2.metric("Ranking victorias", f"#{rankings['Ranking victorias']}")
    r3.metric("Ranking Win Rate", f"#{rankings['Ranking Win Rate']}")
    r4.metric("Ranking derrotas", f"#{rankings['Ranking derrotas']}")


# ==================================================
# INFORMACION DESTACADA
# ==================================================

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.info(
        "👑 Jugador más presente\n\n"
        f"**{texto_seguro(info.get('jugador_mas_presente'))}**\n\n"
        f"{entero_seguro(info.get('pj_jugador_mas_presente'))} PJ"
    )

with col2:
    mejor_jugador = texto_seguro(info.get("mejor_jugador_historico"))

    if mejor_jugador == "Sin datos":
        st.info("🏆 Mejor jugador histórico\n\nSin datos. Se requieren al menos 20 partidos.")
    else:
        st.info(
            "🏆 Mejor jugador histórico\n\n"
            f"**{mejor_jugador}**\n\n"
            f"{entero_seguro(info.get('pj_mejor_jugador'))} PJ · "
            f"{decimal_seguro(info.get('wr_mejor_jugador')):.1f}% WR"
        )


# ==================================================
# DISTRIBUCION DE RESULTADOS
# ==================================================

st.divider()
st.subheader("📊 Distribución de resultados")
st.plotly_chart(
    construir_grafico_distribucion(kpis_equipo),
    use_container_width=True
)


# ==================================================
# EVOLUCION HISTORICA
# ==================================================

st.divider()
st.subheader("📈 Evolución histórica")
evolucion = construir_evolucion_equipo(resultados_equipo_periodo)

if evolucion.empty:
    st.info("No hay datos históricos para mostrar en el período seleccionado.")
else:
    st.plotly_chart(
        construir_grafico_evolucion(evolucion),
        use_container_width=True
    )


# ==================================================
# MEJORES AÑOS
# ==================================================

if not evolucion.empty:
    mejores_anios = calcular_mejores_anios_equipo(evolucion)

    if mejores_anios is not None:
        anio_mas_pj, anio_mas_victorias, anio_mejor_wr = mejores_anios
        st.divider()
        st.subheader("📆 Mejores años")
        a1, a2, a3 = st.columns(3)
        a1.info(
            "📌 Año con más partidos\n\n"
            f"**{entero_seguro(anio_mas_pj['Año'])}**\n\n"
            f"{entero_seguro(anio_mas_pj['PJ'])} PJ"
        )
        a2.info(
            "🏆 Año con más victorias\n\n"
            f"**{entero_seguro(anio_mas_victorias['Año'])}**\n\n"
            f"{entero_seguro(anio_mas_victorias['G'])} victorias"
        )
        a3.info(
            "🎯 Mejor año por Win Rate\n\n"
            f"**{entero_seguro(anio_mejor_wr['Año'])}**\n\n"
            f"{decimal_seguro(anio_mejor_wr['WinRate']):.1f}% WR"
        )


# ==================================================
# TOP JUGADORES
# ==================================================

st.divider()
st.subheader("👥 Jugadores más presentes")
rendimiento_equipo = calcular_rendimiento_jugadores(participaciones_periodo, equipo)
top_jugadores = construir_top_jugadores_completo(rendimiento_equipo)

if top_jugadores.empty:
    st.info("No hay participaciones registradas para este equipo en el período seleccionado.")
else:
    st.dataframe(
        top_jugadores,
        use_container_width=True,
        hide_index=True,
        height=380
    )


# ==================================================
# RANKINGS DE JUGADORES DEL EQUIPO
# Minimo 20 partidos
# ==================================================

st.divider()
rendimiento_relevante = rendimiento_equipo[
    rendimiento_equipo["PJ"] >= 20
].copy() if not rendimiento_equipo.empty else pd.DataFrame()

col_ganadores, col_bajo = st.columns(2)

with col_ganadores:
    st.subheader("🏆 Mejores jugadores con este equipo")

    if rendimiento_relevante.empty:
        st.info("No hay jugadores con al menos 20 partidos en este equipo.")
    else:
        top_ganadores = (
            rendimiento_relevante
            .sort_values(["WinRate", "PJ", "G", "jugador"], ascending=[False, False, False, True])
            .head(10)
            [["jugador", "PJ", "G", "E", "P", "WinRate"]]
            .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
        )
        st.dataframe(top_ganadores, use_container_width=True, hide_index=True, height=380)

with col_bajo:
    st.subheader("📉 Jugadores con menor Win Rate")

    if rendimiento_relevante.empty:
        st.info("No hay jugadores con al menos 20 partidos en este equipo.")
    else:
        top_bajo = (
            rendimiento_relevante
            .sort_values(["WinRate", "PJ", "P", "jugador"], ascending=[True, False, False, True])
            .head(10)
            [["jugador", "PJ", "G", "E", "P", "WinRate"]]
            .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
        )
        st.dataframe(top_bajo, use_container_width=True, hide_index=True, height=380)


# ==================================================
# ULTIMOS PARTIDOS
# ==================================================

st.divider()
st.subheader("📅 Últimos 10 partidos")
ultimos_partidos = construir_ultimos_partidos(resultados_equipo_periodo)

if ultimos_partidos.empty:
    st.info("No hay partidos disponibles para mostrar.")
else:
    st.dataframe(
        ultimos_partidos,
        use_container_width=True,
        hide_index=True,
        height=380
    )
