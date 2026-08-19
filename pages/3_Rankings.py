import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION
# ==================================================

st.title("🏆 Rankings")

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


def agregar_posicion(dataframe):
    dataframe = dataframe.copy()

    if not dataframe.empty:
        dataframe.insert(0, "#", range(1, len(dataframe) + 1))

    return dataframe


def preparar_mayores_paternidades(rivales_df, minimo_enfrentamientos):
    if rivales_df.empty:
        return pd.DataFrame()

    base = rivales_df[
        rivales_df["pj"] >= minimo_enfrentamientos
    ].copy()

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
        .sort_values(
            ["Diferencia", "PJ", "WR dominador %", "Dominador", "Rival"],
            ascending=[False, False, False, True, True]
        )
    )


def preparar_mano_a_mano_parejo(rivales_df, minimo_enfrentamientos):
    if rivales_df.empty:
        return pd.DataFrame()

    base = rivales_df[
        rivales_df["pj"] >= minimo_enfrentamientos
    ].copy()

    if base.empty:
        return pd.DataFrame()

    base["Diferencia"] = (
        base["g_jugador_1"] - base["g_jugador_2"]
    ).abs()

    return (
        base
        .sort_values(
            ["Diferencia", "pj", "jugador_1", "jugador_2"],
            ascending=[True, False, True, True]
        )
        [[
            "jugador_1",
            "jugador_2",
            "pj",
            "g_jugador_1",
            "g_jugador_2",
            "E",
            "Diferencia"
        ]]
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


def preparar_dupla_nombre(dataframe):
    dataframe = dataframe.copy()
    dataframe["Dupla"] = dataframe["jugador_1"] + " + " + dataframe["jugador_2"]
    return dataframe


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    equipos = leer_tabla_completa("equipos_master")
    parejas = leer_tabla_completa("estadisticas_parejas")
    rivales = leer_tabla_completa("estadisticas_rivales")

except Exception as error:
    st.error("No se pudieron leer los rankings desde Supabase.")
    st.exception(error)
    st.stop()


if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if equipos.empty:
    st.warning("La tabla equipos_master no contiene registros.")
    st.stop()

if parejas.empty:
    st.warning("La tabla estadisticas_parejas no contiene registros.")
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
    "racha_activa",
    "tipo_racha_activa",
    "mejor_racha_ganadora",
    "racha_desde",
    "racha_hasta",
    "peor_racha_perdedora",
    "peor_racha_desde",
    "peor_racha_hasta"
]

columnas_equipos = [
    "equipo",
    "PJ",
    "G",
    "E",
    "P",
    "WinRate"
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

validaciones = [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("equipos_master", equipos, columnas_equipos),
    ("estadisticas_parejas", parejas, columnas_parejas)
]

if not rivales.empty:
    validaciones.append(("estadisticas_rivales", rivales, columnas_rivales))

for nombre_tabla, dataframe, columnas_requeridas in validaciones:
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
# NORMALIZACION NUMERICA Y FECHAS
# ==================================================

for columna in [
    "PJ",
    "G",
    "E",
    "P",
    "racha_activa",
    "mejor_racha_ganadora",
    "peor_racha_perdedora"
]:
    jugadores[columna] = pd.to_numeric(jugadores[columna], errors="coerce")

jugadores["WinRate"] = pd.to_numeric(jugadores["WinRate"], errors="coerce")

for columna in [
    "racha_desde",
    "racha_hasta",
    "peor_racha_desde",
    "peor_racha_hasta"
]:
    jugadores[columna] = pd.to_datetime(jugadores[columna], errors="coerce")

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    equipos[columna] = pd.to_numeric(equipos[columna], errors="coerce")

for columna in ["PJ", "G", "E", "P", "WinRate"]:
    parejas[columna] = pd.to_numeric(parejas[columna], errors="coerce")

for columna in [
    "pj",
    "g_jugador_1",
    "g_jugador_2",
    "E",
    "winrate_jugador_1",
    "winrate_jugador_2"
]:
    if columna in rivales.columns:
        rivales[columna] = pd.to_numeric(rivales[columna], errors="coerce")

jugadores = jugadores.dropna(subset=["jugador"]).copy()
equipos = equipos.dropna(subset=["equipo"]).copy()
parejas = parejas.dropna(subset=["jugador_1", "jugador_2"]).copy()
rivales = rivales.dropna(subset=["jugador_1", "jugador_2"]).copy() if not rivales.empty else rivales


# ==================================================
# FILTROS GLOBALES
# ==================================================

st.caption(
    "Los rankings históricos usan las tablas master recalculadas. "
    "Los mínimos aplican a rankings de Win Rate, duplas y rivalidades."
)

col_min, col_cantidad = st.columns(2)

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
    st.subheader(f"📈 Mejor Win Rate")
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
    st.subheader(f"📉 Menor Win Rate")
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
        .rename(columns={"equipo": "Equipo", "G": "Victorias", "Win Rate": "Win Rate %", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_equipos_g, "Equipo", "Victorias", " victorias")
    mostrar_ranking(agregar_posicion(ranking_equipos_g))

    st.divider()
    st.subheader(f"📈 Mejor Win Rate")
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
    parejas_nombre = preparar_dupla_nombre(parejas)

    st.subheader("👥 Duplas con más partidos juntos")
    ranking_duplas_pj = (
        parejas_nombre
        .sort_values(["PJ", "G", "WinRate", "jugador_1", "jugador_2"], ascending=[False, False, False, True, True])
        [["Dupla", "jugador_1", "jugador_2", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador_1": "Jugador 1", "jugador_2": "Jugador 2", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_pj, "Dupla", "PJ", " PJ")
    mostrar_ranking(agregar_posicion(ranking_duplas_pj))

    st.divider()
    st.subheader(f"🏆 Mejores duplas")
    ranking_duplas_wr = (
        parejas_nombre[parejas_nombre["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "G", "jugador_1", "jugador_2"], ascending=[False, False, False, True, True])
        [["Dupla", "jugador_1", "jugador_2", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador_1": "Jugador 1", "jugador_2": "Jugador 2", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_wr, "Dupla", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_duplas_wr))

    st.divider()
    st.subheader("🔥 Duplas más ganadoras")
    ranking_duplas_g = (
        parejas_nombre
        .sort_values(["G", "PJ", "WinRate", "jugador_1", "jugador_2"], ascending=[False, False, False, True, True])
        [["Dupla", "jugador_1", "jugador_2", "G", "PJ", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador_1": "Jugador 1", "jugador_2": "Jugador 2", "G": "Victorias", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_g, "Dupla", "Victorias", " victorias")
    mostrar_ranking(agregar_posicion(ranking_duplas_g))

    st.divider()
    st.subheader(f"📉 Duplas con menor Win Rate")
    ranking_duplas_bajo = (
        parejas_nombre[parejas_nombre["PJ"] >= minimo_partidos]
        .sort_values(["WinRate", "PJ", "P", "jugador_1", "jugador_2"], ascending=[True, False, False, True, True])
        [["Dupla", "jugador_1", "jugador_2", "PJ", "G", "E", "P", "WinRate"]]
        .head(cantidad_ranking)
        .rename(columns={"jugador_1": "Jugador 1", "jugador_2": "Jugador 2", "WinRate": "Win Rate %"})
    )
    mostrar_podio(ranking_duplas_bajo, "Dupla", "Win Rate %", "%")
    mostrar_ranking(agregar_posicion(ranking_duplas_bajo))


# ==================================================
# RIVALIDADES
# ==================================================

with tab_rivalidades:
    if rivales.empty:
        st.info("No hay datos de estadisticas_rivales para mostrar.")
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
        if not ranking_paternidades.empty:
            ranking_paternidades["Paternidad"] = (
                ranking_paternidades["Dominador"]
                + " sobre "
                + ranking_paternidades["Rival"]
            )
        mostrar_podio(ranking_paternidades, "Paternidad", "Diferencia", " diferencia")
        mostrar_ranking(agregar_posicion(ranking_paternidades))


# ==================================================
# RACHAS
# ==================================================

with tab_rachas:
    st.subheader("🔥 Rachas actuales")

    rachas_validas = jugadores[
        jugadores["racha_activa"].notna()
        & (jugadores["racha_activa"] > 0)
        & (jugadores["tipo_racha_activa"] != "Inactivo")
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
    st.subheader("🏆 Mejores rachas históricas positivas")
    mejores_rachas_historicas = jugadores[
        jugadores["mejor_racha_ganadora"].notna()
        & (jugadores["mejor_racha_ganadora"] > 0)
    ].copy()
    ranking_mejores_rachas = (
        mejores_rachas_historicas
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
    st.subheader("📉 Peores rachas históricas negativas")
    peores_rachas_historicas = jugadores[
        jugadores["peor_racha_perdedora"].notna()
        & (jugadores["peor_racha_perdedora"] > 0)
    ].copy()
    ranking_peores_rachas = (
        peores_rachas_historicas
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
