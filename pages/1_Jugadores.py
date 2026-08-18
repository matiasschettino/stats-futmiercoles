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


def construir_radar(info_1, info_2, jugador_1, jugador_2):
    categorias = [
        "PJ",
        "Victorias",
        "Win Rate",
        "Mejor racha",
        "Racha activa"
    ]

    valores_1 = [
        numero_decimal_seguro(info_1.get("PJ")),
        numero_decimal_seguro(info_1.get("G")),
        numero_decimal_seguro(info_1.get("WinRate")),
        numero_decimal_seguro(info_1.get("mejor_racha_ganadora")),
        numero_decimal_seguro(info_1.get("racha_activa"))
    ]

    valores_2 = [
        numero_decimal_seguro(info_2.get("PJ")),
        numero_decimal_seguro(info_2.get("G")),
        numero_decimal_seguro(info_2.get("WinRate")),
        numero_decimal_seguro(info_2.get("mejor_racha_ganadora")),
        numero_decimal_seguro(info_2.get("racha_activa"))
    ]

    maximos = [
        max(v1, v2, 1)
        for v1, v2 in zip(valores_1, valores_2)
    ]

    valores_1_normalizados = [
        round(v / m * 100, 2)
        for v, m in zip(valores_1, maximos)
    ]

    valores_2_normalizados = [
        round(v / m * 100, 2)
        for v, m in zip(valores_2, maximos)
    ]

    categorias_cerradas = categorias + [categorias[0]]
    valores_1_cerrados = valores_1_normalizados + [valores_1_normalizados[0]]
    valores_2_cerrados = valores_2_normalizados + [valores_2_normalizados[0]]

    valores_reales_1 = valores_1 + [valores_1[0]]
    valores_reales_2 = valores_2 + [valores_2[0]]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=valores_1_cerrados,
            theta=categorias_cerradas,
            fill="toself",
            name=jugador_1,
            line=dict(
                color="#00C2FF",
                width=4
            ),
            fillcolor="rgba(0, 194, 255, 0.25)",
            marker=dict(
                size=8,
                color="#00C2FF"
            ),
            customdata=valores_reales_1,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "%{theta}<br>"
                "Valor real: %{customdata}<br>"
                "Comparación relativa: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=valores_2_cerrados,
            theta=categorias_cerradas,
            fill="toself",
            name=jugador_2,
            line=dict(
                color="#FFB000",
                width=4
            ),
            fillcolor="rgba(255, 176, 0, 0.25)",
            marker=dict(
                size=8,
                color="#FFB000"
            ),
            customdata=valores_reales_2,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "%{theta}<br>"
                "Valor real: %{customdata}<br>"
                "Comparación relativa: %{r:.1f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        height=560,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="white",
            size=14
        ),
        polar=dict(
            bgcolor="rgba(15, 23, 42, 0.95)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(
                    color="rgba(255,255,255,0.75)",
                    size=12
                ),
                gridcolor="rgba(255,255,255,0.18)",
                linecolor="rgba(255,255,255,0.25)"
            ),
            angularaxis=dict(
                tickfont=dict(
                    color="white",
                    size=14
                ),
                gridcolor="rgba(255,255,255,0.18)",
                linecolor="rgba(255,255,255,0.25)"
            )
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.10,
            xanchor="center",
            x=0.5,
            font=dict(
                color="white",
                size=14
            )
        ),
        margin=dict(
            l=80,
            r=80,
            t=90,
            b=60
        )
    )

    return fig


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    participaciones = leer_tabla_completa("participaciones")
    parejas = leer_tabla_completa("estadisticas_parejas")
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

            st.header(f"🏅 {jugador}")

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
                st.info(
                    "🏟️ Equipo favorito: "
                    f"{texto_seguro(info.get('equipo_favorito'))}"
                )

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

                st.info(
                    f"🔥 Mejor racha histórica: {mejor_racha} victorias"
                )
                st.info(
                    f"📉 Peor racha histórica: {peor_racha} derrotas"
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

            st.divider()
            st.subheader("🤝 Analizar dupla")

            opciones_companeros = sorted(
                jugadores.loc[
                    jugadores["jugador"] != jugador,
                    "jugador"
                ]
                .dropna()
                .astype(str)
                .unique()
            )

            companero = st.selectbox(
                "Seleccionar segundo jugador",
                opciones_companeros,
                index=None,
                placeholder="Seleccioná otro jugador...",
                key="selector_dupla"
            )

            if companero is None:
                st.info("Seleccioná un segundo jugador para analizar la dupla.")
            else:
                dupla = parejas[
                    (
                        (parejas["jugador_1"] == jugador)
                        & (parejas["jugador_2"] == companero)
                    )
                    |
                    (
                        (parejas["jugador_2"] == jugador)
                        & (parejas["jugador_1"] == companero)
                    )
                ]

                if not dupla.empty:
                    datos_dupla = dupla.iloc[0]

                    st.subheader(f"📊 {jugador} + {companero}")

                    c1, c2, c3, c4, c5 = st.columns(5)

                    c1.metric(
                        "PJ Juntos",
                        numero_entero_seguro(datos_dupla["PJ"])
                    )
                    c2.metric(
                        "Victorias",
                        numero_entero_seguro(datos_dupla["G"])
                    )
                    c3.metric(
                        "Empates",
                        numero_entero_seguro(datos_dupla["E"])
                    )
                    c4.metric(
                        "Derrotas",
                        numero_entero_seguro(datos_dupla["P"])
                    )
                    c5.metric(
                        "Win Rate",
                        f"{numero_decimal_seguro(datos_dupla['WinRate']):.1f}%"
                    )
                else:
                    st.warning("No se encontraron partidos juntos.")


# ==================================================
# TAB COMPARADOR
# ==================================================

with tab_comparador:
    st.subheader("⚔️ Comparar jugadores")
    st.caption(
        "Seleccioná dos jugadores para comparar rendimiento histórico, rachas y datos principales."
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

            comparacion = construir_comparacion(
                info_1,
                info_2,
                jugador_1,
                jugador_2
            )

            st.dataframe(
                comparacion,
                use_container_width=True,
                hide_index=True,
                height=430
            )

            st.divider()
            st.subheader("📡 Comparación visual normalizada")
            st.caption(
                "El gráfico normaliza cada métrica contra el mejor valor entre ambos jugadores. "
                "Sirve para comparar forma relativa, no valores absolutos."
            )

            fig_comparacion = construir_radar(
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
            st.subheader("🤝 Dupla entre ambos")

            dupla = parejas[
                (
                    (parejas["jugador_1"] == jugador_1)
                    & (parejas["jugador_2"] == jugador_2)
                )
                |
                (
                    (parejas["jugador_2"] == jugador_1)
                    & (parejas["jugador_1"] == jugador_2)
                )
            ]

            if dupla.empty:
                st.info("No se encontraron partidos juntos entre estos jugadores.")
            else:
                datos_dupla = dupla.iloc[0]

                d1, d2, d3, d4, d5 = st.columns(5)

                d1.metric(
                    "PJ juntos",
                    numero_entero_seguro(datos_dupla.get("PJ"))
                )
                d2.metric(
                    "Victorias",
                    numero_entero_seguro(datos_dupla.get("G"))
                )
                d3.metric(
                    "Empates",
                    numero_entero_seguro(datos_dupla.get("E"))
                )
                d4.metric(
                    "Derrotas",
                    numero_entero_seguro(datos_dupla.get("P"))
                )
                d5.metric(
                    "Win Rate",
                    f"{numero_decimal_seguro(datos_dupla.get('WinRate')):.1f}%"
                )
