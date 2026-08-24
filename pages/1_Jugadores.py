import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from itertools import combinations

from supabase_utils import get_supabase


st.title("👤 Jugadores")
supabase = get_supabase()


# ==================================================
# FUNCIONES GENERALES
# ==================================================

def leer_tabla_completa(tabla):
    registros = []
    desde = 0
    lote = 1000

    while True:
        respuesta = (
            supabase.table(tabla)
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
    if valor is None or pd.isna(valor) or str(valor).strip() == "":
        return reemplazo
    return str(valor)


def numero_entero_seguro(valor):
    if valor is None or pd.isna(valor):
        return 0
    return int(valor)


def numero_decimal_seguro(valor):
    if valor is None or pd.isna(valor):
        return 0.0
    return float(valor)


def emoji_equipo_favorito(equipo):
    equipo_texto = texto_seguro(equipo, "").lower()
    if "pesca" in equipo_texto:
        return "🐟"
    if "dealer" in equipo_texto:
        return "🚗"
    if "biologo" in equipo_texto or "biólogo" in equipo_texto:
        return "🦠"
    if "dhl" in equipo_texto:
        return "📦"
    return "🏅"


def filtrar_historial_por_periodo(historial_df, periodo):
    if historial_df.empty or periodo == "Histórico":
        return historial_df.copy()

    fecha_maxima = historial_df["fecha"].max()
    if pd.isna(fecha_maxima):
        return historial_df.copy()

    if periodo == "Últimos 12 meses":
        return historial_df[
            historial_df["fecha"] >= fecha_maxima - pd.Timedelta(days=365)
        ].copy()
    if periodo == "Últimos 3 años":
        return historial_df[
            historial_df["fecha"] >= fecha_maxima - pd.Timedelta(days=365 * 3)
        ].copy()
    if periodo == "Desde 2020":
        return historial_df[historial_df["fecha"].dt.year >= 2020].copy()

    return historial_df.copy()


def racha_maxima(resultados, tipo):
    mejor = 0
    actual = 0
    for resultado in resultados:
        if resultado == tipo:
            actual += 1
            mejor = max(mejor, actual)
        else:
            actual = 0
    return mejor


def racha_activa(resultados):
    if not resultados:
        return 0, "Sin datos"
    tipo = resultados[-1]
    cantidad = 0
    for resultado in reversed(resultados):
        if resultado != tipo:
            break
        cantidad += 1
    return cantidad, tipo


def etiqueta_racha(tipo, cantidad):
    cantidad = numero_entero_seguro(cantidad)
    if tipo == "G":
        return f"{cantidad} victoria(s)"
    if tipo == "E":
        return f"{cantidad} empate(s)"
    if tipo == "P":
        return f"{cantidad} derrota(s)"
    return "Sin datos"


# ==================================================
# CALCULOS POR PERIODO
# ==================================================

def estadisticas_individuales(historial):
    if historial.empty:
        return pd.DataFrame(columns=["jugador", "PJ", "G", "E", "P", "WinRate"])

    df = (
        historial.pivot_table(
            index="jugador",
            columns="resultado_jugador",
            aggfunc="size",
            fill_value=0,
        )
        .reset_index()
    )
    df.columns.name = None
    for columna in ["G", "E", "P"]:
        if columna not in df.columns:
            df[columna] = 0
    df["PJ"] = df["G"] + df["E"] + df["P"]
    df["WinRate"] = (df["G"] / df["PJ"].replace(0, pd.NA) * 100).round(1).fillna(0)
    return df[["jugador", "PJ", "G", "E", "P", "WinRate"]]


def estadisticas_parejas(historial):
    registros = []
    for _, partido in historial.groupby("partido_id"):
        for _, equipo in partido.groupby("equipo"):
            nombres = sorted(equipo["jugador"].dropna().astype(str).unique())
            if len(nombres) < 2:
                continue
            resultado = equipo.iloc[0]["resultado_jugador"]
            for jugador_1, jugador_2 in combinations(nombres, 2):
                registros.append(
                    {"jugador_1": jugador_1, "jugador_2": jugador_2, "resultado": resultado}
                )

    if not registros:
        return pd.DataFrame(
            columns=["jugador_1", "jugador_2", "PJ", "G", "E", "P", "WinRate"]
        )

    df = (
        pd.DataFrame(registros)
        .pivot_table(
            index=["jugador_1", "jugador_2"],
            columns="resultado",
            aggfunc="size",
            fill_value=0,
        )
        .reset_index()
    )
    df.columns.name = None
    for columna in ["G", "E", "P"]:
        if columna not in df.columns:
            df[columna] = 0
    df["PJ"] = df["G"] + df["E"] + df["P"]
    df["WinRate"] = (df["G"] / df["PJ"].replace(0, pd.NA) * 100).round(1).fillna(0)
    return df


def estadisticas_rivales(historial):
    registros = []
    for _, partido in historial.groupby("partido_id"):
        equipos = list(partido["equipo"].dropna().unique())
        if len(equipos) < 2:
            continue
        lado_1 = partido[partido["equipo"] == equipos[0]]
        lado_2 = partido[partido["equipo"] == equipos[1]]

        for _, fila_1 in lado_1.iterrows():
            for _, fila_2 in lado_2.iterrows():
                jugador_a, jugador_b = sorted([str(fila_1["jugador"]), str(fila_2["jugador"])])
                if str(fila_1["jugador"]) == jugador_a:
                    resultado_a = fila_1["resultado_jugador"]
                    resultado_b = fila_2["resultado_jugador"]
                else:
                    resultado_a = fila_2["resultado_jugador"]
                    resultado_b = fila_1["resultado_jugador"]

                registros.append(
                    {
                        "jugador_1": jugador_a,
                        "jugador_2": jugador_b,
                        "pj": 1,
                        "g_jugador_1": int(resultado_a == "G"),
                        "g_jugador_2": int(resultado_b == "G"),
                        "E": int(resultado_a == "E"),
                    }
                )

    if not registros:
        return pd.DataFrame(
            columns=[
                "jugador_1", "jugador_2", "pj", "g_jugador_1",
                "g_jugador_2", "E", "winrate_jugador_1", "winrate_jugador_2"
            ]
        )

    df = (
        pd.DataFrame(registros)
        .groupby(["jugador_1", "jugador_2"], as_index=False)
        .agg(
            pj=("pj", "sum"),
            g_jugador_1=("g_jugador_1", "sum"),
            g_jugador_2=("g_jugador_2", "sum"),
            E=("E", "sum"),
        )
    )
    df["winrate_jugador_1"] = (df["g_jugador_1"] / df["pj"] * 100).round(1)
    df["winrate_jugador_2"] = (df["g_jugador_2"] / df["pj"] * 100).round(1)
    return df


def obtener_rivales_jugador(rivales_df, jugador):
    registros = []
    for _, fila in rivales_df.iterrows():
        if jugador == fila["jugador_1"]:
            registros.append(
                {
                    "rival": fila["jugador_2"],
                    "pj": int(fila["pj"]),
                    "victorias_jugador": int(fila["g_jugador_1"]),
                    "victorias_rival": int(fila["g_jugador_2"]),
                    "empates": int(fila["E"]),
                    "winrate": float(fila["winrate_jugador_1"]),
                }
            )
        elif jugador == fila["jugador_2"]:
            registros.append(
                {
                    "rival": fila["jugador_1"],
                    "pj": int(fila["pj"]),
                    "victorias_jugador": int(fila["g_jugador_2"]),
                    "victorias_rival": int(fila["g_jugador_1"]),
                    "empates": int(fila["E"]),
                    "winrate": float(fila["winrate_jugador_2"]),
                }
            )
    return pd.DataFrame(registros)


def info_jugador_periodo(jugador, info_base, historial_periodo, rivales_periodo):
    historial = historial_periodo[historial_periodo["jugador"] == jugador].copy()
    historial = historial.sort_values(["fecha", "partido_id"])
    resultados = historial["resultado_jugador"].tolist()
    activa, tipo = racha_activa(resultados)

    info = info_base.copy()
    info["PJ"] = len(resultados)
    info["G"] = resultados.count("G")
    info["E"] = resultados.count("E")
    info["P"] = resultados.count("P")
    info["WinRate"] = round(info["G"] / info["PJ"] * 100, 1) if info["PJ"] else 0
    info["mejor_racha_ganadora"] = racha_maxima(resultados, "G")
    info["peor_racha_perdedora"] = racha_maxima(resultados, "P")
    info["racha_activa"] = activa
    info["tipo_racha_activa"] = tipo

    if historial.empty:
        info["equipo_favorito"] = "Sin datos"
    else:
        info["equipo_favorito"] = historial["equipo"].value_counts().index[0]

    rivales_jugador = obtener_rivales_jugador(rivales_periodo, jugador)
    if rivales_jugador.empty:
        info["rival_mas_frecuente"] = "Sin datos"
        info["pj_vs_rival_mas_frecuente"] = 0
    else:
        rival = rivales_jugador.sort_values(["pj", "rival"], ascending=[False, True]).iloc[0]
        info["rival_mas_frecuente"] = rival["rival"]
        info["pj_vs_rival_mas_frecuente"] = rival["pj"]

    return info


def obtener_companeros(jugador, parejas_df):
    df = parejas_df[
        (parejas_df["jugador_1"] == jugador) | (parejas_df["jugador_2"] == jugador)
    ].copy()
    if df.empty:
        return None, None, None
    df["companero"] = df.apply(
        lambda fila: fila["jugador_2"] if fila["jugador_1"] == jugador else fila["jugador_1"],
        axis=1,
    )
    frecuente = df.sort_values(["PJ", "companero"], ascending=[False, True]).iloc[0]
    relevantes = df[df["PJ"] >= 30].copy()
    if relevantes.empty:
        return frecuente, frecuente, frecuente
    mejor = relevantes.sort_values(["WinRate", "PJ", "companero"], ascending=[False, False, True]).iloc[0]
    peor = relevantes.sort_values(["WinRate", "PJ", "companero"], ascending=[True, False, True]).iloc[0]
    return frecuente, mejor, peor


def top_companeros(jugador, parejas_df, individuales_df):
    df = parejas_df[
        (parejas_df["jugador_1"] == jugador) | (parejas_df["jugador_2"] == jugador)
    ].copy()
    if df.empty:
        return pd.DataFrame()
    df["Compañero"] = df.apply(
        lambda fila: fila["jugador_2"] if fila["jugador_1"] == jugador else fila["jugador_1"],
        axis=1,
    )
    wr = individuales_df.set_index("jugador")["WinRate"]
    df["WR individual compañero %"] = df["Compañero"].map(wr).fillna(0).round(1)
    return (
        df.sort_values(["PJ", "WinRate", "Compañero"], ascending=[False, False, True])
        .head(10)[["Compañero", "PJ", "G", "E", "P", "WinRate", "WR individual compañero %"]]
        .rename(columns={"WinRate": "WR dupla %"})
    )


def top_rivales(jugador, rivales_df, individuales_df):
    df = obtener_rivales_jugador(rivales_df, jugador)
    if df.empty:
        return pd.DataFrame()
    wr = individuales_df.set_index("jugador")["WinRate"]
    df["WR individual rival %"] = df["rival"].map(wr).fillna(0).round(1)
    return (
        df.sort_values(["pj", "winrate", "rival"], ascending=[False, False, True])
        .head(10)[[
            "rival", "pj", "victorias_jugador", "empates",
            "victorias_rival", "winrate", "WR individual rival %"
        ]]
        .rename(
            columns={
                "rival": "Rival",
                "pj": "PJ enfrentados",
                "victorias_jugador": "Victorias jugador",
                "empates": "Empates",
                "victorias_rival": "Victorias rival",
                "winrate": "WR contra rival %",
            }
        )
    )


# ==================================================
# VISUALES DEL PERFIL
# ==================================================

def chips_forma(historial, cantidad=8):
    ultimos = historial.sort_values(["fecha", "partido_id"], ascending=[False, False]).head(cantidad)
    colores = {"G": "#22C55E", "E": "#FACC15", "P": "#EF4444"}
    return "".join(
        "<span style='display:inline-flex;align-items:center;justify-content:center;"
        "width:30px;height:30px;margin:2px;border-radius:999px;"
        f"background:{colores.get(resultado, '#64748B')};color:#0B1120;"
        "font-weight:800;font-size:14px;'>"
        f"{resultado}</span>"
        for resultado in ultimos["resultado_jugador"].tolist()
    )


def rendimiento_por_equipo(historial):
    if historial.empty:
        return pd.DataFrame()
    df = (
        historial.pivot_table(
            index="equipo", columns="resultado_jugador", aggfunc="size", fill_value=0
        ).reset_index()
    )
    df.columns.name = None
    for columna in ["G", "E", "P"]:
        if columna not in df.columns:
            df[columna] = 0
    df["PJ"] = df["G"] + df["E"] + df["P"]
    df["Win Rate %"] = (df["G"] / df["PJ"].replace(0, pd.NA) * 100).round(1).fillna(0)
    return (
        df.rename(columns={"equipo": "Equipo"})
        [["Equipo", "PJ", "G", "E", "P", "Win Rate %"]]
        .sort_values(["PJ", "Win Rate %", "Equipo"], ascending=[False, False, True])
    )


def grafico_rendimiento_equipo(df):
    fig = go.Figure()
    fig.add_bar(x=df["Equipo"], y=df["PJ"], name="PJ", marker_color="#38BDF8")
    fig.add_trace(
        go.Scatter(
            x=df["Equipo"], y=df["Win Rate %"], name="Win Rate %",
            mode="lines+markers", yaxis="y2", line={"color": "#FACC15", "width": 3}
        )
    )
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        yaxis={"title": "PJ"},
        yaxis2={"title": "Win Rate %", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": 1.05, "x": 0.5, "xanchor": "center"},
    )
    return fig


def tabla_ultimos_partidos(historial):
    df = historial.sort_values(["fecha", "partido_id"], ascending=[False, False]).head(10).copy()
    if df.empty:
        return pd.DataFrame()
    df["Fecha"] = df["fecha"].dt.strftime("%d/%m/%Y")
    df["Marcador"] = df.apply(
        lambda fila: f"{numero_entero_seguro(fila['goles_local'])}-{numero_entero_seguro(fila['goles_visitante'])}",
        axis=1,
    )
    df["Rival / Equipo rival"] = df.apply(
        lambda fila: fila["equipo_visitante"] if fila["equipo"] == fila["equipo_local"] else fila["equipo_local"],
        axis=1,
    )
    return df[["Fecha", "equipo", "resultado_jugador", "Marcador", "Rival / Equipo rival"]].rename(
        columns={"equipo": "Equipo", "resultado_jugador": "Resultado"}
    )


def grafico_wr_acumulado(historial):
    df = historial.sort_values(["fecha", "partido_id"]).copy()
    if df.empty:
        return None
    df["PJ acumulado"] = range(1, len(df) + 1)
    df["Victorias acumuladas"] = (df["resultado_jugador"] == "G").cumsum()
    df["Win Rate acumulado"] = df["Victorias acumuladas"] / df["PJ acumulado"] * 100
    fig = go.Figure(
        go.Scatter(
            x=df["fecha"], y=df["Win Rate acumulado"], mode="lines",
            line={"color": "#22C55E", "width": 3}, name="Win Rate acumulado"
        )
    )
    fig.update_layout(
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        yaxis_title="Win Rate acumulado %",
        xaxis_title="Fecha",
    )
    return fig


def evolucion_jugador(historial):
    if historial.empty:
        return pd.DataFrame()
    df = historial.copy()
    df["Año"] = df["fecha"].dt.year
    evolucion = (
        df.groupby("Año")
        .agg(
            PJ=("resultado_jugador", "size"),
            PG=("resultado_jugador", lambda x: (x == "G").sum()),
        )
        .reset_index()
    )
    evolucion["WinRate"] = (evolucion["PG"] / evolucion["PJ"] * 100).round(1)
    return evolucion


def grafico_evolucion(evolucion):
    fig = go.Figure()
    fig.add_bar(x=evolucion["Año"], y=evolucion["PJ"], name="Partidos Jugados")
    fig.add_trace(go.Scatter(x=evolucion["Año"], y=evolucion["PG"], mode="lines+markers", name="Victorias"))
    fig.add_trace(
        go.Scatter(
            x=evolucion["Año"], y=evolucion["WinRate"], mode="lines+markers",
            name="Win Rate %", yaxis="y2"
        )
    )
    fig.update_layout(
        height=550,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        xaxis_title="Año",
        yaxis={"title": "Partidos / Victorias"},
        yaxis2={"title": "Win Rate %", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": 1.05, "x": 0.5, "xanchor": "center"},
    )
    return fig


# ==================================================
# COMPARADOR
# ==================================================

def calcular_dupla(historial, jugador_1, jugador_2):
    parejas = estadisticas_parejas(historial)
    dupla = parejas[
        ((parejas["jugador_1"] == jugador_1) & (parejas["jugador_2"] == jugador_2))
        | ((parejas["jugador_1"] == jugador_2) & (parejas["jugador_2"] == jugador_1))
    ]
    if dupla.empty:
        return {"PJ": 0, "G": 0, "E": 0, "P": 0, "WinRate": 0}
    return dupla.iloc[0]


def calcular_enfrentamiento(historial, jugador_1, jugador_2):
    rivales = estadisticas_rivales(historial)
    jugador_a, jugador_b = sorted([jugador_1, jugador_2])
    fila = rivales[
        (rivales["jugador_1"] == jugador_a) & (rivales["jugador_2"] == jugador_b)
    ]
    if fila.empty:
        return None
    fila = fila.iloc[0]
    if jugador_1 == jugador_a:
        return {
            "pj": int(fila["pj"]),
            "victorias_jugador_1": int(fila["g_jugador_1"]),
            "victorias_jugador_2": int(fila["g_jugador_2"]),
            "empates": int(fila["E"]),
        }
    return {
        "pj": int(fila["pj"]),
        "victorias_jugador_1": int(fila["g_jugador_2"]),
        "victorias_jugador_2": int(fila["g_jugador_1"]),
        "empates": int(fila["E"]),
    }


def info_comparacion(jugador, info_base, historial):
    rivales = estadisticas_rivales(historial)
    return info_jugador_periodo(jugador, info_base, historial, rivales)


def grafico_comparacion(info_1, info_2, jugador_1, jugador_2):
    metricas = ["PJ", "Victorias", "Win Rate %", "Mejor racha", "Peor racha"]
    valores_1 = [info_1["PJ"], info_1["G"], info_1["WinRate"], info_1["mejor_racha_ganadora"], info_1["peor_racha_perdedora"]]
    valores_2 = [info_2["PJ"], info_2["G"], info_2["WinRate"], info_2["mejor_racha_ganadora"], info_2["peor_racha_perdedora"]]
    fig = go.Figure()
    fig.add_bar(y=metricas, x=valores_1, name=jugador_1, orientation="h", marker_color="#00C2FF")
    fig.add_bar(y=metricas, x=valores_2, name=jugador_2, orientation="h", marker_color="#FFB000")
    fig.update_layout(
        height=460, barmode="group", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font={"color": "white"},
        legend={"orientation": "h", "y": 1.05, "x": 0.5, "xanchor": "center"}
    )
    return fig


def grafico_enfrentamiento(enfrentamiento, jugador_1, jugador_2):
    fig = go.Figure()
    fig.add_bar(y=["Mano a mano"], x=[enfrentamiento["victorias_jugador_1"]], name=f"Victorias {jugador_1}", orientation="h", marker_color="#00C2FF")
    fig.add_bar(y=["Mano a mano"], x=[enfrentamiento["empates"]], name="Empates", orientation="h", marker_color="#94A3B8")
    fig.add_bar(y=["Mano a mano"], x=[enfrentamiento["victorias_jugador_2"]], name=f"Victorias {jugador_2}", orientation="h", marker_color="#FFB000")
    fig.update_layout(
        height=260, barmode="stack", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font={"color": "white"},
        legend={"orientation": "h", "y": 1.05, "x": 0.5, "xanchor": "center"}
    )
    return fig


# ==================================================
# CARGA Y PREPARACION
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    participaciones = leer_tabla_completa("participaciones")
    partidos = leer_tabla_completa("partidos")
except Exception as error:
    st.error("No se pudieron leer los datos desde Supabase.")
    st.exception(error)
    st.stop()

if jugadores.empty or participaciones.empty or partidos.empty:
    st.warning("Faltan datos en jugadores_master, participaciones o partidos.")
    st.stop()

columnas_jugadores = [
    "jugador", "PJ", "G", "E", "P", "WinRate", "equipo_favorito",
    "rival_mas_frecuente", "pj_vs_rival_mas_frecuente",
    "mejor_racha_ganadora", "peor_racha_perdedora", "racha_activa",
    "tipo_racha_activa"
]
columnas_participaciones = ["partido_id", "jugador", "equipo"]
columnas_partidos = ["id", "fecha", "equipo_local", "equipo_visitante", "goles_local", "goles_visitante"]

for nombre, df, columnas in [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("participaciones", participaciones, columnas_participaciones),
    ("partidos", partidos, columnas_partidos),
]:
    faltantes = [columna for columna in columnas if columna not in df.columns]
    if faltantes:
        st.error(f"Faltan columnas en {nombre}: " + ", ".join(faltantes))
        st.stop()

partidos["fecha"] = pd.to_datetime(partidos["fecha"], errors="coerce")
partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")
partidos["resultado_local"] = "E"
partidos.loc[partidos["goles_local"] > partidos["goles_visitante"], "resultado_local"] = "G"
partidos.loc[partidos["goles_local"] < partidos["goles_visitante"], "resultado_local"] = "P"

historial_total = participaciones.merge(
    partidos[[
        "id", "fecha", "equipo_local", "equipo_visitante",
        "goles_local", "goles_visitante", "resultado_local"
    ]],
    left_on="partido_id",
    right_on="id",
    how="left",
)
historial_total["resultado_jugador"] = ""
mask_local = historial_total["equipo"] == historial_total["equipo_local"]
mask_visitante = historial_total["equipo"] == historial_total["equipo_visitante"]
historial_total.loc[mask_local, "resultado_jugador"] = historial_total["resultado_local"]
historial_total.loc[mask_visitante & (historial_total["resultado_local"] == "G"), "resultado_jugador"] = "P"
historial_total.loc[mask_visitante & (historial_total["resultado_local"] == "P"), "resultado_jugador"] = "G"
historial_total.loc[mask_visitante & (historial_total["resultado_local"] == "E"), "resultado_jugador"] = "E"
historial_total = historial_total[
    historial_total["fecha"].notna()
    & historial_total["resultado_jugador"].isin(["G", "E", "P"])
].copy()

for columna in ["PJ", "G", "E", "P", "WinRate", "racha_activa", "mejor_racha_ganadora", "peor_racha_perdedora", "pj_vs_rival_mas_frecuente"]:
    jugadores[columna] = pd.to_numeric(jugadores[columna], errors="coerce")

lista_jugadores = sorted(jugadores["jugador"].dropna().astype(str).unique())
tab_perfil, tab_comparador = st.tabs(["👤 Perfil del jugador", "⚔️ Comparar jugadores"])


# ==================================================
# PERFIL DEL JUGADOR
# ==================================================

with tab_perfil:
    col_selector, col_periodo = st.columns(2)
    with col_selector:
        jugador = st.selectbox(
            "🔎 Buscar jugador",
            lista_jugadores,
            index=None,
            placeholder="Escribí el nombre del jugador...",
            key="selector_perfil_jugador",
        )
    with col_periodo:
        periodo_perfil = st.selectbox(
            "Período del perfil",
            ["Histórico", "Últimos 12 meses", "Últimos 3 años", "Desde 2020"],
            index=0,
            key="periodo_perfil_jugador",
        )

    if jugador is None:
        st.info("Seleccioná un jugador para ver sus estadísticas.")
    else:
        info_base = jugadores[jugadores["jugador"] == jugador].iloc[0]
        historial_periodo = filtrar_historial_por_periodo(historial_total, periodo_perfil)
        historial = historial_periodo[historial_periodo["jugador"] == jugador].copy()
        individuales = estadisticas_individuales(historial_periodo)
        parejas = estadisticas_parejas(historial_periodo)
        rivales = estadisticas_rivales(historial_periodo)
        info = info_jugador_periodo(jugador, info_base, historial_periodo, rivales)
        frecuente, mejor, peor = obtener_companeros(jugador, parejas)
        rivales_jugador = obtener_rivales_jugador(rivales, jugador)

        emoji = emoji_equipo_favorito(info.get("equipo_favorito"))
        header_col, forma_col = st.columns([2, 1])
        with header_col:
            st.header(f"{emoji} {jugador}")
            st.caption("Referencias: 🐟 Pescas · 🚗 Dealers · 🦠 Biólogos · 📦 DHL")
            st.caption(f"Período seleccionado: {periodo_perfil}")
        with forma_col:
            chips = chips_forma(historial)
            if chips:
                st.caption("Forma reciente")
                st.markdown(chips, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PJ", numero_entero_seguro(info["PJ"]))
        c2.metric("Victorias", numero_entero_seguro(info["G"]))
        c3.metric("Derrotas", numero_entero_seguro(info["P"]))
        c4.metric("Win Rate", f"{numero_decimal_seguro(info['WinRate']):.1f}%")

        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Racha activa", numero_entero_seguro(info["racha_activa"]), help=etiqueta_racha(info["tipo_racha_activa"], info["racha_activa"]))
        r2.metric("Mejor racha", numero_entero_seguro(info["mejor_racha_ganadora"]))
        r3.metric("Peor racha", numero_entero_seguro(info["peor_racha_perdedora"]))
        r4.metric("Empates", numero_entero_seguro(info["E"]))

        if periodo_perfil == "Histórico":
            st.divider()
            st.subheader("🏛️ Posiciones históricas")
            ranking_pj = int(jugadores["PJ"].rank(method="min", ascending=False)[jugadores["jugador"] == jugador].iloc[0])
            ranking_g = int(jugadores["G"].rank(method="min", ascending=False)[jugadores["jugador"] == jugador].iloc[0])
            ranking_racha = int(jugadores["mejor_racha_ganadora"].rank(method="min", ascending=False)[jugadores["jugador"] == jugador].iloc[0])
            p1, p2, p3 = st.columns(3)
            p1.metric("Ranking PJ", f"#{ranking_pj}")
            p2.metric("Ranking victorias", f"#{ranking_g}")
            p3.metric("Ranking mejor racha", f"#{ranking_racha}")

        st.divider()
        col_1, col_2 = st.columns(2)
        with col_1:
            if frecuente is None:
                st.info("🤝 Compañero más frecuente: Sin datos")
                st.info("🏆 Mejor compañero: Sin datos")
            else:
                st.info(f"🤝 Compañero más frecuente: {frecuente['companero']} ({int(frecuente['PJ'])} PJ)")
                st.info(f"🏆 Mejor compañero: {mejor['companero']} ({float(mejor['WinRate']):.1f}% WR)")
        with col_2:
            st.info(f"🥊 Rival más frecuente: {texto_seguro(info['rival_mas_frecuente'])} ({int(info['pj_vs_rival_mas_frecuente'])} PJ)")
            if peor is None:
                st.info("📉 Peor compañero: Sin datos")
            else:
                st.info(f"📉 Peor compañero: {peor['companero']} ({float(peor['WinRate']):.1f}% WR)")

        rivales_min = rivales_jugador[rivales_jugador["pj"] >= 20].copy() if not rivales_jugador.empty else pd.DataFrame()
        if not rivales_min.empty:
            st.divider()
            st.subheader("⚔️ Rivales destacados")
            mas_vencido = rivales_min.sort_values(["victorias_jugador", "pj"], ascending=[False, False]).iloc[0]
            mas_derrotas = rivales_min.sort_values(["victorias_rival", "pj"], ascending=[False, False]).iloc[0]
            mejor_wr = rivales_min.sort_values(["winrate", "pj"], ascending=[False, False]).iloc[0]
            peor_wr = rivales_min.sort_values(["winrate", "pj"], ascending=[True, False]).iloc[0]
            a, b = st.columns(2)
            c, d = st.columns(2)
            a.info(f"✅ Más victorias contra\n\n**{mas_vencido['rival']}**\n\n{int(mas_vencido['victorias_jugador'])} victorias")
            b.info(f"📈 Mejor WR contra\n\n**{mejor_wr['rival']}**\n\n{float(mejor_wr['winrate']):.1f}%")
            c.info(f"⚠️ Más derrotas contra\n\n**{mas_derrotas['rival']}**\n\n{int(mas_derrotas['victorias_rival'])} derrotas")
            d.info(f"📉 Peor WR contra\n\n**{peor_wr['rival']}**\n\n{float(peor_wr['winrate']):.1f}%")
            st.caption("Se consideran solo rivales con al menos 20 enfrentamientos en el período.")

        st.divider()
        st.subheader("🏟️ Rendimiento por equipo")
        rendimiento = rendimiento_por_equipo(historial).head(4)
        if rendimiento.empty:
            st.info("No hay datos para mostrar.")
        else:
            usado = rendimiento.iloc[0]
            candidatos = rendimiento[rendimiento["PJ"] >= 20]
            mejor_equipo = (candidatos if not candidatos.empty else rendimiento).sort_values(
                ["Win Rate %", "PJ"], ascending=[False, False]
            ).iloc[0]
            e1, e2 = st.columns(2)
            e1.info(f"🏟️ Equipo más usado\n\n**{usado['Equipo']}**\n\n{int(usado['PJ'])} partidos")
            e2.info(f"🎯 Mejor rendimiento\n\n**{mejor_equipo['Equipo']}**\n\n{float(mejor_equipo['Win Rate %']):.1f}% WR")
            st.plotly_chart(grafico_rendimiento_equipo(rendimiento), use_container_width=True)

        evolucion = evolucion_jugador(historial)
        st.divider()
        st.subheader("📈 Evolución histórica")
        if evolucion.empty:
            st.info("No hay datos históricos para mostrar.")
        else:
            st.plotly_chart(grafico_evolucion(evolucion), use_container_width=True)

        st.divider()
        st.subheader("📅 Últimos 10 partidos")
        ultimos = tabla_ultimos_partidos(historial)
        if ultimos.empty:
            st.info("No hay partidos para mostrar.")
        else:
            st.dataframe(ultimos, use_container_width=True, hide_index=True, height=380)

        fig_wr = grafico_wr_acumulado(historial)
        if fig_wr is not None:
            st.divider()
            st.subheader("📈 Win Rate acumulado")
            st.plotly_chart(fig_wr, use_container_width=True)

        st.divider()
        st.subheader("🤝 Compañeros y rivales más frecuentes")
        st.caption("Todos los datos respetan el período seleccionado.")
        tabla_companeros = top_companeros(jugador, parejas, individuales)
        tabla_rivales = top_rivales(jugador, rivales, individuales)

        col_companeros, col_rivales = st.columns(2)
        with col_companeros:
            st.subheader("Top 10 compañeros")
            if tabla_companeros.empty:
                st.info("No hay compañeros para mostrar.")
            else:
                st.dataframe(tabla_companeros, use_container_width=True, hide_index=True, height=420)
        with col_rivales:
            st.subheader("Top 10 rivales")
            if tabla_rivales.empty:
                st.info("No hay rivales para mostrar.")
            else:
                st.dataframe(tabla_rivales, use_container_width=True, hide_index=True, height=420)


# ==================================================
# COMPARAR JUGADORES
# ==================================================

with tab_comparador:
    st.subheader("⚔️ Comparar jugadores")
    col_1, col_2 = st.columns(2)
    with col_1:
        jugador_1 = st.selectbox("Jugador 1", lista_jugadores, index=None, key="comparador_jugador_1")
    with col_2:
        jugador_2 = st.selectbox("Jugador 2", lista_jugadores, index=None, key="comparador_jugador_2")

    periodo = st.selectbox(
        "Período de comparación",
        ["Histórico", "Últimos 12 meses", "Últimos 3 años", "Desde 2020"],
        key="periodo_comparacion_jugadores",
    )

    if jugador_1 is None or jugador_2 is None:
        st.info("Seleccioná dos jugadores.")
    elif jugador_1 == jugador_2:
        st.warning("Seleccioná dos jugadores distintos.")
    else:
        historial = filtrar_historial_por_periodo(historial_total, periodo)
        base_1 = jugadores[jugadores["jugador"] == jugador_1].iloc[0]
        base_2 = jugadores[jugadores["jugador"] == jugador_2].iloc[0]
        info_1 = info_comparacion(jugador_1, base_1, historial)
        info_2 = info_comparacion(jugador_2, base_2, historial)

        st.divider()
        st.subheader(f"📊 {jugador_1} vs {jugador_2}")
        st.caption(f"Período seleccionado: {periodo}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"PJ {jugador_1}", int(info_1["PJ"]))
        k2.metric(f"PJ {jugador_2}", int(info_2["PJ"]))
        k3.metric(f"WR {jugador_1}", f"{float(info_1['WinRate']):.1f}%")
        k4.metric(f"WR {jugador_2}", f"{float(info_2['WinRate']):.1f}%")
        st.plotly_chart(grafico_comparacion(info_1, info_2, jugador_1, jugador_2), use_container_width=True)

        st.divider()
        st.subheader("🤝 Como dupla")
        dupla = calcular_dupla(historial, jugador_1, jugador_2)
        if int(dupla["PJ"]) == 0:
            st.info("No jugaron juntos en el período seleccionado.")
        else:
            pj_juntos = int(dupla["PJ"])
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("PJ juntos", pj_juntos)
            d2.metric(f"% PJ {jugador_1}", f"{pj_juntos / max(int(info_1['PJ']), 1) * 100:.1f}%")
            d3.metric(f"% PJ {jugador_2}", f"{pj_juntos / max(int(info_2['PJ']), 1) * 100:.1f}%")
            d4.metric("WR dupla", f"{float(dupla['WinRate']):.1f}%")
            v1, v2, v3 = st.columns(3)
            v1.metric("Victorias juntos", int(dupla["G"]))
            v2.metric("Empates juntos", int(dupla["E"]))
            v3.metric("Derrotas juntos", int(dupla["P"]))

        st.divider()
        st.subheader("⚔️ Enfrentamiento directo")
        enfrentamiento = calcular_enfrentamiento(historial, jugador_1, jugador_2)
        if enfrentamiento is None:
            st.info("No se enfrentaron en el período seleccionado.")
        else:
            st.plotly_chart(
                grafico_enfrentamiento(enfrentamiento, jugador_1, jugador_2),
                use_container_width=True,
            )
            if enfrentamiento["victorias_jugador_1"] > enfrentamiento["victorias_jugador_2"]:
                diferencia = enfrentamiento["victorias_jugador_1"] - enfrentamiento["victorias_jugador_2"]
                st.success(f"{jugador_1} lidera el mano a mano por {diferencia} victoria(s).")
            elif enfrentamiento["victorias_jugador_2"] > enfrentamiento["victorias_jugador_1"]:
                diferencia = enfrentamiento["victorias_jugador_2"] - enfrentamiento["victorias_jugador_1"]
                st.success(f"{jugador_2} lidera el mano a mano por {diferencia} victoria(s).")
            else:
                st.info("El mano a mano está empatado en victorias.")
