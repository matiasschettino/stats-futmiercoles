import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from itertools import combinations

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("📚 Datos Curiosos")
st.markdown("Récords, rarezas e hitos históricos de FutMiércoles.")

supabase = get_supabase()


# ==================================================
# FUNCIONES BASE
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


def formato_numero(valor):
    return f"{entero_seguro(valor):,}".replace(",", ".")


def formatear_fecha(valor):
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


def mostrar_tarjeta(titulo, fila, valor_label, valor):
    st.info(
        f"{titulo}\n\n"
        f"**{partido_texto(fila)}**\n\n"
        f"📅 {formatear_fecha(fila.get('fecha'))} · {valor_label}: **{valor}**"
    )


def filtrar_por_fechas(dataframe, fecha_desde, fecha_hasta, columna_fecha="fecha"):
    if dataframe.empty or columna_fecha not in dataframe.columns:
        return dataframe.copy()

    filtrado = dataframe.copy()
    filtrado[columna_fecha] = pd.to_datetime(
        filtrado[columna_fecha],
        errors="coerce"
    )
    filtrado = filtrado[filtrado[columna_fecha].notna()].copy()

    if fecha_desde is not None:
        filtrado = filtrado[
            filtrado[columna_fecha].dt.date >= fecha_desde
        ].copy()

    if fecha_hasta is not None:
        filtrado = filtrado[
            filtrado[columna_fecha].dt.date <= fecha_hasta
        ].copy()

    return filtrado


def preparar_tabla_partidos(dataframe):
    if dataframe.empty:
        return pd.DataFrame()

    tabla = dataframe.copy()
    tabla["Fecha"] = tabla["fecha"].dt.strftime("%d/%m/%Y")
    tabla["Partido"] = tabla.apply(partido_texto, axis=1)

    columnas = [
        "Fecha",
        "Partido",
        "goles_totales",
        "diferencia_goles"
    ]

    tabla = tabla[columnas].rename(
        columns={
            "goles_totales": "Total goles",
            "diferencia_goles": "Diferencia"
        }
    )

    return tabla


def mostrar_tabla(dataframe, alto=380):
    if dataframe.empty:
        st.info("No hay datos para mostrar en el período seleccionado.")
    else:
        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
            height=alto
        )


# ==================================================
# DATOS DERIVADOS
# ==================================================

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

    partidos["marcador_exacto"] = (
        partidos["goles_local"].astype(str)
        + "-"
        + partidos["goles_visitante"].astype(str)
    )
    partidos["marcador_normalizado"] = partidos.apply(
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


def construir_resultados_equipos(partidos):
    if partidos.empty:
        return pd.DataFrame()

    local = partidos[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante",
            "resultado_local",
            "goles_totales",
            "diferencia_goles"
        ]
    ].copy()
    local["equipo"] = local["equipo_local"]
    local["rival"] = local["equipo_visitante"]
    local["GF"] = local["goles_local"]
    local["GC"] = local["goles_visitante"]
    local["resultado"] = local["resultado_local"]

    visitante = partidos[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante",
            "resultado_local",
            "goles_totales",
            "diferencia_goles"
        ]
    ].copy()
    visitante["equipo"] = visitante["equipo_visitante"]
    visitante["rival"] = visitante["equipo_local"]
    visitante["GF"] = visitante["goles_visitante"]
    visitante["GC"] = visitante["goles_local"]
    visitante["resultado"] = visitante["resultado_local"].map(
        {
            "G": "P",
            "P": "G",
            "E": "E"
        }
    )

    resultados = pd.concat([local, visitante], ignore_index=True)
    resultados["DG"] = resultados["GF"] - resultados["GC"]

    return resultados


def construir_participaciones_resultados(participaciones, partidos):
    if participaciones.empty or partidos.empty:
        return pd.DataFrame()

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


def calcular_estadisticas_duplas(historial):
    registros = []

    if historial.empty:
        return pd.DataFrame()

    for _, grupo_partido in historial.groupby("partido_id"):
        for equipo, grupo_equipo in grupo_partido.groupby("equipo"):
            jugadores_equipo = sorted(
                grupo_equipo["jugador"].dropna().astype(str).unique()
            )

            if len(jugadores_equipo) < 2:
                continue

            resultado = grupo_equipo.iloc[0]["resultado_jugador"]

            for jugador_1, jugador_2 in combinations(jugadores_equipo, 2):
                registros.append(
                    {
                        "jugador_1": jugador_1,
                        "jugador_2": jugador_2,
                        "resultado": resultado
                    }
                )

    if not registros:
        return pd.DataFrame()

    datos = pd.DataFrame(registros)
    resumen = (
        datos
        .pivot_table(
            index=["jugador_1", "jugador_2"],
            columns="resultado",
            aggfunc="size",
            fill_value=0
        )
        .reset_index()
    )

    resumen.columns.name = None

    for columna in ["G", "E", "P"]:
        if columna not in resumen.columns:
            resumen[columna] = 0

    resumen["PJ"] = resumen["G"] + resumen["E"] + resumen["P"]
    resumen["WinRate"] = (
        resumen["G"] / resumen["PJ"].replace(0, pd.NA) * 100
    ).round(1).fillna(0)
    resumen["% Empates"] = (
        resumen["E"] / resumen["PJ"].replace(0, pd.NA) * 100
    ).round(1).fillna(0)
    resumen["Dupla"] = resumen["jugador_1"] + " + " + resumen["jugador_2"]

    return resumen


def calcular_estadisticas_rivales(historial):
    registros = []

    if historial.empty:
        return pd.DataFrame()

    for _, grupo_partido in historial.groupby("partido_id"):
        equipos_partido = list(grupo_partido["equipo"].dropna().unique())

        if len(equipos_partido) < 2:
            continue

        equipo_1 = equipos_partido[0]
        equipo_2 = equipos_partido[1]
        grupo_1 = grupo_partido[grupo_partido["equipo"] == equipo_1]
        grupo_2 = grupo_partido[grupo_partido["equipo"] == equipo_2]

        for _, fila_1 in grupo_1.iterrows():
            for _, fila_2 in grupo_2.iterrows():
                jugador_a, jugador_b = sorted([fila_1["jugador"], fila_2["jugador"]])

                if fila_1["jugador"] == jugador_a:
                    resultado_a = fila_1["resultado_jugador"]
                    resultado_b = fila_2["resultado_jugador"]
                else:
                    resultado_a = fila_2["resultado_jugador"]
                    resultado_b = fila_1["resultado_jugador"]

                registros.append(
                    {
                        "jugador_1": jugador_a,
                        "jugador_2": jugador_b,
                        "g_jugador_1": 1 if resultado_a == "G" else 0,
                        "g_jugador_2": 1 if resultado_b == "G" else 0,
                        "E": 1 if resultado_a == "E" else 0,
                        "pj": 1
                    }
                )

    if not registros:
        return pd.DataFrame()

    resumen = (
        pd.DataFrame(registros)
        .groupby(["jugador_1", "jugador_2"], as_index=False)
        .agg(
            pj=("pj", "sum"),
            g_jugador_1=("g_jugador_1", "sum"),
            g_jugador_2=("g_jugador_2", "sum"),
            E=("E", "sum")
        )
    )

    resumen["winrate_jugador_1"] = (
        resumen["g_jugador_1"] / resumen["pj"].replace(0, pd.NA) * 100
    ).round(1).fillna(0)
    resumen["winrate_jugador_2"] = (
        resumen["g_jugador_2"] / resumen["pj"].replace(0, pd.NA) * 100
    ).round(1).fillna(0)

    return resumen


def preparar_mayores_paternidades(rivales_df, minimo_enfrentamientos):
    if rivales_df.empty:
        return pd.DataFrame()

    base = rivales_df[rivales_df["pj"] >= minimo_enfrentamientos].copy()

    if base.empty:
        return pd.DataFrame()

    registros = []

    for _, fila in base.iterrows():
        jugador_1 = fila["jugador_1"]
        jugador_2 = fila["jugador_2"]
        g_jugador_1 = entero_seguro(fila["g_jugador_1"])
        g_jugador_2 = entero_seguro(fila["g_jugador_2"])

        if g_jugador_1 >= g_jugador_2:
            dominador = jugador_1
            rival = jugador_2
            victorias_dominador = g_jugador_1
            victorias_rival = g_jugador_2
            wr_dominador = decimal_seguro(fila["winrate_jugador_1"])
        else:
            dominador = jugador_2
            rival = jugador_1
            victorias_dominador = g_jugador_2
            victorias_rival = g_jugador_1
            wr_dominador = decimal_seguro(fila["winrate_jugador_2"])

        registros.append(
            {
                "Paternidad": f"{dominador} sobre {rival}",
                "Dominador": dominador,
                "Rival": rival,
                "PJ": entero_seguro(fila["pj"]),
                "Victorias dominador": victorias_dominador,
                "Victorias rival": victorias_rival,
                "Diferencia": abs(victorias_dominador - victorias_rival),
                "WR dominador %": wr_dominador,
                "Empates": entero_seguro(fila["E"])
            }
        )

    return (
        pd.DataFrame(registros)
        .sort_values(["Diferencia", "PJ", "WR dominador %", "Paternidad"], ascending=[False, False, False, True])
    )


def construir_evolucion_anual(partidos):
    if partidos.empty:
        return pd.DataFrame()

    evolucion = (
        partidos
        .groupby("Año")
        .agg(
            Partidos=("id", "size"),
            Goles=("goles_totales", "sum"),
            Promedio_goles=("goles_totales", "mean")
        )
        .reset_index()
    )
    evolucion["Promedio_goles"] = evolucion["Promedio_goles"].round(2)

    return evolucion


def construir_grafico_evolucion(evolucion):
    fig = go.Figure()

    fig.add_bar(
        x=evolucion["Año"],
        y=evolucion["Partidos"],
        name="Partidos",
        marker_color="#38BDF8",
        hovertemplate="Año: %{x}<br>Partidos: %{y}<extra></extra>"
    )
    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"],
            y=evolucion["Promedio_goles"],
            name="Promedio goles",
            mode="lines+markers",
            yaxis="y2",
            line={"color": "#FACC15", "width": 3},
            marker={"size": 8},
            hovertemplate="Año: %{x}<br>Promedio: %{y:.2f}<extra></extra>"
        )
    )

    fig.update_layout(
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        xaxis={"title": "Año", "tickmode": "linear", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis={"title": "Partidos", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis2={"title": "Promedio goles", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"}
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
# VALIDACION
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
    faltantes = [columna for columna in columnas_requeridas if columna not in dataframe.columns]

    if faltantes:
        st.error(f"Faltan columnas en {nombre_tabla}: " + ", ".join(faltantes))
        st.stop()


# ==================================================
# PREPARACION
# ==================================================

partidos = preparar_partidos(partidos)

if partidos.empty:
    st.warning("No existen partidos con información completa de fecha, equipos y goles.")
    st.stop()

historial = construir_participaciones_resultados(participaciones, partidos)

fechas_validas = partidos["fecha"].dropna()
fecha_minima = fechas_validas.min().date()
fecha_maxima = fechas_validas.max().date()

col_f1, col_f2 = st.columns(2)
with col_f1:
    fecha_desde = st.date_input(
        "Desde",
        value=fecha_minima,
        min_value=fecha_minima,
        max_value=fecha_maxima
    )
with col_f2:
    fecha_hasta = st.date_input(
        "Hasta",
        value=fecha_maxima,
        min_value=fecha_minima,
        max_value=fecha_maxima
    )

partidos_filtrados = filtrar_por_fechas(partidos, fecha_desde, fecha_hasta)
historial_filtrado = filtrar_por_fechas(historial, fecha_desde, fecha_hasta)

if partidos_filtrados.empty:
    st.warning("No hay partidos dentro del período seleccionado.")
    st.stop()

resultados_equipos = construir_resultados_equipos(partidos_filtrados)
duplas = calcular_estadisticas_duplas(historial_filtrado)
rivales = calcular_estadisticas_rivales(historial_filtrado)


# ==================================================
# KPIS GENERALES
# ==================================================

total_partidos = len(partidos_filtrados)
total_goles = int(partidos_filtrados["goles_totales"].sum())
promedio_goles = partidos_filtrados["goles_totales"].mean()
promedio_local = partidos_filtrados["goles_local"].mean()
promedio_visitante = partidos_filtrados["goles_visitante"].mean()
empates = int((partidos_filtrados["resultado_local"] == "E").sum())
porcentaje_empates = empates / total_partidos * 100 if total_partidos else 0
promedio_diferencia = partidos_filtrados["diferencia_goles"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Partidos", formato_numero(total_partidos))
k2.metric("Total goles", formato_numero(total_goles))
k3.metric("Promedio goles", f"{promedio_goles:.2f}")
k4.metric("Empates", f"{empates} ({porcentaje_empates:.1f}%)")

k5, k6, k7, k8 = st.columns(4)
k5.metric("Primer partido", formatear_fecha(partidos_filtrados["fecha"].min()))
k6.metric("Último partido", formatear_fecha(partidos_filtrados["fecha"].max()))
k7.metric("Prom. local / visitante", f"{promedio_local:.2f} / {promedio_visitante:.2f}")
k8.metric("Prom. diferencia", f"{promedio_diferencia:.2f}")

st.divider()


# ==================================================
# TABS
# ==================================================

tab_records, tab_goles, tab_equipos, tab_jugadores, tab_duplas, tab_calendario = st.tabs(
    [
        "🎯 Récords generales",
        "⚽ Goles y marcadores",
        "🐟 Equipos",
        "👤 Jugadores",
        "🤝 Duplas y rivalidades",
        "📆 Calendario"
    ]
)


# ==================================================
# RECORDS GENERALES
# ==================================================

with tab_records:
    mas_goles = partidos_filtrados.loc[partidos_filtrados["goles_totales"].idxmax()]
    menos_goles = partidos_filtrados.loc[partidos_filtrados["goles_totales"].idxmin()]
    mayor_diferencia = partidos_filtrados.loc[partidos_filtrados["diferencia_goles"].idxmax()]

    c1, c2, c3 = st.columns(3)
    with c1:
        mostrar_tarjeta("🔥 Partido con más goles", mas_goles, "goles", entero_seguro(mas_goles["goles_totales"]))
    with c2:
        mostrar_tarjeta("🧤 Partido con menos goles", menos_goles, "goles", entero_seguro(menos_goles["goles_totales"]))
    with c3:
        mostrar_tarjeta("💥 Mayor goleada", mayor_diferencia, "diferencia", entero_seguro(mayor_diferencia["diferencia_goles"]))

    st.divider()
    st.subheader("🔥 Top 10 partidos con más goles")
    mostrar_tabla(
        preparar_tabla_partidos(
            partidos_filtrados.sort_values(["goles_totales", "fecha"], ascending=[False, True]).head(10)
        )
    )

    st.subheader("🧤 Top 10 partidos con menos goles")
    mostrar_tabla(
        preparar_tabla_partidos(
            partidos_filtrados.sort_values(["goles_totales", "fecha"], ascending=[True, True]).head(10)
        )
    )

    st.subheader("💥 Top 10 goleadas")
    mostrar_tabla(
        preparar_tabla_partidos(
            partidos_filtrados.sort_values(["diferencia_goles", "goles_totales"], ascending=[False, False]).head(10)
        )
    )

    st.subheader("⚖️ Partidos más parejos")
    partidos_parejos = partidos_filtrados[partidos_filtrados["diferencia_goles"] <= 1].copy()
    st.info(
        f"Hubo **{len(partidos_parejos)}** partido(s) con diferencia de 0 o 1 gol, "
        f"equivalentes al **{len(partidos_parejos) / total_partidos * 100:.1f}%** del período."
    )
    mostrar_tabla(
        preparar_tabla_partidos(
            partidos_parejos.sort_values(["fecha"], ascending=False).head(10)
        ),
        alto=320
    )


# ==================================================
# GOLES Y MARCADORES
# ==================================================

with tab_goles:
    st.subheader("🔢 Marcadores más comunes")

    marcador_exacto = (
        partidos_filtrados
        .groupby("marcador_exacto")
        .size()
        .reset_index(name="Veces")
        .sort_values(["Veces", "marcador_exacto"], ascending=[False, True])
        .head(10)
        .rename(columns={"marcador_exacto": "Marcador exacto"})
    )
    mostrar_tabla(marcador_exacto, alto=320)

    marcador_normalizado = (
        partidos_filtrados
        .groupby("marcador_normalizado")
        .size()
        .reset_index(name="Veces")
        .sort_values(["Veces", "marcador_normalizado"], ascending=[False, True])
        .head(10)
        .rename(columns={"marcador_normalizado": "Resultado sin localía"})
    )
    st.subheader("🔁 Resultados más comunes, sin importar localía")
    mostrar_tabla(marcador_normalizado, alto=320)

    st.divider()
    empates_df = partidos_filtrados[partidos_filtrados["resultado_local"] == "E"].copy()

    if not empates_df.empty:
        empate_mas_goles = empates_df.loc[empates_df["goles_totales"].idxmax()]
        empate_menos_goles = empates_df.loc[empates_df["goles_totales"].idxmin()]

        c1, c2 = st.columns(2)
        with c1:
            mostrar_tarjeta("🤝 Empate con más goles", empate_mas_goles, "goles", entero_seguro(empate_mas_goles["goles_totales"]))
        with c2:
            mostrar_tarjeta("🧊 Empate con menos goles", empate_menos_goles, "goles", entero_seguro(empate_menos_goles["goles_totales"]))
    else:
        st.info("No hubo empates en el período seleccionado.")

    st.divider()
    st.subheader("📊 Distribución de goles por partido")
    distribucion = (
        partidos_filtrados
        .groupby("goles_totales")
        .size()
        .reset_index(name="Partidos")
        .rename(columns={"goles_totales": "Goles totales"})
        .sort_values("Goles totales")
    )
    mostrar_tabla(distribucion, alto=360)


# ==================================================
# EQUIPOS
# ==================================================

with tab_equipos:
    if resultados_equipos.empty:
        st.info("No hay datos de equipos en el período seleccionado.")
    else:
        resumen_equipos = (
            resultados_equipos
            .groupby("equipo", as_index=False)
            .agg(
                PJ=("id", "size"),
                GF=("GF", "sum"),
                GC=("GC", "sum"),
                DG=("DG", "sum"),
                G=("resultado", lambda x: (x == "G").sum()),
                E=("resultado", lambda x: (x == "E").sum()),
                P=("resultado", lambda x: (x == "P").sum())
            )
        )
        resumen_equipos["GF/PJ"] = (resumen_equipos["GF"] / resumen_equipos["PJ"]).round(2)
        resumen_equipos["GC/PJ"] = (resumen_equipos["GC"] / resumen_equipos["PJ"]).round(2)
        resumen_equipos["Win Rate %"] = (resumen_equipos["G"] / resumen_equipos["PJ"] * 100).round(1)

        equipo_mas_goleador = resumen_equipos.sort_values(["GF", "PJ"], ascending=[False, False]).iloc[0]
        equipo_mejor_dg = resumen_equipos.sort_values(["DG", "GF"], ascending=[False, False]).iloc[0]
        equipo_mas_recibio = resumen_equipos.sort_values(["GC", "PJ"], ascending=[False, False]).iloc[0]
        equipo_menos_gc_pj = resumen_equipos.sort_values(["GC/PJ", "PJ"], ascending=[True, False]).iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.info(f"🔥 Equipo más goleador\n\n**{equipo_mas_goleador['equipo']}**\n\n{entero_seguro(equipo_mas_goleador['GF'])} goles")
        c2.info(f"🎯 Mejor diferencia de gol\n\n**{equipo_mejor_dg['equipo']}**\n\n{entero_seguro(equipo_mejor_dg['DG'])} DG")
        c3.info(f"🥅 Equipo que más recibió\n\n**{equipo_mas_recibio['equipo']}**\n\n{entero_seguro(equipo_mas_recibio['GC'])} goles")
        c4.info(f"🧱 Menor GC/PJ\n\n**{equipo_menos_gc_pj['equipo']}**\n\n{decimal_seguro(equipo_menos_gc_pj['GC/PJ']):.2f}")

        st.divider()
        st.subheader("📊 Resumen por equipo")
        mostrar_tabla(
            resumen_equipos.sort_values(["GF", "DG", "PJ"], ascending=[False, False, False]),
            alto=380
        )

        st.subheader("💥 Mayor goleada de cada equipo")
        victorias = resultados_equipos[resultados_equipos["resultado"] == "G"].copy()
        if victorias.empty:
            st.info("No hay victorias registradas en el período seleccionado.")
        else:
            idx = victorias.groupby("equipo")["DG"].idxmax()
            goleadas_equipo = victorias.loc[idx].copy()
            goleadas_equipo["Fecha"] = goleadas_equipo["fecha"].dt.strftime("%d/%m/%Y")
            goleadas_equipo["Partido"] = (
                goleadas_equipo["equipo"]
                + " "
                + goleadas_equipo["GF"].astype(int).astype(str)
                + " - "
                + goleadas_equipo["GC"].astype(int).astype(str)
                + " "
                + goleadas_equipo["rival"]
            )
            mostrar_tabla(
                goleadas_equipo[["equipo", "Fecha", "Partido", "DG"]]
                .rename(columns={"equipo": "Equipo", "DG": "Diferencia"})
                .sort_values(["Diferencia", "Equipo"], ascending=[False, True]),
                alto=360
            )


# ==================================================
# JUGADORES
# ==================================================

with tab_jugadores:
    if historial_filtrado.empty:
        st.info("No hay datos de jugadores en el período seleccionado.")
    else:
        umbral_goleada = 5
        umbral_goles_altos = partidos_filtrados["goles_totales"].quantile(0.90)

        st.subheader("👤 Jugadores en partidos especiales")
        c1, c2, c3 = st.columns(3)
        c1.metric("Umbral goleada", f"{umbral_goleada}+ goles")
        c2.metric("Partido cerrado", "0 o 1 gol")
        c3.metric("Muchos goles", f">= {umbral_goles_altos:.0f}")

        jugadores_goleadas = (
            historial_filtrado[
                (historial_filtrado["resultado_jugador"] == "G")
                & (historial_filtrado["diferencia_goles"] >= umbral_goleada)
            ]
            .groupby("jugador")
            .size()
            .reset_index(name="Goleadas ganadas")
            .sort_values(["Goleadas ganadas", "jugador"], ascending=[False, True])
            .head(10)
            .rename(columns={"jugador": "Jugador"})
        )
        st.subheader("💥 Más participaciones en goleadas ganadas")
        mostrar_tabla(jugadores_goleadas, alto=320)

        jugadores_cerrados = (
            historial_filtrado[historial_filtrado["diferencia_goles"] <= 1]
            .groupby("jugador")
            .size()
            .reset_index(name="Partidos cerrados")
            .sort_values(["Partidos cerrados", "jugador"], ascending=[False, True])
            .head(10)
            .rename(columns={"jugador": "Jugador"})
        )
        st.subheader("⚖️ Más participaciones en partidos cerrados")
        mostrar_tabla(jugadores_cerrados, alto=320)

        jugadores_muchos_goles = (
            historial_filtrado[historial_filtrado["goles_totales"] >= umbral_goles_altos]
            .groupby("jugador")
            .size()
            .reset_index(name="Partidos de muchos goles")
            .sort_values(["Partidos de muchos goles", "jugador"], ascending=[False, True])
            .head(10)
            .rename(columns={"jugador": "Jugador"})
        )
        st.subheader("🔥 Más participaciones en partidos de muchos goles")
        mostrar_tabla(jugadores_muchos_goles, alto=320)

        jugadores_derrotas_amplias = (
            historial_filtrado[
                (historial_filtrado["resultado_jugador"] == "P")
                & (historial_filtrado["diferencia_goles"] >= umbral_goleada)
            ]
            .groupby("jugador")
            .size()
            .reset_index(name="Derrotas amplias")
            .sort_values(["Derrotas amplias", "jugador"], ascending=[False, True])
            .head(10)
            .rename(columns={"jugador": "Jugador"})
        )
        st.subheader("😬 Más participaciones en derrotas amplias")
        mostrar_tabla(jugadores_derrotas_amplias, alto=320)


# ==================================================
# DUPLAS Y RIVALIDADES
# ==================================================

with tab_duplas:
    min_pj = st.slider(
        "Mínimo de partidos para duplas/rivalidades",
        min_value=0,
        max_value=200,
        value=30,
        step=5
    )

    st.subheader("🤝 Curiosidades de duplas")
    if duplas.empty:
        st.info("No hay duplas en el período seleccionado.")
    else:
        c1, c2, c3 = st.columns(3)
        dupla_frecuente = duplas.sort_values(["PJ", "G", "Dupla"], ascending=[False, False, True]).iloc[0]
        c1.info(f"🤝 Dupla más frecuente\n\n**{dupla_frecuente['Dupla']}**\n\n{entero_seguro(dupla_frecuente['PJ'])} PJ")

        duplas_min = duplas[duplas["PJ"] >= min_pj].copy()
        if not duplas_min.empty:
            mejor_dupla = duplas_min.sort_values(["WinRate", "PJ", "G", "Dupla"], ascending=[False, False, False, True]).iloc[0]
            mas_derrotas_dupla = duplas_min.sort_values(["P", "PJ", "Dupla"], ascending=[False, False, True]).iloc[0]
            c2.info(f"🏆 Mejor Win Rate\n\n**{mejor_dupla['Dupla']}**\n\n{decimal_seguro(mejor_dupla['WinRate']):.1f}% WR")
            c3.info(f"⚠️ Más derrotas juntas\n\n**{mas_derrotas_dupla['Dupla']}**\n\n{entero_seguro(mas_derrotas_dupla['P'])} derrotas")

            st.subheader("🎭 Duplas más todo o nada")
            todo_o_nada = (
                duplas_min
                .sort_values(["% Empates", "PJ", "Dupla"], ascending=[True, False, True])
                [["Dupla", "PJ", "G", "E", "P", "% Empates", "WinRate"]]
                .head(10)
                .rename(columns={"WinRate": "Win Rate %"})
            )
            mostrar_tabla(todo_o_nada, alto=360)
        else:
            st.info("No hay duplas que cumplan el mínimo seleccionado.")

    st.divider()
    st.subheader("⚔️ Curiosidades de rivalidades")
    if rivales.empty:
        st.info("No hay rivalidades en el período seleccionado.")
    else:
        rivalidad_frecuente = rivales.sort_values(["pj", "jugador_1", "jugador_2"], ascending=[False, True, True]).iloc[0]
        rivales_min = rivales[rivales["pj"] >= min_pj].copy()

        c1, c2, c3 = st.columns(3)
        c1.info(
            "⚔️ Rivalidad más repetida\n\n"
            f"**{rivalidad_frecuente['jugador_1']} vs {rivalidad_frecuente['jugador_2']}**\n\n"
            f"{entero_seguro(rivalidad_frecuente['pj'])} enfrentamientos"
        )

        if not rivales_min.empty:
            rivales_min["Diferencia"] = (rivales_min["g_jugador_1"] - rivales_min["g_jugador_2"]).abs()
            mas_pareja = rivales_min.sort_values(["Diferencia", "pj"], ascending=[True, False]).iloc[0]
            paternidades = preparar_mayores_paternidades(rivales, min_pj)

            c2.info(
                "⚖️ Mano a mano más parejo\n\n"
                f"**{mas_pareja['jugador_1']} vs {mas_pareja['jugador_2']}**\n\n"
                f"Diferencia: {entero_seguro(mas_pareja['Diferencia'])}"
            )

            if not paternidades.empty:
                mayor_paternidad = paternidades.iloc[0]
                c3.info(
                    "👑 Mayor paternidad\n\n"
                    f"**{mayor_paternidad['Paternidad']}**\n\n"
                    f"Diferencia: {entero_seguro(mayor_paternidad['Diferencia'])}"
                )

            st.subheader("🤝 Rivalidades con más empates")
            mas_empates = (
                rivales_min
                .sort_values(["E", "pj", "jugador_1", "jugador_2"], ascending=[False, False, True, True])
                [["jugador_1", "jugador_2", "pj", "g_jugador_1", "g_jugador_2", "E"]]
                .head(10)
                .rename(
                    columns={
                        "jugador_1": "Jugador 1",
                        "jugador_2": "Jugador 2",
                        "pj": "PJ",
                        "g_jugador_1": "Victorias J1",
                        "g_jugador_2": "Victorias J2",
                        "E": "Empates"
                    }
                )
            )
            mostrar_tabla(mas_empates, alto=360)
        else:
            st.info("No hay rivalidades que cumplan el mínimo seleccionado.")


# ==================================================
# CALENDARIO
# ==================================================

with tab_calendario:
    evolucion = construir_evolucion_anual(partidos_filtrados)

    if evolucion.empty:
        st.info("No hay datos de calendario para el período seleccionado.")
    else:
        anio_mas_partidos = evolucion.sort_values(["Partidos", "Año"], ascending=[False, True]).iloc[0]
        anio_mas_goleador = evolucion.sort_values(["Promedio_goles", "Partidos", "Año"], ascending=[False, False, True]).iloc[0]
        anio_menos_goleador = evolucion.sort_values(["Promedio_goles", "Partidos", "Año"], ascending=[True, False, True]).iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.info(f"📆 Año con más partidos\n\n**{entero_seguro(anio_mas_partidos['Año'])}**\n\n{entero_seguro(anio_mas_partidos['Partidos'])} partidos")
        c2.info(f"🔥 Año más goleador\n\n**{entero_seguro(anio_mas_goleador['Año'])}**\n\n{decimal_seguro(anio_mas_goleador['Promedio_goles']):.2f} goles/partido")
        c3.info(f"🧊 Año menos goleador\n\n**{entero_seguro(anio_menos_goleador['Año'])}**\n\n{decimal_seguro(anio_menos_goleador['Promedio_goles']):.2f} goles/partido")

        st.subheader("📈 Evolución de partidos y goles")
        st.plotly_chart(construir_grafico_evolucion(evolucion), use_container_width=True)

        st.subheader("📅 Meses con más partidos")
        partidos_mes = (
            partidos_filtrados
            .groupby("Mes")
            .agg(
                Partidos=("id", "size"),
                Goles=("goles_totales", "sum"),
                Promedio_goles=("goles_totales", "mean")
            )
            .reset_index()
        )
        partidos_mes["Promedio_goles"] = partidos_mes["Promedio_goles"].round(2)
        partidos_mes = partidos_mes.sort_values(["Partidos", "Mes"], ascending=[False, True])
        mostrar_tabla(partidos_mes, alto=360)

        st.subheader("🔥 Meses más goleadores")
        mostrar_tabla(
            partidos_mes.sort_values(["Promedio_goles", "Partidos"], ascending=[False, False]),
            alto=360
        )
