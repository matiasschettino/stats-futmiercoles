import streamlit as st
import pandas as pd
from itertools import combinations, product

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("🏆 Rankings")

supabase = get_supabase()


# ==================================================
# FUNCIONES BASICAS
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


def mostrar_ranking(dataframe, alto=420):
    if dataframe.empty:
        st.info("No hay registros que cumplan los requisitos del ranking.")
    else:
        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
            height=alto
        )


def formatear_fechas(dataframe, columnas):
    dataframe = dataframe.copy()

    for columna in columnas:
        if columna in dataframe.columns:
            dataframe[columna] = (
                pd.to_datetime(dataframe[columna], errors="coerce")
                .dt.strftime("%d/%m/%Y")
            )

    return dataframe


def numero_entero(valor):
    if valor is None or pd.isna(valor):
        return 0

    return int(valor)


def numero_decimal(valor):
    if valor is None or pd.isna(valor):
        return 0.0

    return float(valor)


def texto_seguro(valor, reemplazo="Sin datos"):
    if valor is None or pd.isna(valor) or str(valor).strip() == "":
        return reemplazo

    return str(valor)


def agregar_posicion(dataframe):
    dataframe = dataframe.copy()

    if not dataframe.empty:
        dataframe.insert(0, "#", range(1, len(dataframe) + 1))

    return dataframe


def mostrar_podio(dataframe, columna_nombre, columna_valor, sufijo="", cantidad=3):
    if dataframe.empty:
        return

    podio = dataframe.head(cantidad).copy()
    medallas = ["🥇", "🥈", "🥉"]
    columnas = st.columns(cantidad)

    for indice, (_, fila) in enumerate(podio.iterrows()):
        valor = fila.get(columna_valor)

        if isinstance(valor, float) and valor.is_integer():
            valor_texto = f"{int(valor)}{sufijo}"
        elif isinstance(valor, float):
            valor_texto = f"{valor:.1f}{sufijo}"
        else:
            valor_texto = f"{valor}{sufijo}"

        with columnas[indice]:
            st.info(
                f"{medallas[indice]} {texto_seguro(fila.get(columna_nombre))}\n\n"
                f"**{valor_texto}**"
            )


def filtrar_por_fechas(dataframe, fecha_desde, fecha_hasta, columna_fecha="fecha"):
    if dataframe.empty or columna_fecha not in dataframe.columns:
        return dataframe.copy()

    filtrado = dataframe.copy()
    filtrado[columna_fecha] = pd.to_datetime(filtrado[columna_fecha], errors="coerce")
    filtrado = filtrado[filtrado[columna_fecha].notna()].copy()

    if fecha_desde is not None:
        filtrado = filtrado[filtrado[columna_fecha].dt.date >= fecha_desde].copy()

    if fecha_hasta is not None:
        filtrado = filtrado[filtrado[columna_fecha].dt.date <= fecha_hasta].copy()

    return filtrado


# ==================================================
# PREPARACION DE DATOS
# ==================================================

def preparar_partidos(partidos):
    partidos = partidos.copy()

    if "fecha" not in partidos.columns:
        partidos["fecha"] = pd.NaT

    partidos["fecha"] = pd.to_datetime(partidos["fecha"], errors="coerce")
    partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
    partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")

    partidos["resultado_local"] = "E"
    partidos.loc[partidos["goles_local"] > partidos["goles_visitante"], "resultado_local"] = "G"
    partidos.loc[partidos["goles_local"] < partidos["goles_visitante"], "resultado_local"] = "P"

    return partidos


def preparar_participaciones_resultados(participaciones, partidos):
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
                "resultado_local"
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
    historial.loc[mask_visitante & (historial["resultado_local"] == "G"), "resultado_jugador"] = "P"
    historial.loc[mask_visitante & (historial["resultado_local"] == "P"), "resultado_jugador"] = "G"
    historial.loc[mask_visitante & (historial["resultado_local"] == "E"), "resultado_jugador"] = "E"

    historial = historial[
        historial["resultado_jugador"].isin(["G", "E", "P"])
    ].copy()

    return historial


def calcular_estadisticas_jugadores(historial):
    if historial.empty:
        return pd.DataFrame(columns=["jugador", "PJ", "G", "E", "P", "WinRate"])

    ranking = (
        historial
        .pivot_table(
            index="jugador",
            columns="resultado_jugador",
            aggfunc="size",
            fill_value=0
        )
        .reset_index()
    )

    ranking.columns.name = None

    for columna in ["G", "E", "P"]:
        if columna not in ranking.columns:
            ranking[columna] = 0

    ranking["PJ"] = ranking["G"] + ranking["E"] + ranking["P"]
    ranking["WinRate"] = (
        ranking["G"]
        / ranking["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return ranking[["jugador", "PJ", "G", "E", "P", "WinRate"]]


def calcular_estadisticas_equipos(partidos_filtrados):
    if partidos_filtrados.empty:
        return pd.DataFrame(columns=["equipo", "PJ", "G", "E", "P", "WinRate"])

    local = partidos_filtrados[
        ["id", "fecha", "equipo_local", "equipo_visitante", "resultado_local"]
    ].copy()
    local["equipo"] = local["equipo_local"]
    local["resultado_equipo"] = local["resultado_local"]

    visitante = partidos_filtrados[
        ["id", "fecha", "equipo_local", "equipo_visitante", "resultado_local"]
    ].copy()
    visitante["equipo"] = visitante["equipo_visitante"]
    visitante["resultado_equipo"] = visitante["resultado_local"].map(
        {
            "G": "P",
            "P": "G",
            "E": "E"
        }
    )

    resultados = pd.concat([local, visitante], ignore_index=True)
    resultados = resultados[
        resultados["equipo"].notna()
        & resultados["resultado_equipo"].isin(["G", "E", "P"])
    ].copy()

    ranking = (
        resultados
        .pivot_table(
            index="equipo",
            columns="resultado_equipo",
            aggfunc="size",
            fill_value=0
        )
        .reset_index()
    )

    ranking.columns.name = None

    for columna in ["G", "E", "P"]:
        if columna not in ranking.columns:
            ranking[columna] = 0

    ranking["PJ"] = ranking["G"] + ranking["E"] + ranking["P"]
    ranking["WinRate"] = (
        ranking["G"]
        / ranking["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return ranking[["equipo", "PJ", "G", "E", "P", "WinRate"]]


def calcular_estadisticas_duplas(historial):
    registros = []

    if historial.empty:
        return pd.DataFrame(columns=["Dupla", "PJ", "G", "E", "P", "WinRate"])

    for _, grupo_partido in historial.groupby("partido_id"):
        for equipo, grupo_equipo in grupo_partido.groupby("equipo"):
            jugadores_equipo = sorted(grupo_equipo["jugador"].dropna().astype(str).unique())

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
        return pd.DataFrame(columns=["Dupla", "PJ", "G", "E", "P", "WinRate"])

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
        resumen["G"]
        / resumen["PJ"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)
    resumen["Dupla"] = resumen["jugador_1"] + " + " + resumen["jugador_2"]

    return resumen[["Dupla", "PJ", "G", "E", "P", "WinRate"]]


def calcular_estadisticas_rivales(historial):
    registros = []

    if historial.empty:
        return pd.DataFrame(
            columns=[
                "jugador_1",
                "jugador_2",
                "pj",
                "g_jugador_1",
                "g_jugador_2",
                "E",
                "winrate_jugador_1",
                "winrate_jugador_2"
            ]
        )

    for _, grupo_partido in historial.groupby("partido_id"):
        equipos_partido = list(grupo_partido["equipo"].dropna().unique())

        if len(equipos_partido) < 2:
            continue

        grupo_local = grupo_partido[grupo_partido["equipo"] == equipos_partido[0]]
        grupo_visitante = grupo_partido[grupo_partido["equipo"] == equipos_partido[1]]

        for _, fila_1 in grupo_local.iterrows():
            for _, fila_2 in grupo_visitante.iterrows():
                jugador_a, jugador_b = sorted([fila_1["jugador"], fila_2["jugador"]])

                resultado_a = fila_1["resultado_jugador"] if fila_1["jugador"] == jugador_a else fila_2["resultado_jugador"]
                resultado_b = fila_2["resultado_jugador"] if fila_2["jugador"] == jugador_b else fila_1["resultado_jugador"]

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
        return pd.DataFrame(
            columns=[
                "jugador_1",
                "jugador_2",
                "pj",
                "g_jugador_1",
                "g_jugador_2",
                "E",
                "winrate_jugador_1",
                "winrate_jugador_2"
            ]
        )

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
        resumen["g_jugador_1"]
        / resumen["pj"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)
    resumen["winrate_jugador_2"] = (
        resumen["g_jugador_2"]
        / resumen["pj"].replace(0, pd.NA)
        * 100
    ).round(1).fillna(0)

    return resumen


def calcular_rachas_periodo(historial):
    registros = []

    if historial.empty:
        return pd.DataFrame()

    historial = historial.sort_values(["jugador", "fecha", "partido_id"]).copy()

    for jugador, grupo in historial.groupby("jugador"):
        resultados = grupo["resultado_jugador"].tolist()

        if not resultados:
            continue

        mejor_g = 0
        mejor_p = 0
        actual_g = 0
        actual_p = 0
        mejor_g_desde = pd.NaT
        mejor_g_hasta = pd.NaT
        mejor_p_desde = pd.NaT
        mejor_p_hasta = pd.NaT
        temp_g_desde = pd.NaT
        temp_p_desde = pd.NaT

        fechas = grupo["fecha"].tolist()

        for resultado, fecha in zip(resultados, fechas):
            if resultado == "G":
                if actual_g == 0:
                    temp_g_desde = fecha
                actual_g += 1
                if actual_g > mejor_g:
                    mejor_g = actual_g
                    mejor_g_desde = temp_g_desde
                    mejor_g_hasta = fecha
            else:
                actual_g = 0
                temp_g_desde = pd.NaT

            if resultado == "P":
                if actual_p == 0:
                    temp_p_desde = fecha
                actual_p += 1
                if actual_p > mejor_p:
                    mejor_p = actual_p
                    mejor_p_desde = temp_p_desde
                    mejor_p_hasta = fecha
            else:
                actual_p = 0
                temp_p_desde = pd.NaT

        ultimo_resultado = resultados[-1]
        racha_activa = 0

        for resultado in reversed(resultados):
            if resultado == ultimo_resultado:
                racha_activa += 1
            else:
                break

        registros.append(
            {
                "jugador": jugador,
                "tipo_racha_activa": ultimo_resultado,
                "racha_activa": racha_activa,
                "mejor_racha_ganadora": mejor_g,
                "racha_desde": mejor_g_desde,
                "racha_hasta": mejor_g_hasta,
                "peor_racha_perdedora": mejor_p,
                "peor_racha_desde": mejor_p_desde,
                "peor_racha_hasta": mejor_p_hasta,
                "PJ": len(resultados),
                "G": resultados.count("G"),
                "P": resultados.count("P"),
                "WinRate": round(resultados.count("G") / len(resultados) * 100, 1)
            }
        )

    return pd.DataFrame(registros)


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
        g_jugador_1 = numero_entero(fila["g_jugador_1"])
        g_jugador_2 = numero_entero(fila["g_jugador_2"])
        pj = numero_entero(fila["pj"])

        if g_jugador_1 >= g_jugador_2:
            dominador = jugador_1
            rival = jugador_2
            victorias_dominador = g_jugador_1
            victorias_rival = g_jugador_2
            wr_dominador = numero_decimal(fila["winrate_jugador_1"])
        else:
            dominador = jugador_2
            rival = jugador_1
            victorias_dominador = g_jugador_2
            victorias_rival = g_jugador_1
            wr_dominador = numero_decimal(fila["winrate_jugador_2"])

        registros.append(
            {
                "Paternidad": f"{dominador} sobre {rival}",
                "Dominador": dominador,
                "Rival": rival,
                "PJ": pj,
                "Victorias dominador": victorias_dominador,
                "Victorias rival": victorias_rival,
                "Diferencia": abs(victorias_dominador - victorias_rival),
                "WR dominador %": wr_dominador,
                "Empates": numero_entero(fila["E"])
            }
        )

    return (
        pd.DataFrame(registros)
        .sort_values(["Diferencia", "PJ", "WR dominador %", "Paternidad"], ascending=[False, False, False, True])
    )


def preparar_mano_a_mano_parejo(rivales_df, minimo_enfrentamientos):
    if rivales_df.empty:
        return pd.DataFrame()

    base = rivales_df[rivales_df["pj"] >= minimo_enfrentamientos].copy()

    if base.empty:
        return pd.DataFrame()

    base["Diferencia"] = (base["g_jugador_1"] - base["g_jugador_2"]).abs()

    return (
        base
        .sort_values(["Diferencia", "pj", "jugador_1", "jugador_2"], ascending=[True, False, True, True])
        [["jugador_1", "jugador_2", "pj", "g_jugador_1", "g_jugador_2", "E", "Diferencia"]]
        .rename(
            columns={
                "jugador_1": "Jugador 1",
                "jugador_2": "Jugador 2",
                "pj": "PJ enfrentados",
                "g_jugador_1": "Victorias J1",
                "g_jugador_2": "Victorias J2",
                "E": "Empates"
            }
        )
    )


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores_master = leer_tabla_completa("jugadores_master")
    equipos_master = leer_tabla_completa("equipos_master")
    participaciones = leer_tabla_completa("participaciones")
    partidos = leer_tabla_completa("partidos")

except Exception as error:
    st.error("No se pudieron leer los rankings desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores_master.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if equipos_master.empty:
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

columnas_jugadores = [
    "jugador",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
]

columnas_equipos = [
    "equipo",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
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
    ("jugadores_master", jugadores_master, columnas_jugadores),
    ("equipos_master", equipos_master, columnas_equipos),
    ("participaciones", participaciones, columnas_participaciones),
    ("partidos", partidos, columnas_partidos)
]:
    faltantes = [columna for columna in columnas_requeridas if columna not in dataframe.columns]

    if faltantes:
        st.error(f"Faltan columnas en {nombre_tabla}: " + ", ".join(faltantes))
        st.stop()


# ==================================================
# NORMALIZACION
# ==================================================

if "fecha" not in partidos.columns:
    partidos["fecha"] = pd.NaT

partidos = preparar_partidos(partidos)
historial_completo = preparar_participaciones_resultados(participaciones, partidos)

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    jugadores_master[columna] = pd.to_numeric(jugadores_master[columna], errors="coerce")
    equipos_master[columna] = pd.to_numeric(equipos_master[columna], errors="coerce")

jugadores_master = jugadores_master.dropna(subset=["jugador"]).copy()
equipos_master = equipos_master.dropna(subset=["equipo"]).copy()


# ==================================================
# FILTROS GLOBALES
# ==================================================

fechas_validas = pd.to_datetime(partidos["fecha"], errors="coerce").dropna()

if fechas_validas.empty:
    fecha_minima = None
    fecha_maxima = None
else:
    fecha_minima = fechas_validas.min().date()
    fecha_maxima = fechas_validas.max().date()

st.caption(
    "Los rankings se calculan con el período seleccionado. "
    "El mínimo aplica a Win Rate, duplas y rivalidades."
)

col_f1, col_f2, col_min, col_cantidad = st.columns(4)

with col_f1:
    fecha_desde = st.date_input(
        "Desde",
        value=fecha_minima,
        min_value=fecha_minima,
        max_value=fecha_maxima,
        disabled=fecha_minima is None
    )

with col_f2:
    fecha_hasta = st.date_input(
        "Hasta",
        value=fecha_maxima,
        min_value=fecha_minima,
        max_value=fecha_maxima,
        disabled=fecha_maxima is None
    )

with col_min:
    minimo_partidos = st.slider(
        "Mínimo de partidos / enfrentamientos",
        min_value=0,
        max_value=200,
        value=50,
        step=5
    )

with col_cantidad:
    cantidad_ranking = st.selectbox(
        "Cantidad a mostrar",
        [10, 20, 30, 50],
        index=0
    )

partidos_filtrados = filtrar_por_fechas(partidos, fecha_desde, fecha_hasta)
historial_filtrado = filtrar_por_fechas(historial_completo, fecha_desde, fecha_hasta)

jugadores = calcular_estadisticas_jugadores(historial_filtrado)
equipos = calcular_estadisticas_equipos(partidos_filtrados)
parejas = calcular_estadisticas_duplas(historial_filtrado)
rivales = calcular_estadisticas_rivales(historial_filtrado)
rachas = calcular_rachas_periodo(historial_filtrado)


# ==================================================
# PESTANAS
# ==================================================

tab_jugadores, tab_equipos, tab_duplas, tab_rivalidades, tab_rachas = st.tabs(
    [
        "👤 Jugadores",
        "⚽ Equipos",
        "🤝 Duplas",
        "⚔️ Rivalidades",
        "🔥 Rachas"
    ]
)


# ==================================================
# JUGADORES
# ==================================================

with tab_jugadores:
    st.subheader("🏃 Más partidos")
    ranking_pj = (
        jugadores
        .sort_values(["PJ", "G", "WinRate", "jugador"], ascending=[False, False, False, True])
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_pj, "Jugador", "PJ", " PJ")
    mostrar_ranking(agregar_posicion(ranking_pj))

    st.divider()
    st.subheader("🥇 Más victorias")
    ranking_victorias = (
        jugadores
        .sort_values(["G", "PJ", "WinRate", "jugador"], ascending=[False, False, False, True])
        [["jugador", "G", "PJ", "WinRate", "E", "P"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %", "G": "Victorias"})
    )
    mostrar_podio(ranking_victorias, "Jugador", "Victorias", " victorias")
    mostrar_ranking(agregar_posicion(ranking_victorias))

    st.divider()
    st.subheader("📈 Mejor Win Rate")
    ranking_wr = (
        jugadores[jugadores["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "G", "jugador"], ascending=[False, False, False, True])
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_wr, "Jugador", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_wr))

    st.divider()
    st.subheader("📉 Menor Win Rate")
    ranking_wr_bajo = (
        jugadores[jugadores["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "P", "jugador"], ascending=[True, False, False, True])
        [["jugador", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador": "Jugador", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_wr_bajo, "Jugador", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_wr_bajo))


# ==================================================
# EQUIPOS
# ==================================================

with tab_equipos:
    st.subheader("⚽ Equipos con más partidos")
    ranking_equipos_pj = (
        equipos
        .sort_values(["PJ", "G", "WinRate", "equipo"], ascending=[False, False, False, True])
        [["equipo", "PJ", "G", "E", "P", "WinRate"]]
        .head(5)
        .rename(columns={"equipo": "Equipo", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_equipos_pj, "Equipo", "PJ", " PJ")
    mostrar_ranking(agregar_posicion(ranking_equipos_pj))

    st.divider()
    st.subheader("🥇 Equipos con más victorias")
    ranking_equipos_g = (
        equipos
        .sort_values(["G", "PJ", "WinRate", "equipo"], ascending=[False, False, False, True])
        [["equipo", "G", "PJ", "E", "P", "WinRate"]]
        .head(5)
        .rename(columns={"equipo": "Equipo", "G": "Victorias", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_equipos_g, "Equipo", "Victorias", " victorias")
    mostrar_ranking(agregar_posicion(ranking_equipos_g))

    st.divider()
    st.subheader("📈 Mejor Win Rate")
    ranking_equipos_wr = (
        equipos[equipos["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "G", "equipo"], ascending=[False, False, False, True])
        [["equipo", "PJ", "G", "E", "P", "WinRate"]]
        .head(5)
        .rename(columns={"equipo": "Equipo", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_equipos_wr, "Equipo", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_equipos_wr))


# ==================================================
# DUPLAS
# ==================================================

with tab_duplas:
    st.subheader("👥 Duplas con más partidos juntos")
    ranking_duplas_pj = (
        parejas
        .sort_values(["PJ", "G", "WinRate", "Dupla"], ascending=[False, False, False, True])
        [["Dupla", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_pj, "Dupla", "PJ", " PJ")
    mostrar_ranking(agregar_posicion(ranking_duplas_pj))

    st.divider()
    st.subheader("🏆 Mejores duplas")
    ranking_duplas_wr = (
        parejas[parejas["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "G", "Dupla"], ascending=[False, False, False, True])
        [["Dupla", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_wr, "Dupla", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_duplas_wr))

    st.divider()
    st.subheader("🔥 Duplas más ganadoras")
    ranking_duplas_g = (
        parejas
        .sort_values(["G", "PJ", "WinRate", "Dupla"], ascending=[False, False, False, True])
        [["Dupla", "G", "PJ", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"G": "Victorias", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_g, "Dupla", "Victorias", " victorias")
    mostrar_ranking(agregar_posicion(ranking_duplas_g))

    st.divider()
    st.subheader("📉 Duplas con menor Win Rate")
    ranking_duplas_bajo = (
        parejas[parejas["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "P", "Dupla"], ascending=[True, False, False, True])
        [["Dupla", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_bajo, "Dupla", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_duplas_bajo))


# ==================================================
# RIVALIDADES
# ==================================================

with tab_rivalidades:
    if rivales.empty:
        st.info("No hay datos de rivalidades para el período seleccionado.")
    else:
        st.subheader("⚔️ Rivalidades más repetidas")
        ranking_rivalidades_pj = (
            rivales
            .sort_values(["pj", "g_jugador_1", "g_jugador_2", "jugador_1", "jugador_2"], ascending=[False, False, False, True, True])
            [["jugador_1", "jugador_2", "pj", "g_jugador_1", "g_jugador_2", "E"]]
            .head(cantidad_ranking)
            .rename(
                columns={
                    "jugador_1": "Jugador 1",
                    "jugador_2": "Jugador 2",
                    "pj": "PJ enfrentados",
                    "g_jugador_1": "Victorias J1",
                    "g_jugador_2": "Victorias J2",
                    "E": "Empates"
                }
            )
        )
        ranking_rivalidades_pj["Rivalidad"] = ranking_rivalidades_pj["Jugador 1"] + " vs " + ranking_rivalidades_pj["Jugador 2"]
        mostrar_podio(ranking_rivalidades_pj, "Rivalidad", "PJ enfrentados", " PJ")
        mostrar_ranking(agregar_posicion(ranking_rivalidades_pj))

        st.divider()
        st.subheader("⚖️ Mano a mano más parejos")
        ranking_parejos = preparar_mano_a_mano_parejo(rivales, minimo_partidos).head(cantidad_ranking)
        if not ranking_parejos.empty:
            ranking_parejos["Rivalidad"] = ranking_parejos["Jugador 1"] + " vs " + ranking_parejos["Jugador 2"]
        mostrar_podio(ranking_parejos, "Rivalidad", "Diferencia", " diferencia")
        mostrar_ranking(agregar_posicion(ranking_parejos))

        st.divider()
        st.subheader("👑 Mayores paternidades")
        ranking_paternidades = preparar_mayores_paternidades(rivales, minimo_partidos).head(cantidad_ranking)
        mostrar_podio(ranking_paternidades, "Paternidad", "Diferencia", " diferencia")
        mostrar_ranking(agregar_posicion(ranking_paternidades))


# ==================================================
# RACHAS
# ==================================================

with tab_rachas:
    if rachas.empty:
        st.info("No hay rachas para el período seleccionado.")
    else:
        st.subheader("🔥 Rachas actuales del período")

        rachas_validas = rachas[
            rachas["racha_activa"].notna()
            & (rachas["racha_activa"] > 0)
        ].copy()

        rachas_positivas = rachas_validas[rachas_validas["tipo_racha_activa"] == "G"].copy()
        rachas_negativas = rachas_validas[rachas_validas["tipo_racha_activa"] == "P"].copy()
        rachas_empates = rachas_validas[rachas_validas["tipo_racha_activa"] == "E"].copy()

        k1, k2, k3 = st.columns(3)
        k1.metric("En racha positiva", len(rachas_positivas))
        k2.metric("En racha negativa", len(rachas_negativas))
        k3.metric("En racha de empates", len(rachas_empates))

        st.divider()
        st.subheader("🔥 Rachas positivas actuales")
        ranking_positivo = (
            rachas_positivas
            .sort_values(["racha_activa", "WinRate", "PJ", "jugador"], ascending=[False, False, False, True])
            [["jugador", "racha_activa", "PJ", "G", "WinRate"]]
            .head(cantidad_ranking)
            .rename(columns={"jugador": "Jugador", "racha_activa": "Victorias consecutivas actuales", "WinRate": "Win Rate %"})
        )
        for columna in ["Victorias consecutivas actuales", "PJ", "G"]:
            if columna in ranking_positivo.columns:
                ranking_positivo[columna] = pd.to_numeric(ranking_positivo[columna], errors="coerce").fillna(0).astype(int)
        mostrar_podio(ranking_positivo, "Jugador", "Victorias consecutivas actuales", " victorias")
        mostrar_ranking(agregar_posicion(ranking_positivo), alto=360)

        st.divider()
        st.subheader("📉 Rachas negativas actuales")
        ranking_negativo = (
            rachas_negativas
            .sort_values(["racha_activa", "WinRate", "PJ", "jugador"], ascending=[False, True, False, True])
            [["jugador", "racha_activa", "PJ", "P", "WinRate"]]
            .head(cantidad_ranking)
            .rename(columns={"jugador": "Jugador", "racha_activa": "Derrotas consecutivas actuales", "WinRate": "Win Rate %"})
        )
        for columna in ["Derrotas consecutivas actuales", "PJ", "P"]:
            if columna in ranking_negativo.columns:
                ranking_negativo[columna] = pd.to_numeric(ranking_negativo[columna], errors="coerce").fillna(0).astype(int)
        mostrar_podio(ranking_negativo, "Jugador", "Derrotas consecutivas actuales", " derrotas")
        mostrar_ranking(agregar_posicion(ranking_negativo), alto=360)

        st.divider()
        st.subheader("🏆 Mejores rachas positivas del período")
        ranking_mejores_rachas = (
            rachas[rachas["mejor_racha_ganadora"] > 0]
            .sort_values(["mejor_racha_ganadora", "WinRate", "PJ", "jugador"], ascending=[False, False, False, True])
            [["jugador", "mejor_racha_ganadora", "racha_desde", "racha_hasta", "PJ", "G", "WinRate"]]
            .head(cantidad_ranking)
            .rename(
                columns={
                    "jugador": "Jugador",
                    "mejor_racha_ganadora": "Victorias consecutivas",
                    "racha_desde": "Desde",
                    "racha_hasta": "Hasta",
                    "PJ": "Partidos totales",
                    "G": "Victorias totales",
                    "WinRate": "Win Rate %"
                }
            )
        )
        ranking_mejores_rachas = formatear_fechas(ranking_mejores_rachas, ["Desde", "Hasta"])
        for columna in ["Victorias consecutivas", "Partidos totales", "Victorias totales"]:
            if columna in ranking_mejores_rachas.columns:
                ranking_mejores_rachas[columna] = pd.to_numeric(ranking_mejores_rachas[columna], errors="coerce").fillna(0).astype(int)
        mostrar_podio(ranking_mejores_rachas, "Jugador", "Victorias consecutivas", " victorias")
        mostrar_ranking(agregar_posicion(ranking_mejores_rachas), alto=420)

        st.divider()
        st.subheader("📉 Peores rachas negativas del período")
        ranking_peores_rachas = (
            rachas[rachas["peor_racha_perdedora"] > 0]
            .sort_values(["peor_racha_perdedora", "WinRate", "PJ", "jugador"], ascending=[False, True, False, True])
            [["jugador", "peor_racha_perdedora", "peor_racha_desde", "peor_racha_hasta", "PJ", "P", "WinRate"]]
            .head(cantidad_ranking)
            .rename(
                columns={
                    "jugador": "Jugador",
                    "peor_racha_perdedora": "Derrotas consecutivas",
                    "peor_racha_desde": "Desde",
                    "peor_racha_hasta": "Hasta",
                    "PJ": "Partidos totales",
                    "P": "Derrotas totales",
                    "WinRate": "Win Rate %"
                }
            )
        )
        ranking_peores_rachas = formatear_fechas(ranking_peores_rachas, ["Desde", "Hasta"])
        for columna in ["Derrotas consecutivas", "Partidos totales", "Derrotas totales"]:
            if columna in ranking_peores_rachas.columns:
                ranking_peores_rachas[columna] = pd.to_numeric(ranking_peores_rachas[columna], errors="coerce").fillna(0).astype(int)
        mostrar_podio(ranking_peores_rachas, "Jugador", "Derrotas consecutivas", " derrotas")
        mostrar_ranking(agregar_posicion(ranking_peores_rachas), alto=420)
