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

            emoji_equipo = emoji_equipo_favorito(
                info.get("equipo_favorito")
            )

            st.header(f"{emoji_equipo} {jugador}")
            st.caption(
                "Referencias de equipo favorito: 🐟 Pescas · 🚗 Dealers · 🦠 Biólogos · 📦 DHL"
            )

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

            historial = participaciones_historial[
                participaciones_historial["jugador"] == jugador
            ].copy()

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

    if jugador_1 is None or jugador_2 is None:
        st.info("Seleccioná dos jugadores para ver la comparación.")
    elif jugador_1 == jugador_2:
        st.warning("Seleccioná dos jugadores distintos para comparar.")
    else:
        info_1 = obtener_fila_jugador(jugadores, jugador_1)
        info_2 = obtener_fila_jugador(jugadores, jugador_2)

        if info_1 is None or info_2 is None:
            st.warning("No se encontraron datos para alguno de los jugadores seleccionados.")
        else:
            enfrentamiento = obtener_enfrentamiento(
                rivales,
                jugador_1,
                jugador_2
            )

            st.divider()
            st.subheader(f"📊 {jugador_1} vs {jugador_2}")

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

            st.divider()
            st.subheader("🤝 Como dupla")

            datos_dupla = obtener_dupla(
                parejas,
                jugador_1,
                jugador_2
            )

            if datos_dupla is None:
                st.info("No se encontraron partidos juntos entre estos jugadores.")
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

                timeline_dupla = obtener_timeline_dupla(
                    participaciones_historial,
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
                    participaciones_historial,
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
