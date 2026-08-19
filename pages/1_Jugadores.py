import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("👤 Jugadores")

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


def texto_seguro(valor, reemplazo="Sin datos"):
    if pd.isna(valor) or valor is None or str(valor).strip() == "":
        return reemplazo

    return str(valor)


def numero_entero_seguro(valor):
    if pd.isna(valor) or valor is None:
        return 0

    return int(valor)


def numero_decimal_seguro(valor):
    if pd.isna(valor) or valor is None:
        return 0.0

    return float(valor)


def emoji_equipo_favorito(equipo):
    equipo_texto = texto_seguro(equipo, "").lower()

    if "pesca" in equipo_texto or "pescas" in equipo_texto:
        return "🐟"

    if "dealer" in equipo_texto or "dealers" in equipo_texto:
        return "🚗"

    if "biologo" in equipo_texto or "biólogo" in equipo_texto:
        return "🦠"

    if "dhl" in equipo_texto:
        return "📦"

    return "🏅"


def etiqueta_racha(tipo_racha, cantidad):
    cantidad = numero_entero_seguro(cantidad)
    tipo_racha = texto_seguro(tipo_racha, "Sin datos")

    if tipo_racha == "G":
        return f"{cantidad} victoria(s)"

    if tipo_racha == "P":
        return f"{cantidad} derrota(s)"

    if tipo_racha == "E":
        return f"{cantidad} empate(s)"

    if tipo_racha == "Inactivo":
        return "Inactivo"

    return "Sin datos"


def obtener_fila_jugador(jugadores_df, nombre_jugador):
    fila = jugadores_df[jugadores_df["jugador"] == nombre_jugador]

    if fila.empty:
        return None

    return fila.iloc[0]


def obtener_companeros(jugador, parejas_df):
    companeros_jugador = parejas_df[
        (parejas_df["jugador_1"] == jugador)
        | (parejas_df["jugador_2"] == jugador)
    ].copy()

    if companeros_jugador.empty:
        return None, None, None

    companeros_jugador["companero"] = companeros_jugador.apply(
        lambda fila: (
            fila["jugador_2"]
            if fila["jugador_1"] == jugador
            else fila["jugador_1"]
        ),
        axis=1
    )

    companero_frecuente = (
        companeros_jugador
        .sort_values(
            ["PJ", "companero"],
            ascending=[False, True]
        )
        .iloc[0]
    )

    companeros_relevantes = companeros_jugador[
        companeros_jugador["PJ"] >= 30
    ].copy()

    if not companeros_relevantes.empty:
        mejor_companero = (
            companeros_relevantes
            .sort_values(
                ["WinRate", "PJ", "companero"],
                ascending=[False, False, True]
            )
            .iloc[0]
        )

        peor_companero = (
            companeros_relevantes
            .sort_values(
                ["WinRate", "PJ", "companero"],
                ascending=[True, False, True]
            )
            .iloc[0]
        )
    else:
        mejor_companero = companero_frecuente
        peor_companero = companero_frecuente

    return companero_frecuente, mejor_companero, peor_companero


def obtener_dupla(parejas_df, jugador_1, jugador_2):
    dupla = parejas_df[
        (
            (parejas_df["jugador_1"] == jugador_1)
            & (parejas_df["jugador_2"] == jugador_2)
        )
        |
        (
            (parejas_df["jugador_2"] == jugador_1)
            & (parejas_df["jugador_1"] == jugador_2)
        )
    ]

    if dupla.empty:
        return None

    return dupla.iloc[0]


def obtener_enfrentamiento(rivales_df, jugador_1, jugador_2):
    if rivales_df.empty:
        return None

    jugador_a, jugador_b = sorted([jugador_1, jugador_2])

    enfrentamiento = rivales_df[
        (rivales_df["jugador_1"] == jugador_a)
        & (rivales_df["jugador_2"] == jugador_b)
    ]

    if enfrentamiento.empty:
        return None

    datos = enfrentamiento.iloc[0]

    if jugador_1 == jugador_a:
        victorias_jugador_1 = numero_entero_seguro(datos.get("g_jugador_1"))
        victorias_jugador_2 = numero_entero_seguro(datos.get("g_jugador_2"))
        winrate_jugador_1 = numero_decimal_seguro(datos.get("winrate_jugador_1"))
        winrate_jugador_2 = numero_decimal_seguro(datos.get("winrate_jugador_2"))
    else:
        victorias_jugador_1 = numero_entero_seguro(datos.get("g_jugador_2"))
        victorias_jugador_2 = numero_entero_seguro(datos.get("g_jugador_1"))
        winrate_jugador_1 = numero_decimal_seguro(datos.get("winrate_jugador_2"))
        winrate_jugador_2 = numero_decimal_seguro(datos.get("winrate_jugador_1"))

    return {
        "pj": numero_entero_seguro(datos.get("pj")),
        "victorias_jugador_1": victorias_jugador_1,
        "victorias_jugador_2": victorias_jugador_2,
        "empates": numero_entero_seguro(datos.get("E")),
        "winrate_jugador_1": winrate_jugador_1,
        "winrate_jugador_2": winrate_jugador_2
    }


def obtener_rivales_jugador(rivales_df, jugador):
    if rivales_df.empty:
        return pd.DataFrame()

    registros = []

    for _, fila in rivales_df.iterrows():
        jugador_1 = fila.get("jugador_1")
        jugador_2 = fila.get("jugador_2")

        if jugador not in [jugador_1, jugador_2]:
            continue

        if jugador == jugador_1:
            rival = jugador_2
            victorias_jugador = numero_entero_seguro(fila.get("g_jugador_1"))
            victorias_rival = numero_entero_seguro(fila.get("g_jugador_2"))
            winrate = numero_decimal_seguro(fila.get("winrate_jugador_1"))
        else:
            rival = jugador_1
            victorias_jugador = numero_entero_seguro(fila.get("g_jugador_2"))
            victorias_rival = numero_entero_seguro(fila.get("g_jugador_1"))
            winrate = numero_decimal_seguro(fila.get("winrate_jugador_2"))

        registros.append(
            {
                "rival": rival,
                "pj": numero_entero_seguro(fila.get("pj")),
                "victorias_jugador": victorias_jugador,
                "victorias_rival": victorias_rival,
                "empates": numero_entero_seguro(fila.get("E")),
                "winrate": winrate
            }
        )

    return pd.DataFrame(registros)


def obtener_timeline_enfrentamientos(participaciones_df, jugador_1, jugador_2):
    registros = []

    participaciones_filtradas = participaciones_df[
        participaciones_df["jugador"].isin([jugador_1, jugador_2])
    ].copy()

    for _, grupo in participaciones_filtradas.groupby("partido_id"):
        jugadores_partido = set(grupo["jugador"].dropna().astype(str))

        if not {jugador_1, jugador_2}.issubset(jugadores_partido):
            continue

        fila_1 = grupo[grupo["jugador"] == jugador_1].iloc[0]
        fila_2 = grupo[grupo["jugador"] == jugador_2].iloc[0]

        if fila_1["equipo"] == fila_2["equipo"]:
            continue

        fecha = fila_1["fecha"]

        if pd.isna(fecha):
            continue

        resultado_1 = fila_1["resultado_jugador"]
        resultado_2 = fila_2["resultado_jugador"]

        registros.append(
            {
                "Año": fecha.year,
                f"Victorias {jugador_1}": 1 if resultado_1 == "G" else 0,
                "Empates": 1 if resultado_1 == "E" else 0,
                f"Victorias {jugador_2}": 1 if resultado_2 == "G" else 0,
                "Total": 1
            }
        )

    if not registros:
        return pd.DataFrame()

    return (
        pd.DataFrame(registros)
        .groupby("Año", as_index=False)
        .sum()
        .sort_values("Año")
    )


def obtener_timeline_dupla(participaciones_df, jugador_1, jugador_2):
    registros = []

    participaciones_filtradas = participaciones_df[
        participaciones_df["jugador"].isin([jugador_1, jugador_2])
    ].copy()

    for _, grupo in participaciones_filtradas.groupby("partido_id"):
        jugadores_partido = set(grupo["jugador"].dropna().astype(str))

        if not {jugador_1, jugador_2}.issubset(jugadores_partido):
            continue

        fila_1 = grupo[grupo["jugador"] == jugador_1].iloc[0]
        fila_2 = grupo[grupo["jugador"] == jugador_2].iloc[0]

        if fila_1["equipo"] != fila_2["equipo"]:
            continue

        fecha = fila_1["fecha"]

        if pd.isna(fecha):
            continue

        resultado = fila_1["resultado_jugador"]

        registros.append(
            {
                "Año": fecha.year,
                "Victorias": 1 if resultado == "G" else 0,
                "Empates": 1 if resultado == "E" else 0,
                "Derrotas": 1 if resultado == "P" else 0,
                "Total": 1
            }
        )

    if not registros:
        return pd.DataFrame()

    return (
        pd.DataFrame(registros)
        .groupby("Año", as_index=False)
        .sum()
        .sort_values("Año")
    )


def calcular_dupla_periodo(participaciones_df, jugador_1, jugador_2):
    registros = []

    participaciones_filtradas = participaciones_df[
        participaciones_df["jugador"].isin([jugador_1, jugador_2])
    ].copy()

    for _, grupo in participaciones_filtradas.groupby("partido_id"):
        jugadores_partido = set(grupo["jugador"].dropna().astype(str))

        if not {jugador_1, jugador_2}.issubset(jugadores_partido):
            continue

        fila_1 = grupo[grupo["jugador"] == jugador_1].iloc[0]
        fila_2 = grupo[grupo["jugador"] == jugador_2].iloc[0]

        if fila_1["equipo"] != fila_2["equipo"]:
            continue

        registros.append(fila_1["resultado_jugador"])

    pj = len(registros)
    g = registros.count("G")
    e = registros.count("E")
    p = registros.count("P")
    winrate = round(g / pj * 100, 2) if pj else 0

    return {
        "PJ": pj,
        "G": g,
        "E": e,
        "P": p,
        "WinRate": winrate
    }


def calcular_enfrentamiento_periodo(participaciones_df, jugador_1, jugador_2):
    resultados_jugador_1 = []

    participaciones_filtradas = participaciones_df[
        participaciones_df["jugador"].isin([jugador_1, jugador_2])
    ].copy()

    for _, grupo in participaciones_filtradas.groupby("partido_id"):
        jugadores_partido = set(grupo["jugador"].dropna().astype(str))

        if not {jugador_1, jugador_2}.issubset(jugadores_partido):
            continue

        fila_1 = grupo[grupo["jugador"] == jugador_1].iloc[0]
        fila_2 = grupo[grupo["jugador"] == jugador_2].iloc[0]

        if fila_1["equipo"] == fila_2["equipo"]:
            continue

        resultados_jugador_1.append(fila_1["resultado_jugador"])

    pj = len(resultados_jugador_1)

    if pj == 0:
        return None

    victorias_jugador_1 = resultados_jugador_1.count("G")
    empates = resultados_jugador_1.count("E")
    victorias_jugador_2 = resultados_jugador_1.count("P")

    return {
        "pj": pj,
        "victorias_jugador_1": victorias_jugador_1,
        "victorias_jugador_2": victorias_jugador_2,
        "empates": empates,
        "winrate_jugador_1": round(victorias_jugador_1 / pj * 100, 2),
        "winrate_jugador_2": round(victorias_jugador_2 / pj * 100, 2)
    }


def construir_grafico_dupla_timeline(timeline_df):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=timeline_df["Año"],
            y=timeline_df["Victorias"],
            name="Victorias",
            marker_color="#22C55E",
            hovertemplate=(
                "<b>Victorias</b><br>"
                "Año: %{x}<br>"
                "Cantidad: %{y}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Bar(
            x=timeline_df["Año"],
            y=timeline_df["Empates"],
            name="Empates",
            marker_color="#FACC15",
            hovertemplate=(
                "<b>Empates</b><br>"
                "Año: %{x}<br>"
                "Cantidad: %{y}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Bar(
            x=timeline_df["Año"],
            y=timeline_df["Derrotas"],
            name="Derrotas",
            marker_color="#EF4444",
            hovertemplate=(
                "<b>Derrotas</b><br>"
                "Año: %{x}<br>"
                "Cantidad: %{y}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=timeline_df["Año"],
            y=timeline_df["Total"],
            name="Total juntos",
            mode="lines+markers",
            line={
                "color": "white",
                "width": 3
            },
            marker={
                "size": 8,
                "color": "white"
            },
            hovertemplate=(
                "<b>Total juntos</b><br>"
                "Año: %{x}<br>"
                "Total: %{y}"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=420,
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": "white",
            "size": 13
        },
        xaxis={
            "title": "Año",
            "tickmode": "linear",
            "gridcolor": "rgba(255,255,255,0.12)"
        },
        yaxis={
            "title": "Partidos juntos",
            "gridcolor": "rgba(255,255,255,0.12)"
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "center",
            "x": 0.5
        },
        hoverlabel={
            "bgcolor": "#111827",
            "font_size": 13,
            "font_color": "white",
            "bordercolor": "rgba(255,255,255,0.35)"
        },
        margin={
            "l": 50,
            "r": 30,
            "t": 80,
            "b": 50
        }
    )

    return fig



def filtrar_historial_por_periodo(historial_df, periodo):
    if historial_df.empty or periodo == "Histórico":
        return historial_df.copy()

    fecha_maxima = historial_df["fecha"].max()

    if pd.isna(fecha_maxima):
        return historial_df.copy()

    if periodo == "Últimos 12 meses":
        fecha_minima = fecha_maxima - pd.Timedelta(days=365)
        return historial_df[historial_df["fecha"] >= fecha_minima].copy()

    if periodo == "Últimos 3 años":
        fecha_minima = fecha_maxima - pd.Timedelta(days=365 * 3)
        return historial_df[historial_df["fecha"] >= fecha_minima].copy()

    if periodo == "Desde 2020":
        return historial_df[historial_df["fecha"].dt.year >= 2020].copy()

    return historial_df.copy()


def calcular_racha_en_resultados(resultados, tipo):
    mejor = 0
    actual = 0

    for resultado in resultados:
        if resultado == tipo:
            actual += 1
            mejor = max(mejor, actual)
        else:
            actual = 0

    return mejor


def construir_info_periodo(jugador, info_historica, participaciones_df, periodo):
    if periodo == "Histórico":
        return info_historica

    historial_jugador = participaciones_df[
        participaciones_df["jugador"] == jugador
    ].copy()
    historial_jugador = filtrar_historial_por_periodo(
        historial_jugador,
        periodo
    )
    historial_jugador = historial_jugador.sort_values(
        ["fecha", "partido_id"]
    )

    resultados = historial_jugador["resultado_jugador"].tolist()
    pj = len(resultados)
    g = resultados.count("G")
    e = resultados.count("E")
    p = resultados.count("P")
    winrate = round(g / pj * 100, 2) if pj else 0

    datos = info_historica.copy()
    datos["PJ"] = pj
    datos["G"] = g
    datos["E"] = e
    datos["P"] = p
    datos["WinRate"] = winrate
    datos["mejor_racha_ganadora"] = calcular_racha_en_resultados(
        resultados,
        "G"
    )
    datos["peor_racha_perdedora"] = calcular_racha_en_resultados(
        resultados,
        "P"
    )

    return datos


def obtener_forma_reciente(historial_jugador, cantidad=8):
    return (
        historial_jugador
        .sort_values(["fecha", "partido_id"], ascending=[False, False])
        .head(cantidad)
        .copy()
    )


def render_forma_reciente(historial_jugador):
    ultimos = obtener_forma_reciente(historial_jugador)

    if ultimos.empty:
        st.info("No hay partidos recientes para mostrar.")
        return

    colores = {
        "G": "#22C55E",
        "E": "#FACC15",
        "P": "#EF4444"
    }

    chips = []

    for resultado in ultimos["resultado_jugador"].tolist():
        chips.append(
            "<span style='display:inline-block; padding:8px 12px; "
            f"margin:3px; border-radius:999px; background:{colores.get(resultado, '#64748B')}; "
            "color:#0B1120; font-weight:700;'>"
            f"{resultado}</span>"
        )

    st.markdown("".join(chips), unsafe_allow_html=True)

    pj = len(ultimos)
    g = int((ultimos["resultado_jugador"] == "G").sum())
    e = int((ultimos["resultado_jugador"] == "E").sum())
    p = int((ultimos["resultado_jugador"] == "P").sum())
    wr = g / pj * 100 if pj else 0

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("PJ recientes", pj)
    f2.metric("Victorias", g)
    f3.metric("Empates / Derrotas", f"{e} / {p}")
    f4.metric("WR reciente", f"{wr:.1f}%")


def construir_chips_forma_reciente(historial_jugador):
    ultimos = obtener_forma_reciente(historial_jugador)
    if ultimos.empty:
        return ""
    colores = {"G": "#22C55E", "E": "#FACC15", "P": "#EF4444"}
    chips = []
    for resultado in ultimos["resultado_jugador"].tolist():
        chips.append(
            "<span style='display:inline-flex; align-items:center; justify-content:center; "
            "width:30px; height:30px; margin:2px; border-radius:999px; "
            f"background:{colores.get(resultado, '#64748B')}; color:#0B1120; "
            "font-weight:800; font-size:14px;'>"
            f"{resultado}</span>"
        )
    return "".join(chips)


def construir_tabla_ultimos_partidos(historial_jugador):
    ultimos = (
        historial_jugador
        .sort_values(["fecha", "partido_id"], ascending=[False, False])
        .head(10)
        .copy()
    )

    if ultimos.empty:
        return pd.DataFrame()

    def marcador(fila):
        if pd.isna(fila.get("goles_local")) or pd.isna(fila.get("goles_visitante")):
            return "Sin datos"
        return f"{numero_entero_seguro(fila.get('goles_local'))}-{numero_entero_seguro(fila.get('goles_visitante'))}"

    def rival_equipo(fila):
        if fila.get("equipo") == fila.get("equipo_local"):
            return fila.get("equipo_visitante")
        return fila.get("equipo_local")

    tabla = pd.DataFrame(
        {
            "Fecha": ultimos["fecha"].dt.strftime("%d/%m/%Y"),
            "Equipo": ultimos["equipo"],
            "Resultado": ultimos["resultado_jugador"],
            "Marcador": ultimos.apply(marcador, axis=1),
            "Rival / Equipo rival": ultimos.apply(rival_equipo, axis=1)
        }
    )

    return tabla


def construir_rendimiento_por_equipo(historial_jugador):
    if historial_jugador.empty:
        return pd.DataFrame()

    rendimiento = (
        historial_jugador
        .pivot_table(
            index="equipo",
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

    rendimiento["PJ"] = rendimiento["G"] + rendimiento["E"] + rendimiento["P"]
    rendimiento["Win Rate %"] = (
        rendimiento["G"]
        / rendimiento["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return (
        rendimiento[["equipo", "PJ", "G", "E", "P", "Win Rate %"]]
        .rename(columns={"equipo": "Equipo"})
        .sort_values(["PJ", "Win Rate %", "Equipo"], ascending=[False, False, True])
    )


def construir_grafico_rendimiento_equipo(rendimiento_df):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=rendimiento_df["Equipo"],
            y=rendimiento_df["PJ"],
            name="PJ",
            marker_color="#38BDF8",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "PJ: %{y}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=rendimiento_df["Equipo"],
            y=rendimiento_df["Win Rate %"],
            mode="lines+markers",
            name="Win Rate %",
            yaxis="y2",
            line={"color": "#FACC15", "width": 3},
            marker={"size": 8, "color": "#FACC15"},
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Win Rate: %{y:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        yaxis={"title": "PJ", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis2={"title": "Win Rate %", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"}
    )

    return fig


def construir_wr_acumulado(historial_jugador):
    historial = historial_jugador.sort_values(["fecha", "partido_id"]).copy()

    if historial.empty:
        return None

    historial["PJ acumulado"] = range(1, len(historial) + 1)
    historial["Victorias acumuladas"] = (
        historial["resultado_jugador"] == "G"
    ).cumsum()
    historial["Win Rate acumulado"] = (
        historial["Victorias acumuladas"]
        / historial["PJ acumulado"]
        * 100
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=historial["fecha"],
            y=historial["Win Rate acumulado"],
            mode="lines",
            name="Win Rate acumulado",
            line={"color": "#22C55E", "width": 3},
            hovertemplate=(
                "Fecha: %{x|%d/%m/%Y}<br>"
                "WR acumulado: %{y:.1f}%"
                "<extra></extra>"
            )
        )
    )
    fig.update_layout(
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 13},
        xaxis={"title": "Fecha", "gridcolor": "rgba(255,255,255,0.12)"},
        yaxis={"title": "Win Rate acumulado %", "gridcolor": "rgba(255,255,255,0.12)"},
        hoverlabel={"bgcolor": "#111827", "font_color": "white"}
    )

    return fig


def obtener_posiciones_historicas(jugadores_df, jugador):
    posiciones = {}
    base = jugadores_df.copy()

    def ranking_columna(dataframe, columna, filtro=None):
        datos = dataframe.copy()

        if filtro is not None:
            datos = datos[filtro(datos)].copy()

        if jugador not in datos["jugador"].values:
            return None

        datos[columna] = pd.to_numeric(
            datos[columna],
            errors="coerce"
        ).fillna(0)

        ranking = datos[columna].rank(
            method="min",
            ascending=False
        )

        valor = ranking[datos["jugador"] == jugador].iloc[0]

        if pd.isna(valor):
            return None

        return int(valor)

    posiciones["Ranking PJ"] = ranking_columna(base, "PJ")
    posiciones["Ranking victorias"] = ranking_columna(base, "G")
    posiciones["Ranking WR +50 PJ"] = ranking_columna(
        base,
        "WinRate",
        filtro=lambda df: pd.to_numeric(
            df["PJ"],
            errors="coerce"
        ).fillna(0) >= 50
    )
    posiciones["Ranking mejor racha"] = ranking_columna(
        base,
        "mejor_racha_ganadora"
    )
    posiciones["Ranking peor racha"] = ranking_columna(
        base,
        "peor_racha_perdedora"
    )

    return posiciones


def construir_top_rivales(rivales_jugador):
    if rivales_jugador.empty:
        return pd.DataFrame()

    tabla = rivales_jugador.copy()
    tabla = tabla[tabla["pj"] >= 20].copy()

    if tabla.empty:
        return pd.DataFrame()

    tabla = tabla.rename(
        columns={
            "rival": "Rival",
            "pj": "PJ",
            "victorias_jugador": "Victorias jugador",
            "victorias_rival": "Victorias rival",
            "empates": "Empates",
            "winrate": "Win Rate %"
        }
    )

    return (
        tabla[["Rival", "PJ", "Victorias jugador", "Victorias rival", "Empates", "Win Rate %"]]
        .sort_values(["PJ", "Win Rate %", "Rival"], ascending=[False, False, True])
        .head(5)
    )


def construir_mejores_anios(evolucion_df):
    if evolucion_df.empty:
        return None

    anio_mas_pj = evolucion_df.sort_values(["PJ", "Año"], ascending=[False, True]).iloc[0]
    anio_mas_victorias = evolucion_df.sort_values(["PG", "Año"], ascending=[False, True]).iloc[0]
    candidatos_wr = evolucion_df[evolucion_df["PJ"] >= 10].copy()

    if candidatos_wr.empty:
        anio_mejor_wr = evolucion_df.sort_values(["WinRate", "PJ", "Año"], ascending=[False, False, True]).iloc[0]
    else:
        anio_mejor_wr = candidatos_wr.sort_values(["WinRate", "PJ", "Año"], ascending=[False, False, True]).iloc[0]

    return anio_mas_pj, anio_mas_victorias, anio_mejor_wr


def construir_diferencias_comparacion(info_1, info_2, jugador_1, jugador_2):
    diferencias = []
    metricas = [
        ("PJ", "PJ", "partidos"),
        ("G", "Victorias", "victorias"),
        ("WinRate", "Win Rate", "puntos"),
        ("mejor_racha_ganadora", "Mejor racha", "partidos"),
        ("peor_racha_perdedora", "Peor racha", "partidos")
    ]

    for columna, etiqueta, unidad in metricas:
        valor_1 = numero_decimal_seguro(info_1.get(columna))
        valor_2 = numero_decimal_seguro(info_2.get(columna))
        diferencia = round(abs(valor_1 - valor_2), 1)

        if valor_1 > valor_2:
            diferencias.append(f"{etiqueta}: +{diferencia:g} {unidad} para {jugador_1}")
        elif valor_2 > valor_1:
            diferencias.append(f"{etiqueta}: +{diferencia:g} {unidad} para {jugador_2}")
        else:
            diferencias.append(f"{etiqueta}: sin diferencia")

    return diferencias


def obtener_quimica_dupla(datos_dupla):
    pj = numero_entero_seguro(datos_dupla.get("PJ"))
    wr = numero_decimal_seguro(datos_dupla.get("WinRate"))

    if pj < 20:
        return "Muestra chica: todavía hay pocos partidos juntos."

    if pj >= 50 and wr >= 55:
        return "Dupla muy efectiva: muchos partidos juntos y alto Win Rate."

    if pj >= 50 and wr >= 45:
        return "Dupla equilibrada: rendimiento sólido en una muestra importante."

    if pj >= 50:
        return "Dupla con rendimiento bajo: muchos partidos juntos, pero Win Rate debajo del 45%."

    if wr >= 55:
        return "Dupla prometedora: buen Win Rate, aunque con muestra moderada."

    return "Dupla en desarrollo: muestra moderada y rendimiento mejorable."


def construir_comparacion(info_1, info_2, jugador_1, jugador_2):
    datos = [
        {
            "Métrica": "PJ",
            jugador_1: numero_entero_seguro(info_1.get("PJ")),
            jugador_2: numero_entero_seguro(info_2.get("PJ"))
        },
        {
            "Métrica": "Victorias",
            jugador_1: numero_entero_seguro(info_1.get("G")),
            jugador_2: numero_entero_seguro(info_2.get("G"))
        },
        {
            "Métrica": "Empates",
            jugador_1: numero_entero_seguro(info_1.get("E")),
            jugador_2: numero_entero_seguro(info_2.get("E"))
        },
        {
            "Métrica": "Derrotas",
            jugador_1: numero_entero_seguro(info_1.get("P")),
            jugador_2: numero_entero_seguro(info_2.get("P"))
        },
        {
            "Métrica": "Win Rate %",
            jugador_1: f"{numero_decimal_seguro(info_1.get('WinRate')):.1f}%",
            jugador_2: f"{numero_decimal_seguro(info_2.get('WinRate')):.1f}%"
        },
        {
            "Métrica": "Equipo favorito",
            jugador_1: texto_seguro(info_1.get("equipo_favorito")),
            jugador_2: texto_seguro(info_2.get("equipo_favorito"))
        },
        {
            "Métrica": "Rival más frecuente",
            jugador_1: texto_seguro(info_1.get("rival_mas_frecuente")),
            jugador_2: texto_seguro(info_2.get("rival_mas_frecuente"))
        },
        {
            "Métrica": "PJ vs rival frecuente",
            jugador_1: numero_entero_seguro(info_1.get("pj_vs_rival_mas_frecuente")),
            jugador_2: numero_entero_seguro(info_2.get("pj_vs_rival_mas_frecuente"))
        },
        {
            "Métrica": "Mejor racha positiva",
            jugador_1: numero_entero_seguro(info_1.get("mejor_racha_ganadora")),
            jugador_2: numero_entero_seguro(info_2.get("mejor_racha_ganadora"))
        },
        {
            "Métrica": "Peor racha negativa",
            jugador_1: numero_entero_seguro(info_1.get("peor_racha_perdedora")),
            jugador_2: numero_entero_seguro(info_2.get("peor_racha_perdedora"))
        },
        {
            "Métrica": "Racha activa",
            jugador_1: etiqueta_racha(
                info_1.get("tipo_racha_activa"),
                info_1.get("racha_activa")
            ),
            jugador_2: etiqueta_racha(
                info_2.get("tipo_racha_activa"),
                info_2.get("racha_activa")
            )
        }
    ]

    return pd.DataFrame(datos)


def construir_barras_comparacion(info_1, info_2, jugador_1, jugador_2):
    metricas = [
        "PJ",
        "Victorias",
        "Win Rate %",
        "Mejor racha positiva",
        "Peor racha negativa"
    ]

    valores_jugador_1 = [
        numero_decimal_seguro(info_1.get("PJ")),
        numero_decimal_seguro(info_1.get("G")),
        numero_decimal_seguro(info_1.get("WinRate")),
        numero_decimal_seguro(info_1.get("mejor_racha_ganadora")),
        numero_decimal_seguro(info_1.get("peor_racha_perdedora"))
    ]

    valores_jugador_2 = [
        numero_decimal_seguro(info_2.get("PJ")),
        numero_decimal_seguro(info_2.get("G")),
        numero_decimal_seguro(info_2.get("WinRate")),
        numero_decimal_seguro(info_2.get("mejor_racha_ganadora")),
        numero_decimal_seguro(info_2.get("peor_racha_perdedora"))
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=metricas,
            x=valores_jugador_1,
            name=jugador_1,
            orientation="h",
            marker_color="#00C2FF",
            text=[f"{valor:.1f}" for valor in valores_jugador_1],
            textposition="outside",
            hovertemplate=(
                f"<b>{jugador_1}</b><br>"
                "%{y}: %{x:.1f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Bar(
            y=metricas,
            x=valores_jugador_2,
            name=jugador_2,
            orientation="h",
            marker_color="#FFB000",
            text=[f"{valor:.1f}" for valor in valores_jugador_2],
            textposition="outside",
            hovertemplate=(
                f"<b>{jugador_2}</b><br>"
                "%{y}: %{x:.1f}"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=460,
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": "white",
            "size": 13
        },
        xaxis={
            "title": "Valor",
            "gridcolor": "rgba(255,255,255,0.15)"
        },
        yaxis={
            "title": ""
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "center",
            "x": 0.5
        },
        hoverlabel={
            "bgcolor": "#111827",
            "font_size": 13,
            "font_color": "white",
            "bordercolor": "rgba(255,255,255,0.35)"
        },
        margin={
            "l": 140,
            "r": 40,
            "t": 70,
            "b": 40
        }
    )

    return fig


def construir_grafico_enfrentamiento(enfrentamiento, jugador_1, jugador_2):
    total = max(numero_entero_seguro(enfrentamiento.get("pj")), 1)
    victorias_1 = numero_entero_seguro(enfrentamiento.get("victorias_jugador_1"))
    victorias_2 = numero_entero_seguro(enfrentamiento.get("victorias_jugador_2"))
    empates = numero_entero_seguro(enfrentamiento.get("empates"))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=["Enfrentamiento directo"],
            x=[victorias_1],
            name=f"Victorias {jugador_1}",
            orientation="h",
            marker_color="#00C2FF",
            text=[f"{victorias_1}"],
            textposition="inside",
            hovertemplate=(
                f"<b>{jugador_1}</b><br>"
                "Victorias directas: %{x}<br>"
                f"Participación: {victorias_1 / total * 100:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Bar(
            y=["Enfrentamiento directo"],
            x=[empates],
            name="Empates",
            orientation="h",
            marker_color="#94A3B8",
            text=[f"{empates}"],
            textposition="inside",
            hovertemplate=(
                "<b>Empates</b><br>"
                "Empates: %{x}<br>"
                f"Participación: {empates / total * 100:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Bar(
            y=["Enfrentamiento directo"],
            x=[victorias_2],
            name=f"Victorias {jugador_2}",
            orientation="h",
            marker_color="#FFB000",
            text=[f"{victorias_2}"],
            textposition="inside",
            hovertemplate=(
                f"<b>{jugador_2}</b><br>"
                "Victorias directas: %{x}<br>"
                f"Participación: {victorias_2 / total * 100:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=260,
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": "white",
            "size": 13
        },
        xaxis={
            "title": "Partidos enfrentados",
            "range": [0, total],
            "gridcolor": "rgba(255,255,255,0.15)"
        },
        yaxis={
            "title": "",
            "showticklabels": False
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.05,
            "xanchor": "center",
            "x": 0.5
        },
        margin={
            "l": 20,
            "r": 20,
            "t": 70,
            "b": 40
        }
    )

    return fig


def resumen_comparacion(info_1, info_2, jugador_1, jugador_2, enfrentamiento):
    mensajes = []

    pj_1 = numero_entero_seguro(info_1.get("PJ"))
    pj_2 = numero_entero_seguro(info_2.get("PJ"))
    wr_1 = numero_decimal_seguro(info_1.get("WinRate"))
    wr_2 = numero_decimal_seguro(info_2.get("WinRate"))
    g_1 = numero_entero_seguro(info_1.get("G"))
    g_2 = numero_entero_seguro(info_2.get("G"))
    mejor_racha_1 = numero_entero_seguro(info_1.get("mejor_racha_ganadora"))
    mejor_racha_2 = numero_entero_seguro(info_2.get("mejor_racha_ganadora"))

    if pj_1 > pj_2:
        mensajes.append(f"{jugador_1} tiene más partidos jugados históricamente.")
    elif pj_2 > pj_1:
        mensajes.append(f"{jugador_2} tiene más partidos jugados históricamente.")

    if g_1 > g_2:
        mensajes.append(f"{jugador_1} suma más victorias totales.")
    elif g_2 > g_1:
        mensajes.append(f"{jugador_2} suma más victorias totales.")

    if wr_1 > wr_2:
        mensajes.append(f"{jugador_1} tiene mejor Win Rate histórico.")
    elif wr_2 > wr_1:
        mensajes.append(f"{jugador_2} tiene mejor Win Rate histórico.")

    if mejor_racha_1 > mejor_racha_2:
        mensajes.append(f"{jugador_1} tiene mejor racha positiva histórica.")
    elif mejor_racha_2 > mejor_racha_1:
        mensajes.append(f"{jugador_2} tiene mejor racha positiva histórica.")

    if enfrentamiento is not None and enfrentamiento["pj"] > 0:
        if enfrentamiento["victorias_jugador_1"] > enfrentamiento["victorias_jugador_2"]:
            diferencia = enfrentamiento["victorias_jugador_1"] - enfrentamiento["victorias_jugador_2"]
            mensajes.append(f"En enfrentamientos directos, {jugador_1} lidera por {diferencia} victoria(s).")
        elif enfrentamiento["victorias_jugador_2"] > enfrentamiento["victorias_jugador_1"]:
            diferencia = enfrentamiento["victorias_jugador_2"] - enfrentamiento["victorias_jugador_1"]
            mensajes.append(f"En enfrentamientos directos, {jugador_2} lidera por {diferencia} victoria(s).")
        else:
            mensajes.append("El historial de enfrentamientos directos está empatado en victorias.")

    if not mensajes:
        mensajes.append("La comparación está muy pareja en las métricas principales.")

    return mensajes


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    participaciones = leer_tabla_completa("participaciones")
    parejas = leer_tabla_completa("estadisticas_parejas")
    rivales = leer_tabla_completa("estadisticas_rivales")
    partidos = leer_tabla_completa("partidos")

except Exception as error:
    st.error("No se pudieron leer los datos desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
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

columnas_jugadores = [
    "jugador",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate",
    "equipo_favorito",
    "rival_mas_frecuente",
    "pj_vs_rival_mas_frecuente",
    "mejor_racha_ganadora",
    "peor_racha_perdedora",
    "racha_activa",
    "tipo_racha_activa"
]

columnas_participaciones = [
    "partido_id",
    "jugador",
    "equipo"
]

columnas_parejas = [
    "jugador_1",
    "jugador_2",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
]

columnas_rivales = [
    "jugador_1",
    "jugador_2",
    "pj",
    "g_jugador_1",
    "g_jugador_2",
    "E",
    "winrate_jugador_1",
    "winrate_jugador_2"
]

columnas_partidos = [
    "id",
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

validaciones = [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("participaciones", participaciones, columnas_participaciones),
    ("estadisticas_parejas", parejas, columnas_parejas),
    ("partidos", partidos, columnas_partidos)
]

if not rivales.empty:
    validaciones.append(
        ("estadisticas_rivales", rivales, columnas_rivales)
    )

for nombre_tabla, dataframe, columnas_requeridas in validaciones:
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
# PREPARACION DEL HISTORIAL
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

partidos["resultado_local"] = "E"

partidos.loc[
    partidos["goles_local"] > partidos["goles_visitante"],
    "resultado_local"
] = "G"

partidos.loc[
    partidos["goles_local"] < partidos["goles_visitante"],
    "resultado_local"
] = "P"

participaciones_historial = participaciones.merge(
    partidos[
        [
            "id",
            "fecha",
            "equipo_local",
            "equipo_visitante",
            "goles_local",
            "goles_visitante",
            "resultado_local"
        ]
    ],
    left_on="partido_id",
    right_on="id",
    how="left",
    suffixes=("", "_partido")
)

participaciones_historial["resultado_jugador"] = ""

mask_local = (
    participaciones_historial["equipo"]
    == participaciones_historial["equipo_local"]
)

mask_visitante = (
    participaciones_historial["equipo"]
    == participaciones_historial["equipo_visitante"]
)

participaciones_historial.loc[
    mask_local,
    "resultado_jugador"
] = participaciones_historial["resultado_local"]

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "G"),
    "resultado_jugador"
] = "P"

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "P"),
    "resultado_jugador"
] = "G"

participaciones_historial.loc[
    mask_visitante
    & (participaciones_historial["resultado_local"] == "E"),
    "resultado_jugador"
] = "E"

participaciones_historial = participaciones_historial[
    participaciones_historial["fecha"].notna()
    & participaciones_historial["resultado_jugador"].isin(["G", "E", "P"])
].copy()


# ==================================================
# NORMALIZACION NUMERICA
# ==================================================

for columna in [
    "PJ",
    "G",
    "E",
    "P",
    "racha_activa",
    "mejor_racha_ganadora",
    "peor_racha_perdedora",
    "pj_vs_rival_mas_frecuente"
]:
    if columna in jugadores.columns:
        jugadores[columna] = pd.to_numeric(
            jugadores[columna],
            errors="coerce"
        )

jugadores["WinRate"] = pd.to_numeric(
    jugadores["WinRate"],
    errors="coerce"
)

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    parejas[columna] = pd.to_numeric(
        parejas[columna],
        errors="coerce"
    )

for columna in [
    "pj",
    "g_jugador_1",
    "g_jugador_2",
    "E",
    "winrate_jugador_1",
    "winrate_jugador_2"
]:
    if columna in rivales.columns:
        rivales[columna] = pd.to_numeric(
            rivales[columna],
            errors="coerce"
        )


# ==================================================
# LISTAS Y TABS
# ==================================================

lista_jugadores = sorted(
    jugadores["jugador"]
    .dropna()
    .astype(str)
    .unique()
)

tab_perfil, tab_comparador = st.tabs(
    [
        "👤 Perfil del jugador",
        "⚔️ Comparar jugadores"
    ]
)


# ==================================================
# TAB PERFIL DEL JUGADOR
# ==================================================

with tab_perfil:
    jugador = st.selectbox(
        "🔎 Buscar jugador",
        lista_jugadores,
        index=None,
        placeholder="Escribí el nombre del jugador...",
        key="selector_perfil_jugador"
    )

    if jugador is None:
        st.info("Seleccioná un jugador para ver sus estadísticas.")
    else:
        filas_jugador = jugadores[
            jugadores["jugador"] == jugador
        ]

        if filas_jugador.empty:
            st.warning("No se encontraron datos para el jugador seleccionado.")
        else:
            info = filas_jugador.iloc[0]

            companero_frecuente, mejor_companero, peor_companero = obtener_companeros(
                jugador,
                parejas
            )

            racha_activa = numero_entero_seguro(info.get("racha_activa"))
            mejor_racha = numero_entero_seguro(info.get("mejor_racha_ganadora"))
            peor_racha = numero_entero_seguro(info.get("peor_racha_perdedora"))
            pj_rival = numero_entero_seguro(info.get("pj_vs_rival_mas_frecuente"))
            tipo_racha_activa = texto_seguro(
                info.get("tipo_racha_activa"),
                "Sin datos"
            )

            historial = participaciones_historial[
                participaciones_historial["jugador"] == jugador
            ].copy()

            emoji_equipo = emoji_equipo_favorito(
                info.get("equipo_favorito")
            )

            header_col, forma_col = st.columns([2, 1])
            with header_col:
                st.header(f"{emoji_equipo} {jugador}")
                st.caption(
                    "Referencias de equipo favorito: 🐟 Pescas · 🚗 Dealers · 🦠 Biólogos · 📦 DHL"
                )
            with forma_col:
                chips_forma = construir_chips_forma_reciente(historial)
                if chips_forma:
                    st.caption("Forma reciente")
                    st.markdown(chips_forma, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("PJ", numero_entero_seguro(info.get("PJ")))
            c2.metric("Victorias", numero_entero_seguro(info.get("G")))
            c3.metric("Derrotas", numero_entero_seguro(info.get("P")))
            c4.metric(
                "Win Rate",
                f"{numero_decimal_seguro(info.get('WinRate')):.1f}%"
            )

            st.divider()

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Racha Activa",
                racha_activa,
                help=f"Tipo de racha: {tipo_racha_activa}"
            )
            c2.metric("Mejor Racha", mejor_racha)
            c3.metric("Peor Racha", peor_racha)
            c4.metric("Empates", numero_entero_seguro(info.get("E")))
            st.divider()
            st.subheader("🏛️ Posiciones históricas")
            posiciones = obtener_posiciones_historicas(
                jugadores,
                jugador
            )
            p1, p2, p3, p4, p5 = st.columns(5)
            p1.metric("PJ", f"#{posiciones['Ranking PJ']}")
            p2.metric("Victorias", f"#{posiciones['Ranking victorias']}")
            p3.metric(
                "Win Rate +50 PJ",
                (
                    f"#{posiciones['Ranking WR +50 PJ']}"
                    if posiciones["Ranking WR +50 PJ"] is not None
                    else "Sin ranking"
                )
            )
            p4.metric("Mejor racha", f"#{posiciones['Ranking mejor racha']}")
            p5.metric("Peor racha", f"#{posiciones['Ranking peor racha']}")

            st.divider()

            c1, c2 = st.columns(2)

            with c1:
                if companero_frecuente is not None:
                    st.info(
                        "🤝 Compañero más frecuente: "
                        f"{companero_frecuente['companero']} "
                        f"({numero_entero_seguro(companero_frecuente['PJ'])} PJ)"
                    )
                else:
                    st.info("🤝 Compañero más frecuente: Sin datos")

                if mejor_companero is not None:
                    st.info(
                        "🏆 Mejor compañero: "
                        f"{mejor_companero['companero']} "
                        f"({numero_decimal_seguro(mejor_companero['WinRate']):.1f}% WR)"
                    )
                else:
                    st.info("🏆 Mejor compañero: Sin datos")

            with c2:
                st.info(
                    "🥊 Rival más frecuente: "
                    f"{texto_seguro(info.get('rival_mas_frecuente'))} "
                    f"({pj_rival} PJ)"
                )

                if peor_companero is not None:
                    st.info(
                        "📉 Peor compañero: "
                        f"{peor_companero['companero']} "
                        f"({numero_decimal_seguro(peor_companero['WinRate']):.1f}% WR)"
                    )
                else:
                    st.info("📉 Peor compañero: Sin datos")


            rivales_jugador = obtener_rivales_jugador(
                rivales,
                jugador
            )

            if not rivales_jugador.empty:
                rivales_con_minimo = rivales_jugador[
                    rivales_jugador["pj"] >= 20
                ].copy()

                if not rivales_con_minimo.empty:
                    st.divider()
                    st.subheader("⚔️ Rivales destacados")

                    rival_mas_vencido = (
                        rivales_con_minimo
                        .sort_values(
                            ["victorias_jugador", "pj", "rival"],
                            ascending=[False, False, True]
                        )
                        .iloc[0]
                    )

                    rival_que_mas_le_gano = (
                        rivales_con_minimo
                        .sort_values(
                            ["victorias_rival", "pj", "rival"],
                            ascending=[False, False, True]
                        )
                        .iloc[0]
                    )

                    mejor_porcentaje = (
                        rivales_con_minimo
                        .sort_values(
                            ["winrate", "pj", "rival"],
                            ascending=[False, False, True]
                        )
                        .iloc[0]
                    )

                    peor_porcentaje = (
                        rivales_con_minimo
                        .sort_values(
                            ["winrate", "pj", "rival"],
                            ascending=[True, False, True]
                        )
                        .iloc[0]
                    )

                    fila_1_col_1, fila_1_col_2 = st.columns(2)
                    fila_2_col_1, fila_2_col_2 = st.columns(2)

                    with fila_1_col_1:
                        st.info(
                            "✅ Más victorias contra\n\n"
                            f"**{texto_seguro(rival_mas_vencido['rival'])}**\n\n"
                            f"{numero_entero_seguro(rival_mas_vencido['victorias_jugador'])} victorias "
                            f"en {numero_entero_seguro(rival_mas_vencido['pj'])} enfrentamientos"
                        )

                    with fila_1_col_2:
                        st.info(
                            "📈 Mejor Win Rate vs rival\n\n"
                            f"**{texto_seguro(mejor_porcentaje['rival'])}**\n\n"
                            f"{numero_decimal_seguro(mejor_porcentaje['winrate']):.1f}% WR "
                            f"en {numero_entero_seguro(mejor_porcentaje['pj'])} enfrentamientos"
                        )

                    with fila_2_col_1:
                        st.info(
                            "⚠️ Más derrotas contra\n\n"
                            f"**{texto_seguro(rival_que_mas_le_gano['rival'])}**\n\n"
                            f"{numero_entero_seguro(rival_que_mas_le_gano['victorias_rival'])} derrotas "
                            f"en {numero_entero_seguro(rival_que_mas_le_gano['pj'])} enfrentamientos"
                        )

                    with fila_2_col_2:
                        st.info(
                            "📉 Peor Win Rate vs rival\n\n"
                            f"**{texto_seguro(peor_porcentaje['rival'])}**\n\n"
                            f"{numero_decimal_seguro(peor_porcentaje['winrate']):.1f}% WR "
                            f"en {numero_entero_seguro(peor_porcentaje['pj'])} enfrentamientos"
                        )

                    st.caption(
                        "Se consideran solo rivales con al menos 20 enfrentamientos."
                    )

                    top_rivales = construir_top_rivales(rivales_jugador)
                    if not top_rivales.empty:
                        st.subheader("⚔️ Top 5 rivales por enfrentamientos")
                        st.dataframe(
                            top_rivales,
                            use_container_width=True,
                            hide_index=True,
                            height=260
                        )

            historial["Año"] = historial["fecha"].dt.year

            evolucion = (
                historial
                .groupby("Año")
                .agg(
                    PJ=("resultado_jugador", "size"),
                    PG=(
                        "resultado_jugador",
                        lambda resultados: (resultados == "G").sum()
                    )
                )
                .reset_index()
            )

            if not evolucion.empty:
                evolucion["WinRate"] = (
                    evolucion["PG"]
                    / evolucion["PJ"].replace(0, pd.NA)
                    * 100
                ).round(1).fillna(0)

            st.divider()
            st.subheader("🏟️ Rendimiento por equipo")
            rendimiento_equipo = construir_rendimiento_por_equipo(historial)

            if not rendimiento_equipo.empty:
                rendimiento_equipo = rendimiento_equipo.head(4).copy()

            if rendimiento_equipo.empty:
                st.info("No hay rendimiento por equipo para mostrar.")
            else:
                equipo_mas_usado = rendimiento_equipo.iloc[0]
                candidatos_mejor_equipo = rendimiento_equipo[
                    rendimiento_equipo["PJ"] >= 20
                ].copy()
                if candidatos_mejor_equipo.empty:
                    mejor_equipo_wr = rendimiento_equipo.sort_values(
                        ["Win Rate %", "PJ", "Equipo"],
                        ascending=[False, False, True]
                    ).iloc[0]
                else:
                    mejor_equipo_wr = candidatos_mejor_equipo.sort_values(
                        ["Win Rate %", "PJ", "Equipo"],
                        ascending=[False, False, True]
                    ).iloc[0]

                e1, e2 = st.columns(2)
                e1.info(
                    "🏟️ Equipo más usado\n\n"
                    f"**{texto_seguro(equipo_mas_usado['Equipo'])}**\n\n"
                    f"{numero_entero_seguro(equipo_mas_usado['PJ'])} partidos"
                )
                e2.info(
                    "🎯 Mejor rendimiento\n\n"
                    f"**{texto_seguro(mejor_equipo_wr['Equipo'])}**\n\n"
                    f"{numero_decimal_seguro(mejor_equipo_wr['Win Rate %']):.1f}% WR "
                    f"en {numero_entero_seguro(mejor_equipo_wr['PJ'])} partidos"
                )

                st.plotly_chart(
                    construir_grafico_rendimiento_equipo(rendimiento_equipo),
                    use_container_width=True
                )

            if not evolucion.empty:
                mejores_anios = construir_mejores_anios(evolucion)
                if mejores_anios is not None:
                    anio_mas_pj, anio_mas_victorias, anio_mejor_wr = mejores_anios
                    st.divider()
                    st.subheader("📆 Mejores años")
                    a1, a2, a3 = st.columns(3)
                    a1.info(
                        "📌 Año con más partidos\n\n"
                        f"**{numero_entero_seguro(anio_mas_pj['Año'])}**\n\n"
                        f"{numero_entero_seguro(anio_mas_pj['PJ'])} PJ"
                    )
                    a2.info(
                        "🏆 Año con más victorias\n\n"
                        f"**{numero_entero_seguro(anio_mas_victorias['Año'])}**\n\n"
                        f"{numero_entero_seguro(anio_mas_victorias['PG'])} victorias"
                    )
                    a3.info(
                        "🎯 Mejor año por Win Rate\n\n"
                        f"**{numero_entero_seguro(anio_mejor_wr['Año'])}**\n\n"
                        f"{numero_decimal_seguro(anio_mejor_wr['WinRate']):.1f}% WR"
                    )

            st.divider()
            st.subheader("📈 Evolución histórica")

            if evolucion.empty:
                st.info("No hay datos históricos para mostrar.")
            else:
                fig = go.Figure()

                fig.add_bar(
                    x=evolucion["Año"],
                    y=evolucion["PJ"],
                    name="Partidos Jugados"
                )

                fig.add_trace(
                    go.Scatter(
                        x=evolucion["Año"],
                        y=evolucion["PG"],
                        mode="lines+markers",
                        name="Victorias"
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=evolucion["Año"],
                        y=evolucion["WinRate"],
                        mode="lines+markers",
                        name="Win Rate %",
                        yaxis="y2"
                    )
                )

                fig.update_layout(
                    height=550,
                    hovermode="x unified",
                    xaxis_title="Año",
                    yaxis={
                        "title": "Partidos / Victorias"
                    },
                    yaxis2={
                        "title": "Win Rate %",
                        "overlaying": "y",
                        "side": "right"
                    },
                    legend={
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "right",
                        "x": 1
                    }
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            st.divider()
            st.subheader("📅 Últimos 10 partidos")
            ultimos_partidos = construir_tabla_ultimos_partidos(historial)
            if ultimos_partidos.empty:
                st.info("No hay últimos partidos disponibles para mostrar.")
            else:
                st.dataframe(
                    ultimos_partidos,
                    use_container_width=True,
                    hide_index=True,
                    height=380
                )

            fig_wr_acumulado = construir_wr_acumulado(historial)
            if fig_wr_acumulado is not None:
                st.divider()
                st.subheader("📈 Win Rate acumulado")
                st.plotly_chart(
                    fig_wr_acumulado,
                    use_container_width=True
                )


# ==================================================
# TAB COMPARADOR
# ==================================================

with tab_comparador:
    st.subheader("⚔️ Comparar jugadores")
    st.caption(
        "Seleccioná dos jugadores para comparar rendimiento histórico, dupla y enfrentamientos directos."
    )

    col_1, col_2 = st.columns(2)

    with col_1:
        jugador_1 = st.selectbox(
            "Jugador 1",
            lista_jugadores,
            index=None,
            placeholder="Seleccioná el primer jugador...",
            key="comparador_jugador_1"
        )

    with col_2:
        jugador_2 = st.selectbox(
            "Jugador 2",
            lista_jugadores,
            index=None,
            placeholder="Seleccioná el segundo jugador...",
            key="comparador_jugador_2"
        )

    periodo_comparacion = st.selectbox(
        "Período de comparación",
        [
            "Histórico",
            "Últimos 12 meses",
            "Últimos 3 años",
            "Desde 2020"
        ],
        index=0,
        key="periodo_comparacion_jugadores"
    )

    if jugador_1 is None or jugador_2 is None:
        st.info("Seleccioná dos jugadores para ver la comparación.")
    elif jugador_1 == jugador_2:
        st.warning("Seleccioná dos jugadores distintos para comparar.")
    else:
        info_1_base = obtener_fila_jugador(jugadores, jugador_1)
        info_2_base = obtener_fila_jugador(jugadores, jugador_2)

        if info_1_base is None or info_2_base is None:
            st.warning("No se encontraron datos para alguno de los jugadores seleccionados.")
        else:
            info_1 = construir_info_periodo(
                jugador_1,
                info_1_base,
                participaciones_historial,
                periodo_comparacion
            )
            info_2 = construir_info_periodo(
                jugador_2,
                info_2_base,
                participaciones_historial,
                periodo_comparacion
            )

            participaciones_periodo = filtrar_historial_por_periodo(
                participaciones_historial,
                periodo_comparacion
            )
            enfrentamiento = calcular_enfrentamiento_periodo(
                participaciones_periodo,
                jugador_1,
                jugador_2
            )

            st.divider()
            st.subheader(f"📊 {jugador_1} vs {jugador_2}")
            st.caption(f"Período seleccionado: {periodo_comparacion}")

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                f"PJ {jugador_1}",
                numero_entero_seguro(info_1.get("PJ"))
            )
            c2.metric(
                f"PJ {jugador_2}",
                numero_entero_seguro(info_2.get("PJ"))
            )
            c3.metric(
                f"WR {jugador_1}",
                f"{numero_decimal_seguro(info_1.get('WinRate')):.1f}%"
            )
            c4.metric(
                f"WR {jugador_2}",
                f"{numero_decimal_seguro(info_2.get('WinRate')):.1f}%"
            )

            st.divider()
            st.subheader("📊 Comparación")

            fig_comparacion = construir_barras_comparacion(
                info_1,
                info_2,
                jugador_1,
                jugador_2
            )

            st.plotly_chart(
                fig_comparacion,
                use_container_width=True
            )

            st.subheader("➕ Diferencias principales")
            for diferencia in construir_diferencias_comparacion(
                info_1,
                info_2,
                jugador_1,
                jugador_2
            ):
                st.info(diferencia)

            st.divider()
            st.subheader("🤝 Como dupla")

            datos_dupla = calcular_dupla_periodo(
                participaciones_periodo,
                jugador_1,
                jugador_2
            )

            if numero_entero_seguro(datos_dupla.get("PJ")) == 0:
                st.info("No se encontraron partidos juntos entre estos jugadores en el período seleccionado.")
            else:
                pj_juntos = numero_entero_seguro(datos_dupla.get("PJ"))
                pj_jugador_1 = max(numero_entero_seguro(info_1.get("PJ")), 1)
                pj_jugador_2 = max(numero_entero_seguro(info_2.get("PJ")), 1)
                porcentaje_jugador_1 = pj_juntos / pj_jugador_1 * 100
                porcentaje_jugador_2 = pj_juntos / pj_jugador_2 * 100
                d1, d2, d3, d4 = st.columns(4)

                d1.metric(
                    "PJ juntos",
                    pj_juntos
                )
                d2.metric(
                    "% PJ jugador 1",
                    f"{porcentaje_jugador_1:.1f}%",
                    help=f"Porcentaje de partidos de {jugador_1} que jugó junto a {jugador_2}."
                )
                d3.metric(
                    "% PJ jugador 2",
                    f"{porcentaje_jugador_2:.1f}%",
                    help=f"Porcentaje de partidos de {jugador_2} que jugó junto a {jugador_1}."
                )
                d4.metric(
                    "WR dupla",
                    f"{numero_decimal_seguro(datos_dupla.get('WinRate')):.1f}%"
                )

                v1, v2, v3 = st.columns(3)
                v1.metric(
                    "Victorias juntos",
                    numero_entero_seguro(datos_dupla.get("G"))
                )
                v2.metric(
                    "Empates juntos",
                    numero_entero_seguro(datos_dupla.get("E"))
                )
                v3.metric(
                    "Derrotas juntos",
                    numero_entero_seguro(datos_dupla.get("P"))
                )

                st.info(
                    "🧪 Química de dupla: "
                    + obtener_quimica_dupla(datos_dupla)
                )

                timeline_dupla = obtener_timeline_dupla(
                    participaciones_periodo,
                    jugador_1,
                    jugador_2
                )

                if not timeline_dupla.empty:
                    st.subheader("📅 Partidos juntos por año")
                    fig_dupla = construir_grafico_dupla_timeline(
                        timeline_dupla
                    )
                    st.plotly_chart(
                        fig_dupla,
                        use_container_width=True
                    )

            st.divider()
            st.subheader("⚔️ Enfrentamiento directo")

            if enfrentamiento is None:
                st.info("No se encontraron enfrentamientos directos entre estos jugadores.")
            else:
                fig_enfrentamiento = construir_grafico_enfrentamiento(
                    enfrentamiento,
                    jugador_1,
                    jugador_2
                )

                st.plotly_chart(
                    fig_enfrentamiento,
                    use_container_width=True
                )

                timeline_enfrentamientos = obtener_timeline_enfrentamientos(
                    participaciones_periodo,
                    jugador_1,
                    jugador_2
                )

                if not timeline_enfrentamientos.empty:
                    st.subheader("📅 Evolución anual del mano a mano")

                    fig_timeline = go.Figure()
                    columna_victorias_1 = f"Victorias {jugador_1}"
                    columna_victorias_2 = f"Victorias {jugador_2}"

                    fig_timeline.add_trace(
                        go.Bar(
                            x=timeline_enfrentamientos["Año"],
                            y=timeline_enfrentamientos[columna_victorias_1],
                            name=f"Victorias {jugador_1}",
                            marker_color="#00C2FF",
                            hovertemplate=(
                                f"<b>{jugador_1}</b><br>"
                                "Año: %{x}<br>"
                                "Victorias: %{y}"
                                "<extra></extra>"
                            )
                        )
                    )

                    fig_timeline.add_trace(
                        go.Bar(
                            x=timeline_enfrentamientos["Año"],
                            y=timeline_enfrentamientos["Empates"],
                            name="Empates",
                            marker_color="#94A3B8",
                            hovertemplate=(
                                "<b>Empates</b><br>"
                                "Año: %{x}<br>"
                                "Empates: %{y}"
                                "<extra></extra>"
                            )
                        )
                    )

                    fig_timeline.add_trace(
                        go.Bar(
                            x=timeline_enfrentamientos["Año"],
                            y=timeline_enfrentamientos[columna_victorias_2],
                            name=f"Victorias {jugador_2}",
                            marker_color="#FFB000",
                            hovertemplate=(
                                f"<b>{jugador_2}</b><br>"
                                "Año: %{x}<br>"
                                "Victorias: %{y}"
                                "<extra></extra>"
                            )
                        )
                    )

                    fig_timeline.add_trace(
                        go.Scatter(
                            x=timeline_enfrentamientos["Año"],
                            y=timeline_enfrentamientos["Total"],
                            name="Total enfrentamientos",
                            mode="lines+markers",
                            line={
                                "color": "white",
                                "width": 3
                            },
                            marker={
                                "size": 8,
                                "color": "white"
                            },
                            hovertemplate=(
                                "<b>Total enfrentamientos</b><br>"
                                "Año: %{x}<br>"
                                "Total: %{y}"
                                "<extra></extra>"
                            )
                        )
                    )

                    fig_timeline.update_layout(
                        height=430,
                        barmode="stack",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font={
                            "color": "white",
                            "size": 13
                        },
                        xaxis={
                            "title": "Año",
                            "tickmode": "linear",
                            "gridcolor": "rgba(255,255,255,0.12)"
                        },
                        yaxis={
                            "title": "Cantidad de partidos",
                            "gridcolor": "rgba(255,255,255,0.12)"
                        },
                        legend={
                            "orientation": "h",
                            "yanchor": "bottom",
                            "y": 1.02,
                            "xanchor": "center",
                            "x": 0.5
                        },
                        hoverlabel={
                            "bgcolor": "#111827",
                            "font_size": 13,
                            "font_color": "white",
                            "bordercolor": "rgba(255,255,255,0.35)"
                        },
                        margin={
                            "l": 50,
                            "r": 30,
                            "t": 80,
                            "b": 50
                        }
                    )

                    st.plotly_chart(
                        fig_timeline,
                        use_container_width=True
                    )

                if enfrentamiento["victorias_jugador_1"] > enfrentamiento["victorias_jugador_2"]:
                    diferencia = (
                        enfrentamiento["victorias_jugador_1"]
                        - enfrentamiento["victorias_jugador_2"]
                    )
                    st.success(
                        f"{jugador_1} lidera el mano a mano por {diferencia} victoria(s)."
                    )
                elif enfrentamiento["victorias_jugador_2"] > enfrentamiento["victorias_jugador_1"]:
                    diferencia = (
                        enfrentamiento["victorias_jugador_2"]
                        - enfrentamiento["victorias_jugador_1"]
                    )
                    st.success(
                        f"{jugador_2} lidera el mano a mano por {diferencia} victoria(s)."
                    )
                else:
                    st.info("El mano a mano está empatado en victorias.")
