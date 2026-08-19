import streamlit as st
import pandas as pd
from datetime import date, datetime
from itertools import combinations

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION Y LOGIN
# ==================================================

st.title("🔄 Admin - Recalcular Estadísticas")

usuario = st.text_input("Usuario")
password = st.text_input("Contraseña", type="password")

if (
    usuario != st.secrets["ADMIN_USER"]
    or password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning("Acceso restringido")
    st.stop()

st.success("✅ Acceso autorizado")

supabase = get_supabase()


# ==================================================
# INICIALIZACION DE SESSION STATE
# ==================================================

valores_iniciales = {
    "chequeo_realizado": False,
    "backup_generado": False,
    "backup_parejas_generado": False,
    "backup_registros": None,
    "jugadores_master_registros": None,
    "backup_parejas_registros": None,
    "estadisticas_parejas_registros": None,
    "backup_equipos_registros": None,
    "equipos_master_registros": None,
    "backup_equipos_generado": False,
    "backup_rivales_registros": None,
    "estadisticas_rivales_registros": None,
    "backup_rivales_generado": False
}

for clave, valor_inicial in valores_iniciales.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor_inicial


# ==================================================
# FUNCIONES AUXILIARES
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


def valor_json(valor):
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.isoformat()

    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except (ValueError, AttributeError):
            pass

    # Evita errores de Supabase/Postgres en columnas bigint.
    # Cuando pandas lee una columna entera con nulos, puede devolver 1.0.
    # Postgres bigint no acepta valores con decimal como "1.0".
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)

    if isinstance(valor, str):
        texto = valor.strip()
        try:
            numero = float(texto)
            if texto.endswith(".0") and numero.is_integer():
                return int(numero)
        except ValueError:
            pass

    return valor


def dataframe_a_registros(df):
    registros = []

    for fila in df.to_dict("records"):
        registros.append(
            {
                columna: valor_json(valor)
                for columna, valor in fila.items()
            }
        )

    return registros


def convertir_columnas_enteras(df, columnas):
    df = df.copy()

    for columna in columnas:
        if columna in df.columns:
            df[columna] = pd.to_numeric(
                df[columna],
                errors="coerce"
            ).astype("Int64")

    return df


def insertar_en_lotes(tabla, registros, lote=500):
    for inicio in range(0, len(registros), lote):
        bloque = registros[inicio:inicio + lote]
        supabase.table(tabla).insert(bloque).execute()


def upsert_en_lotes(tabla, registros, conflicto, lote=500):
    for inicio in range(0, len(registros), lote):
        bloque = registros[inicio:inicio + lote]
        (
            supabase
            .table(tabla)
            .upsert(bloque, on_conflict=conflicto)
            .execute()
        )


COLUMNAS_ENTERAS_JUGADORES = [
    "PJ",
    "G",
    "E",
    "P",
    "partidos_equipo_favorito",
    "pj_mejor_companero",
    "pj_vs_rival_mas_frecuente",
    "mejor_racha_ganadora",
    "peor_racha_perdedora",
    "racha_activa"
]

COLUMNAS_ENTERAS_PAREJAS = [
    "E",
    "G",
    "PJ",
    "P"
]

COLUMNAS_ENTERAS_EQUIPOS = [
    "PJ",
    "G",
    "E",
    "P",
    "pj_jugador_mas_presente",
    "pj_mejor_jugador"
]

COLUMNAS_ENTERAS_RIVALES = [
    "pj",
    "g_jugador_1",
    "g_jugador_2",
    "E"
]


# ==================================================
# CHEQUEO Y RECALCULO
# ==================================================

if st.button("🔄 Ejecutar Chequeo", key="btn_ejecutar_chequeo"):
    try:
        partidos_df = leer_tabla_completa("partidos")
        participaciones_df = leer_tabla_completa("participaciones")
        jugadores_master_df = leer_tabla_completa("jugadores_master")
        estadisticas_parejas_actual_df = leer_tabla_completa(
            "estadisticas_parejas"
        )
        equipos_master_actual_df = leer_tabla_completa(
            "equipos_master"
        )
        estadisticas_rivales_actual_df = leer_tabla_completa(
            "estadisticas_rivales"
        )

        if partidos_df.empty:
            raise ValueError("La tabla partidos está vacía.")

        if participaciones_df.empty:
            raise ValueError("La tabla participaciones está vacía.")

        st.subheader("📊 Datos leídos")
        st.write(f"Partidos: {len(partidos_df)}")
        st.write(f"Participaciones: {len(participaciones_df)}")
        st.write(f"Jugadores Master: {len(jugadores_master_df)}")
        st.write(
            "Estadísticas de parejas actuales: "
            f"{len(estadisticas_parejas_actual_df)}"
        )
        st.write(
            f"Equipos Master actuales: {len(equipos_master_actual_df)}"
        )
        st.write(
            "Estadísticas de rivales actuales: "
            f"{len(estadisticas_rivales_actual_df)}"
        )

        # ==========================================
        # RESULTADO LOCAL Y RESULTADO POR JUGADOR
        # ==========================================

        partidos_df["goles_local"] = pd.to_numeric(
            partidos_df["goles_local"],
            errors="coerce"
        )
        partidos_df["goles_visitante"] = pd.to_numeric(
            partidos_df["goles_visitante"],
            errors="coerce"
        )
        partidos_df["fecha"] = pd.to_datetime(
            partidos_df["fecha"],
            errors="coerce"
        )

        partidos_df["resultado_local"] = "E"
        partidos_df.loc[
            partidos_df["goles_local"] > partidos_df["goles_visitante"],
            "resultado_local"
        ] = "G"
        partidos_df.loc[
            partidos_df["goles_local"] < partidos_df["goles_visitante"],
            "resultado_local"
        ] = "P"

        participaciones_df = participaciones_df.merge(
            partidos_df[
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

        participaciones_df["resultado_jugador"] = ""

        mask_local = (
            participaciones_df["equipo"]
            == participaciones_df["equipo_local"]
        )
        mask_visitante = (
            participaciones_df["equipo"]
            == participaciones_df["equipo_visitante"]
        )

        participaciones_df.loc[
            mask_local,
            "resultado_jugador"
        ] = participaciones_df["resultado_local"]

        participaciones_df.loc[
            mask_visitante
            & (participaciones_df["resultado_local"] == "G"),
            "resultado_jugador"
        ] = "P"
        participaciones_df.loc[
            mask_visitante
            & (participaciones_df["resultado_local"] == "P"),
            "resultado_jugador"
        ] = "G"
        participaciones_df.loc[
            mask_visitante
            & (participaciones_df["resultado_local"] == "E"),
            "resultado_jugador"
        ] = "E"

        sin_resultado = participaciones_df[
            ~participaciones_df["resultado_jugador"].isin(["G", "E", "P"])
        ]

        if not sin_resultado.empty:
            st.warning(
                f"Hay {len(sin_resultado)} participaciones sin resultado válido. "
                "No se incluirán en PJ/G/E/P."
            )

        participaciones_validas = participaciones_df[
            participaciones_df["resultado_jugador"].isin(["G", "E", "P"])
        ].copy()

        # ==========================================
        # ESTADISTICAS BASICAS
        # ==========================================

        estadisticas_jugador = (
            participaciones_validas
            .pivot_table(
                index="jugador",
                columns="resultado_jugador",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        estadisticas_jugador.columns.name = None

        for columna in ["G", "E", "P"]:
            if columna not in estadisticas_jugador.columns:
                estadisticas_jugador[columna] = 0

        estadisticas_jugador["PJ"] = (
            estadisticas_jugador["G"]
            + estadisticas_jugador["E"]
            + estadisticas_jugador["P"]
        )

        estadisticas_jugador["WinRate"] = (
            estadisticas_jugador["G"]
            / estadisticas_jugador["PJ"].replace(0, pd.NA)
            * 100
        ).round(2).fillna(0)

        # ==========================================
        # EQUIPO FAVORITO
        # ==========================================

        partidos_por_equipo = (
            participaciones_validas
            .groupby(["jugador", "equipo"])
            .size()
            .reset_index(name="partidos")
            .sort_values(
                ["jugador", "partidos", "equipo"],
                ascending=[True, False, True]
            )
        )

        equipo_favorito = (
            partidos_por_equipo
            .groupby("jugador", as_index=False)
            .first()
            .rename(
                columns={
                    "equipo": "equipo_favorito",
                    "partidos": "partidos_equipo_favorito"
                }
            )
        )

        estadisticas_jugador = estadisticas_jugador.merge(
            equipo_favorito[
                [
                    "jugador",
                    "equipo_favorito",
                    "partidos_equipo_favorito"
                ]
            ],
            on="jugador",
            how="left"
        )

        # ==========================================
        # ESTADISTICAS DE PAREJAS
        # ==========================================

        parejas_resultado = []

        for _, grupo in participaciones_validas.groupby("partido_id"):
            for _, jugadores_equipo in grupo.groupby("equipo"):
                lista_jugadores = sorted(
                    jugadores_equipo["jugador"].dropna().unique()
                )

                if len(lista_jugadores) < 2:
                    continue

                resultado = jugadores_equipo["resultado_jugador"].iloc[0]

                for jugador_1, jugador_2 in combinations(lista_jugadores, 2):
                    parejas_resultado.append(
                        {
                            "jugador_1": jugador_1,
                            "jugador_2": jugador_2,
                            "resultado": resultado
                        }
                    )

        if not parejas_resultado:
            raise ValueError("No se pudieron calcular estadísticas de parejas.")

        parejas_df = pd.DataFrame(parejas_resultado)

        estadisticas_parejas = (
            parejas_df
            .pivot_table(
                index=["jugador_1", "jugador_2"],
                columns="resultado",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        estadisticas_parejas.columns.name = None

        for columna in ["G", "E", "P"]:
            if columna not in estadisticas_parejas.columns:
                estadisticas_parejas[columna] = 0

        estadisticas_parejas["PJ"] = (
            estadisticas_parejas["G"]
            + estadisticas_parejas["E"]
            + estadisticas_parejas["P"]
        )

        estadisticas_parejas["WinRate"] = (
            estadisticas_parejas["G"]
            / estadisticas_parejas["PJ"].replace(0, pd.NA)
            * 100
        ).round(2).fillna(0)

        # ==========================================
        # MEJOR COMPAÑERO
        # ==========================================

        parejas_bidireccional = pd.concat(
            [
                estadisticas_parejas.rename(
                    columns={
                        "jugador_1": "jugador",
                        "jugador_2": "companero"
                    }
                ),
                estadisticas_parejas.rename(
                    columns={
                        "jugador_2": "jugador",
                        "jugador_1": "companero"
                    }
                )
            ],
            ignore_index=True
        )

        mejor_companero = (
            parejas_bidireccional
            .sort_values(
                ["jugador", "PJ", "companero"],
                ascending=[True, False, True]
            )
            .groupby("jugador", as_index=False)
            .first()
        )

        estadisticas_jugador = estadisticas_jugador.merge(
            mejor_companero[
                ["jugador", "companero", "PJ", "WinRate"]
            ].rename(
                columns={
                    "companero": "mejor_companero",
                    "PJ": "pj_mejor_companero",
                    "WinRate": "wr_mejor_companero"
                }
            ),
            on="jugador",
            how="left"
        )

        # ==========================================
        # RIVAL MAS FRECUENTE
        # ==========================================

        enfrentamientos = []

        for _, grupo in participaciones_validas.groupby("partido_id"):
            equipos = grupo["equipo"].dropna().unique()

            if len(equipos) != 2:
                continue

            jugadores_1 = grupo[
                grupo["equipo"] == equipos[0]
            ]["jugador"].dropna().unique()

            jugadores_2 = grupo[
                grupo["equipo"] == equipos[1]
            ]["jugador"].dropna().unique()

            for jugador_1 in jugadores_1:
                for jugador_2 in jugadores_2:
                    enfrentamientos.append(
                        {"jugador": jugador_1, "rival": jugador_2}
                    )
                    enfrentamientos.append(
                        {"jugador": jugador_2, "rival": jugador_1}
                    )

        if not enfrentamientos:
            raise ValueError("No se pudieron calcular rivales frecuentes.")

        enfrentamientos_df = pd.DataFrame(enfrentamientos)

        rival_principal = (
            enfrentamientos_df
            .groupby(["jugador", "rival"])
            .size()
            .reset_index(name="partidos")
            .sort_values(
                ["jugador", "partidos", "rival"],
                ascending=[True, False, True]
            )
            .groupby("jugador", as_index=False)
            .first()
            .rename(
                columns={
                    "rival": "rival_mas_frecuente",
                    "partidos": "pj_vs_rival_mas_frecuente"
                }
            )
        )

        estadisticas_jugador = estadisticas_jugador.merge(
            rival_principal[
                [
                    "jugador",
                    "rival_mas_frecuente",
                    "pj_vs_rival_mas_frecuente"
                ]
            ],
            on="jugador",
            how="left"
        )

        # ==========================================
        # ESTADISTICAS DE RIVALES DIRECTOS
        # ==========================================

        enfrentamientos_directos = []

        for _, grupo in participaciones_validas.groupby("partido_id"):
            equipos_partido = grupo["equipo"].dropna().unique()

            if len(equipos_partido) != 2:
                continue

            equipo_1 = equipos_partido[0]
            equipo_2 = equipos_partido[1]

            jugadores_equipo_1 = grupo[
                grupo["equipo"] == equipo_1
            ][
                [
                    "jugador",
                    "resultado_jugador"
                ]
            ].dropna()

            jugadores_equipo_2 = grupo[
                grupo["equipo"] == equipo_2
            ][
                [
                    "jugador",
                    "resultado_jugador"
                ]
            ].dropna()

            for _, fila_1 in jugadores_equipo_1.iterrows():
                for _, fila_2 in jugadores_equipo_2.iterrows():
                    jugador_a = fila_1["jugador"]
                    jugador_b = fila_2["jugador"]

                    resultado_a = fila_1["resultado_jugador"]
                    resultado_b = fila_2["resultado_jugador"]

                    jugador_1, jugador_2 = sorted(
                        [
                            jugador_a,
                            jugador_b
                        ]
                    )

                    if jugador_a == jugador_1:
                        resultado_jugador_1 = resultado_a
                        resultado_jugador_2 = resultado_b
                    else:
                        resultado_jugador_1 = resultado_b
                        resultado_jugador_2 = resultado_a

                    enfrentamientos_directos.append(
                        {
                            "jugador_1": jugador_1,
                            "jugador_2": jugador_2,
                            "resultado_jugador_1": resultado_jugador_1,
                            "resultado_jugador_2": resultado_jugador_2
                        }
                    )

        if enfrentamientos_directos:
            enfrentamientos_directos_df = pd.DataFrame(
                enfrentamientos_directos
            )

            estadisticas_rivales = (
                enfrentamientos_directos_df
                .groupby(
                    [
                        "jugador_1",
                        "jugador_2"
                    ]
                )
                .agg(
                    pj=(
                        "resultado_jugador_1",
                        "size"
                    ),
                    g_jugador_1=(
                        "resultado_jugador_1",
                        lambda resultados: (resultados == "G").sum()
                    ),
                    g_jugador_2=(
                        "resultado_jugador_2",
                        lambda resultados: (resultados == "G").sum()
                    ),
                    E=(
                        "resultado_jugador_1",
                        lambda resultados: (resultados == "E").sum()
                    )
                )
                .reset_index()
            )

            estadisticas_rivales["winrate_jugador_1"] = (
                estadisticas_rivales["g_jugador_1"]
                / estadisticas_rivales["pj"].replace(0, pd.NA)
                * 100
            ).round(2).fillna(0)

            estadisticas_rivales["winrate_jugador_2"] = (
                estadisticas_rivales["g_jugador_2"]
                / estadisticas_rivales["pj"].replace(0, pd.NA)
                * 100
            ).round(2).fillna(0)
        else:
            estadisticas_rivales = pd.DataFrame(
                columns=[
                    "jugador_1",
                    "jugador_2",
                    "PJ",
                    "g_jugador_1",
                    "g_jugador_2",
                    "E",
                    "winrate_jugador_1",
                    "winrate_jugador_2"
                ]
            )

        # ==========================================
        # PARTIDOS ORDENADOS Y RACHAS HISTORICAS
        # ==========================================

        partidos_ordenados = (
            participaciones_validas[
                ["jugador", "partido_id", "resultado_jugador"]
            ]
            .merge(
                partidos_df[["id", "fecha"]],
                left_on="partido_id",
                right_on="id",
                how="left"
            )
            .dropna(subset=["fecha"])
            .sort_values(["jugador", "fecha", "partido_id"])
        )

        mejores_rachas = []

        for jugador, grupo in partidos_ordenados.groupby("jugador"):
            # RACHA GANADORA
            mejor_racha = 0
            mejor_desde = None
            mejor_hasta = None
            racha_actual = 0
            fecha_inicio_actual = None

            # RACHA PERDEDORA
            peor_racha = 0
            peor_desde = None
            peor_hasta = None
            racha_perdedora_actual = 0
            fecha_inicio_perdedora = None

            for _, fila in grupo.iterrows():
                resultado = fila["resultado_jugador"]
                fecha = fila["fecha"]

                # RACHA GANADORA
                if resultado == "G":
                    if racha_actual == 0:
                        fecha_inicio_actual = fecha

                    racha_actual += 1

                    if racha_actual > mejor_racha:
                        mejor_racha = racha_actual
                        mejor_desde = fecha_inicio_actual
                        mejor_hasta = fecha
                else:
                    racha_actual = 0
                    fecha_inicio_actual = None

                # RACHA PERDEDORA
                if resultado == "P":
                    if racha_perdedora_actual == 0:
                        fecha_inicio_perdedora = fecha

                    racha_perdedora_actual += 1

                    if racha_perdedora_actual > peor_racha:
                        peor_racha = racha_perdedora_actual
                        peor_desde = fecha_inicio_perdedora
                        peor_hasta = fecha
                else:
                    racha_perdedora_actual = 0
                    fecha_inicio_perdedora = None

            mejores_rachas.append(
                {
                    "jugador": jugador,
                    "mejor_racha_ganadora": mejor_racha,
                    "racha_desde": (
                        mejor_desde.date()
                        if pd.notnull(mejor_desde)
                        else None
                    ),
                    "racha_hasta": (
                        mejor_hasta.date()
                        if pd.notnull(mejor_hasta)
                        else None
                    ),
                    "peor_racha_perdedora": peor_racha,
                    "peor_racha_desde": (
                        peor_desde.date()
                        if pd.notnull(peor_desde)
                        else None
                    ),
                    "peor_racha_hasta": (
                        peor_hasta.date()
                        if pd.notnull(peor_hasta)
                        else None
                    )
                }
            )

        mejores_rachas_df = pd.DataFrame(mejores_rachas)

        estadisticas_jugador = estadisticas_jugador.merge(
            mejores_rachas_df,
            on="jugador",
            how="left"
        )

        # ==========================================
        # RACHA ACTIVA: SOLO JUGADORES DEL ULTIMO AÑO
        # ==========================================

        fecha_maxima = partidos_df["fecha"].max()

        if pd.isna(fecha_maxima):
            raise ValueError("No se pudo determinar la fecha máxima de partidos.")

        fecha_corte = fecha_maxima - pd.Timedelta(days=365)

        jugadores_activos = set(
            partidos_ordenados.loc[
                partidos_ordenados["fecha"] >= fecha_corte,
                "jugador"
            ].unique()
        )

        rachas_activas = []

        for jugador, grupo in partidos_ordenados.groupby("jugador"):
            if jugador not in jugadores_activos:
                rachas_activas.append(
                    {
                        "jugador": jugador,
                        "racha_activa": None,
                        "tipo_racha_activa": "Inactivo"
                    }
                )
                continue

            grupo = grupo.sort_values(["fecha", "partido_id"])
            resultados = grupo["resultado_jugador"].tolist()

            if not resultados:
                rachas_activas.append(
                    {
                        "jugador": jugador,
                        "racha_activa": None,
                        "tipo_racha_activa": "Inactivo"
                    }
                )
                continue

            ultimo_resultado = resultados[-1]
            contador = 0

            for resultado in reversed(resultados):
                if resultado == ultimo_resultado:
                    contador += 1
                else:
                    break

            rachas_activas.append(
                {
                    "jugador": jugador,
                    "racha_activa": contador,
                    "tipo_racha_activa": ultimo_resultado
                }
            )

        rachas_activas_df = pd.DataFrame(rachas_activas)

        estadisticas_jugador = estadisticas_jugador.merge(
            rachas_activas_df,
            on="jugador",
            how="left"
        )

        # ==========================================
        # ESTADISTICAS DE EQUIPOS
        # ==========================================

        equipos_local = partidos_df[
            ["id", "equipo_local", "resultado_local"]
        ].rename(
            columns={
                "equipo_local": "equipo",
                "resultado_local": "resultado_equipo"
            }
        )

        equipos_visitante = partidos_df[
            ["id", "equipo_visitante", "resultado_local"]
        ].rename(
            columns={
                "equipo_visitante": "equipo"
            }
        )

        equipos_visitante["resultado_equipo"] = (
            equipos_visitante["resultado_local"].map(
                {
                    "G": "P",
                    "P": "G",
                    "E": "E"
                }
            )
        )

        equipos_visitante = equipos_visitante.drop(
            columns=["resultado_local"]
        )

        resultados_equipos = pd.concat(
            [
                equipos_local,
                equipos_visitante
            ],
            ignore_index=True
        )

        resultados_equipos = resultados_equipos[
            resultados_equipos["equipo"].notna()
            & resultados_equipos["resultado_equipo"].isin(["G", "E", "P"])
        ].copy()

        estadisticas_equipos = (
            resultados_equipos
            .pivot_table(
                index="equipo",
                columns="resultado_equipo",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        estadisticas_equipos.columns.name = None

        for columna in ["G", "E", "P"]:
            if columna not in estadisticas_equipos.columns:
                estadisticas_equipos[columna] = 0

        estadisticas_equipos["PJ"] = (
            estadisticas_equipos["G"]
            + estadisticas_equipos["E"]
            + estadisticas_equipos["P"]
        )

        estadisticas_equipos["WinRate"] = (
            estadisticas_equipos["G"]
            / estadisticas_equipos["PJ"].replace(0, pd.NA)
            * 100
        ).round(2).fillna(0)

        # ==========================================
        # JUGADOR MAS PRESENTE POR EQUIPO
        # ==========================================

        presencias_equipo = (
            participaciones_validas
            .groupby(["equipo", "jugador"])
            .size()
            .reset_index(name="pj_jugador_mas_presente")
            .sort_values(
                ["equipo", "pj_jugador_mas_presente", "jugador"],
                ascending=[True, False, True]
            )
        )

        jugador_mas_presente = (
            presencias_equipo
            .groupby("equipo", as_index=False)
            .first()
            .rename(
                columns={
                    "jugador": "jugador_mas_presente"
                }
            )
        )

        # ==========================================
        # MEJOR JUGADOR HISTORICO POR EQUIPO
        # Minimo 20 partidos
        # ==========================================

        rendimiento_jugador_equipo = (
            participaciones_validas
            .pivot_table(
                index=["equipo", "jugador"],
                columns="resultado_jugador",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        rendimiento_jugador_equipo.columns.name = None

        for columna in ["G", "E", "P"]:
            if columna not in rendimiento_jugador_equipo.columns:
                rendimiento_jugador_equipo[columna] = 0

        rendimiento_jugador_equipo["pj_mejor_jugador"] = (
            rendimiento_jugador_equipo["G"]
            + rendimiento_jugador_equipo["E"]
            + rendimiento_jugador_equipo["P"]
        )

        rendimiento_jugador_equipo["wr_mejor_jugador"] = (
            rendimiento_jugador_equipo["G"]
            / rendimiento_jugador_equipo["pj_mejor_jugador"].replace(0, pd.NA)
            * 100
        ).round(2).fillna(0)

        candidatos_mejor_jugador = rendimiento_jugador_equipo[
            rendimiento_jugador_equipo["pj_mejor_jugador"] >= 20
        ].copy()

        if candidatos_mejor_jugador.empty:
            mejor_jugador_historico = pd.DataFrame(
                columns=[
                    "equipo",
                    "mejor_jugador_historico",
                    "pj_mejor_jugador",
                    "wr_mejor_jugador"
                ]
            )
        else:
            mejor_jugador_historico = (
                candidatos_mejor_jugador
                .sort_values(
                    [
                        "equipo",
                        "wr_mejor_jugador",
                        "pj_mejor_jugador",
                        "jugador"
                    ],
                    ascending=[True, False, False, True]
                )
                .groupby("equipo", as_index=False)
                .first()
                .rename(
                    columns={
                        "jugador": "mejor_jugador_historico"
                    }
                )
            )

        equipos_master_nuevo = (
            estadisticas_equipos
            .merge(
                jugador_mas_presente[
                    [
                        "equipo",
                        "jugador_mas_presente",
                        "pj_jugador_mas_presente"
                    ]
                ],
                on="equipo",
                how="left"
            )
            .merge(
                mejor_jugador_historico[
                    [
                        "equipo",
                        "mejor_jugador_historico",
                        "pj_mejor_jugador",
                        "wr_mejor_jugador"
                    ]
                ],
                on="equipo",
                how="left"
            )
        )

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

        equipos_master_nuevo = equipos_master_nuevo[
            columnas_equipos
        ].copy()

        for columna in [
            "PJ",
            "G",
            "E",
            "P",
            "pj_jugador_mas_presente",
            "pj_mejor_jugador"
        ]:
            equipos_master_nuevo[columna] = pd.to_numeric(
                equipos_master_nuevo[columna],
                errors="coerce"
            ).astype("Int64")

        for columna in ["WinRate", "wr_mejor_jugador"]:
            equipos_master_nuevo[columna] = pd.to_numeric(
                equipos_master_nuevo[columna],
                errors="coerce"
            ).round(2)

        # ==========================================
        # DATASET FINAL
        # ==========================================

        columnas_finales = [
            "jugador",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate",
            "equipo_favorito",
            "partidos_equipo_favorito",
            "mejor_companero",
            "pj_mejor_companero",
            "wr_mejor_companero",
            "rival_mas_frecuente",
            "pj_vs_rival_mas_frecuente",
            "mejor_racha_ganadora",
            "racha_desde",
            "racha_hasta",
            "peor_racha_perdedora",
            "peor_racha_desde",
            "peor_racha_hasta",
            "racha_activa",
            "tipo_racha_activa"
        ]

        jugadores_master_nuevo = estadisticas_jugador[
            columnas_finales
        ].copy()

        # Supabase define estas columnas como bigint.
        # Se convierten explícitamente para evitar valores como "2.0".
        for columna in COLUMNAS_ENTERAS_JUGADORES:
            jugadores_master_nuevo[columna] = pd.to_numeric(
                jugadores_master_nuevo[columna],
                errors="coerce"
            ).astype("Int64")

        columnas_decimales = [
            "WinRate",
            "wr_mejor_companero"
        ]

        for columna in columnas_decimales:
            jugadores_master_nuevo[columna] = pd.to_numeric(
                jugadores_master_nuevo[columna],
                errors="coerce"
            ).round(2)

        # Dataset final de estadísticas de parejas.
        columnas_parejas = [
            "jugador_1",
            "jugador_2",
            "E",
            "G",
            "PJ",
            "WinRate",
            "P"
        ]

        estadisticas_parejas_nuevo = estadisticas_parejas[
            columnas_parejas
        ].copy()

        for columna in ["E", "G", "PJ", "P"]:
            estadisticas_parejas_nuevo[columna] = pd.to_numeric(
                estadisticas_parejas_nuevo[columna],
                errors="coerce"
            ).astype("Int64")

        estadisticas_parejas_nuevo["WinRate"] = pd.to_numeric(
            estadisticas_parejas_nuevo["WinRate"],
            errors="coerce"
        ).round(2)

        # Dataset final de estadísticas de rivales.
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

        estadisticas_rivales_nuevo = estadisticas_rivales[
            columnas_rivales
        ].copy()

        for columna in COLUMNAS_ENTERAS_RIVALES:
            estadisticas_rivales_nuevo[columna] = pd.to_numeric(
                estadisticas_rivales_nuevo[columna],
                errors="coerce"
            ).astype("Int64")

        for columna in ["winrate_jugador_1", "winrate_jugador_2"]:
            estadisticas_rivales_nuevo[columna] = pd.to_numeric(
                estadisticas_rivales_nuevo[columna],
                errors="coerce"
            ).round(2)

        jugadores_master_df = convertir_columnas_enteras(
            jugadores_master_df,
            COLUMNAS_ENTERAS_JUGADORES
        )
        estadisticas_parejas_actual_df = convertir_columnas_enteras(
            estadisticas_parejas_actual_df,
            COLUMNAS_ENTERAS_PAREJAS
        )
        equipos_master_actual_df = convertir_columnas_enteras(
            equipos_master_actual_df,
            COLUMNAS_ENTERAS_EQUIPOS
        )
        estadisticas_rivales_actual_df = convertir_columnas_enteras(
            estadisticas_rivales_actual_df,
            COLUMNAS_ENTERAS_RIVALES
        )

        backup_registros = dataframe_a_registros(jugadores_master_df)
        jugadores_master_registros = dataframe_a_registros(
            jugadores_master_nuevo
        )
        backup_parejas_registros = dataframe_a_registros(
            estadisticas_parejas_actual_df
        )
        estadisticas_parejas_registros = dataframe_a_registros(
            estadisticas_parejas_nuevo
        )
        backup_equipos_registros = dataframe_a_registros(
            equipos_master_actual_df
        )
        equipos_master_registros = dataframe_a_registros(
            equipos_master_nuevo
        )
        backup_rivales_registros = dataframe_a_registros(
            estadisticas_rivales_actual_df
        )
        estadisticas_rivales_registros = dataframe_a_registros(
            estadisticas_rivales_nuevo
        )

        st.session_state["backup_registros"] = backup_registros
        st.session_state[
            "jugadores_master_registros"
        ] = jugadores_master_registros
        st.session_state[
            "backup_parejas_registros"
        ] = backup_parejas_registros
        st.session_state[
            "estadisticas_parejas_registros"
        ] = estadisticas_parejas_registros
        st.session_state[
            "backup_equipos_registros"
        ] = backup_equipos_registros
        st.session_state[
            "equipos_master_registros"
        ] = equipos_master_registros
        st.session_state[
            "backup_rivales_registros"
        ] = backup_rivales_registros
        st.session_state[
            "estadisticas_rivales_registros"
        ] = estadisticas_rivales_registros
        st.session_state["chequeo_realizado"] = True
        st.session_state["backup_generado"] = False
        st.session_state["backup_parejas_generado"] = False
        st.session_state["backup_equipos_generado"] = False
        st.session_state["backup_rivales_generado"] = False

        st.write(
            f"Jugadores recalculados: {len(jugadores_master_nuevo)}"
        )
        st.write(
            f"Backup jugadores preparado: {len(backup_registros)} registros"
        )
        st.write(
            "Parejas recalculadas: "
            f"{len(estadisticas_parejas_registros)}"
        )
        st.write(
            "Backup parejas preparado: "
            f"{len(backup_parejas_registros)} registros"
        )
        st.write(
            f"Equipos recalculados: {len(equipos_master_registros)}"
        )
        st.write(
            "Backup equipos preparado: "
            f"{len(backup_equipos_registros)} registros"
        )
        st.write(
            "Rivales recalculados: "
            f"{len(estadisticas_rivales_registros)}"
        )
        st.write(
            "Backup rivales preparado: "
            f"{len(backup_rivales_registros)} registros"
        )

        # ==========================================
        # COMPARACION
        # ==========================================

        columnas_comparacion = [
            "jugador",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate"
        ]

        comparacion = jugadores_master_nuevo[
            columnas_comparacion
        ].merge(
            jugadores_master_df[columnas_comparacion],
            on="jugador",
            how="outer",
            suffixes=("_nuevo", "_actual")
        )

        comparacion["OK"] = (
            (comparacion["PJ_nuevo"] == comparacion["PJ_actual"])
            & (comparacion["G_nuevo"] == comparacion["G_actual"])
            & (comparacion["E_nuevo"] == comparacion["E_actual"])
            & (comparacion["P_nuevo"] == comparacion["P_actual"])
            & (
                comparacion["WinRate_nuevo"].round(2)
                == comparacion["WinRate_actual"].round(2)
            )
        )

        diferencias = comparacion[~comparacion["OK"]].copy()

        st.subheader("✅ Resultado")
        st.write(f"Parejas calculadas: {len(estadisticas_parejas)}")

        if diferencias.empty:
            st.success("✅ PJ / G / E / P / WinRate coinciden")
        else:
            st.warning(
                f"⚠️ Diferencias encontradas: {len(diferencias)}"
            )
            st.dataframe(diferencias, use_container_width=True)

        st.subheader("🤝 Mejor Compañero")
        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "mejor_companero",
                    "pj_mejor_companero",
                    "wr_mejor_companero"
                ]
            ]
            .sort_values("pj_mejor_companero", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("⚔️ Rival Más Frecuente")
        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "rival_mas_frecuente",
                    "pj_vs_rival_mas_frecuente"
                ]
            ]
            .sort_values(
                "pj_vs_rival_mas_frecuente",
                ascending=False
            )
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🏆 Mejor Racha Ganadora")
        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "mejor_racha_ganadora",
                    "racha_desde",
                    "racha_hasta"
                ]
            ]
            .sort_values("mejor_racha_ganadora", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("📉 Peor Racha Perdedora")
        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "peor_racha_perdedora",
                    "peor_racha_desde",
                    "peor_racha_hasta"
                ]
            ]
            .sort_values("peor_racha_perdedora", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🔥 Racha Activa")
        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "racha_activa",
                    "tipo_racha_activa"
                ]
            ]
            .sort_values(
                "racha_activa",
                ascending=False,
                na_position="last"
            )
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("👀 Vista previa jugadores")
        st.dataframe(
            jugadores_master_nuevo
            .sort_values("PJ", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🛡️ Vista previa equipos_master")
        st.dataframe(
            equipos_master_nuevo
            .sort_values("PJ", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("⚔️ Vista previa estadisticas_rivales")
        st.dataframe(
            estadisticas_rivales_nuevo
            .sort_values("pj", ascending=False)
            .head(30),
            use_container_width=True,
            hide_index=True
        )

        st.success(
            "✅ Chequeo terminado. Los datos quedaron listos para backup y actualización."
        )

    except Exception as error:
        st.session_state["chequeo_realizado"] = False
        st.exception(error)


# ==================================================
# BOTONES OPERACIONALES FUERA DEL BOTON DE CHEQUEO
# ==================================================

if st.session_state.get("chequeo_realizado", False):
    st.divider()
    st.subheader("⚙️ Acciones sobre Supabase")
    st.info(
        "Podés generar el backup y actualizar jugadores_master de forma independiente."
    )

    col_backup, col_actualizar = st.columns(2)

    with col_backup:
        if st.button(
            "💾 Generar Backup",
            key="btn_generar_backup",
            use_container_width=True
        ):
            try:
                backup_registros = st.session_state["backup_registros"]

                (
                    supabase
                    .table("jugadores_master_backup")
                    .delete()
                    .neq("jugador", "")
                    .execute()
                )

                insertar_en_lotes(
                    "jugadores_master_backup",
                    backup_registros
                )

                st.session_state["backup_generado"] = True

                st.success(
                    f"✅ Backup actualizado con {len(backup_registros)} registros."
                )

            except Exception as error:
                st.error("No se pudo generar el backup.")
                st.exception(error)

    with col_actualizar:
        if st.button(
            "🚀 Actualizar jugadores_master",
            key="btn_actualizar_jugadores_master",
            use_container_width=True
        ):
            try:
                registros = st.session_state[
                    "jugadores_master_registros"
                ]

                st.write(
                    f"Registros a actualizar: {len(registros)}"
                )

                upsert_en_lotes(
                    "jugadores_master",
                    registros,
                    "jugador"
                )

                st.success(
                    f"✅ jugadores_master actualizado con {len(registros)} registros."
                )

            except Exception as error:
                st.error("No se pudo actualizar jugadores_master.")
                st.exception(error)

    st.divider()
    st.subheader("🤝 Acciones sobre estadísticas de parejas")

    datos_parejas_listos = (
        st.session_state.get("backup_parejas_registros") is not None
        and st.session_state.get("estadisticas_parejas_registros") is not None
    )

    if not datos_parejas_listos:
        st.warning(
            "Los datos de parejas todavía no están preparados. "
            "Volvé a ejecutar el chequeo antes de usar estos botones."
        )

    st.info(
        "El backup de parejas y la actualización son acciones independientes."
    )

    col_backup_parejas, col_actualizar_parejas = st.columns(2)

    with col_backup_parejas:
        if st.button(
            "💾 Backup estadísticas de parejas",
            key="btn_backup_estadisticas_parejas",
            use_container_width=True,
            disabled=not datos_parejas_listos
        ):
            try:
                backup_parejas = st.session_state.get(
                    "backup_parejas_registros",
                    []
                )

                (
                    supabase
                    .table("estadisticas_parejas_backup")
                    .delete()
                    .neq("jugador_1", "")
                    .execute()
                )

                insertar_en_lotes(
                    "estadisticas_parejas_backup",
                    backup_parejas
                )

                st.session_state["backup_parejas_generado"] = True

                st.success(
                    "✅ Backup de parejas actualizado con "
                    f"{len(backup_parejas)} registros."
                )

            except Exception as error:
                st.error("No se pudo generar el backup de parejas.")
                st.exception(error)

    with col_actualizar_parejas:
        if st.button(
            "🚀 Actualizar estadísticas de parejas",
            key="btn_actualizar_estadisticas_parejas",
            use_container_width=True,
            disabled=not datos_parejas_listos
        ):
            try:
                registros_parejas = st.session_state.get(
                    "estadisticas_parejas_registros",
                    []
                )

                st.write(
                    "Parejas a actualizar: "
                    f"{len(registros_parejas)}"
                )

                upsert_en_lotes(
                    "estadisticas_parejas",
                    registros_parejas,
                    "jugador_1,jugador_2"
                )

                st.success(
                    "✅ estadisticas_parejas actualizada con "
                    f"{len(registros_parejas)} registros."
                )

            except Exception as error:
                st.error("No se pudo actualizar estadisticas_parejas.")
                st.exception(error)

    st.divider()
    st.subheader("🛡️ Acciones sobre equipos_master")

    datos_equipos_listos = (
        st.session_state.get("backup_equipos_registros") is not None
        and st.session_state.get("equipos_master_registros") is not None
    )

    if not datos_equipos_listos:
        st.warning(
            "Los datos de equipos todavía no están preparados. "
            "Volvé a ejecutar el chequeo antes de usar estos botones."
        )

    st.info(
        "El backup de equipos y la actualización son acciones independientes."
    )

    col_backup_equipos, col_actualizar_equipos = st.columns(2)

    with col_backup_equipos:
        if st.button(
            "💾 Backup equipos_master",
            key="btn_backup_equipos_master",
            use_container_width=True,
            disabled=not datos_equipos_listos
        ):
            try:
                backup_equipos = st.session_state.get(
                    "backup_equipos_registros",
                    []
                )

                (
                    supabase
                    .table("equipos_master_backup")
                    .delete()
                    .neq("equipo", "")
                    .execute()
                )

                insertar_en_lotes(
                    "equipos_master_backup",
                    backup_equipos
                )

                st.session_state["backup_equipos_generado"] = True

                st.success(
                    "✅ Backup de equipos actualizado con "
                    f"{len(backup_equipos)} registros."
                )

            except Exception as error:
                st.error("No se pudo generar el backup de equipos.")
                st.exception(error)

    with col_actualizar_equipos:
        if st.button(
            "🚀 Actualizar equipos_master",
            key="btn_actualizar_equipos_master",
            use_container_width=True,
            disabled=not datos_equipos_listos
        ):
            try:
                registros_equipos = st.session_state.get(
                    "equipos_master_registros",
                    []
                )

                st.write(
                    f"Equipos a actualizar: {len(registros_equipos)}"
                )

                upsert_en_lotes(
                    "equipos_master",
                    registros_equipos,
                    "equipo"
                )

                st.success(
                    "✅ equipos_master actualizado con "
                    f"{len(registros_equipos)} registros."
                )

            except Exception as error:
                st.error("No se pudo actualizar equipos_master.")
                st.exception(error)

    st.divider()
    st.subheader("⚔️ Acciones sobre estadísticas de rivales")

    datos_rivales_listos = (
        st.session_state.get("backup_rivales_registros") is not None
        and st.session_state.get("estadisticas_rivales_registros") is not None
    )

    if not datos_rivales_listos:
        st.warning(
            "Los datos de rivales todavía no están preparados. "
            "Volvé a ejecutar el chequeo antes de usar estos botones."
        )

    st.info(
        "El backup de rivales y la actualización son acciones independientes."
    )

    col_backup_rivales, col_actualizar_rivales = st.columns(2)

    with col_backup_rivales:
        if st.button(
            "💾 Backup estadísticas de rivales",
            key="btn_backup_estadisticas_rivales",
            use_container_width=True,
            disabled=not datos_rivales_listos
        ):
            try:
                backup_rivales = st.session_state.get(
                    "backup_rivales_registros",
                    []
                )

                (
                    supabase
                    .table("estadisticas_rivales_backup")
                    .delete()
                    .neq("jugador_1", "")
                    .execute()
                )

                insertar_en_lotes(
                    "estadisticas_rivales_backup",
                    backup_rivales
                )

                st.session_state["backup_rivales_generado"] = True

                st.success(
                    "✅ Backup de rivales actualizado con "
                    f"{len(backup_rivales)} registros."
                )

            except Exception as error:
                st.error("No se pudo generar el backup de rivales.")
                st.exception(error)

    with col_actualizar_rivales:
        if st.button(
            "🚀 Actualizar estadísticas de rivales",
            key="btn_actualizar_estadisticas_rivales",
            use_container_width=True,
            disabled=not datos_rivales_listos
        ):
            try:
                registros_rivales = st.session_state.get(
                    "estadisticas_rivales_registros",
                    []
                )

                st.write(
                    "Rivales a actualizar: "
                    f"{len(registros_rivales)}"
                )

                upsert_en_lotes(
                    "estadisticas_rivales",
                    registros_rivales,
                    "jugador_1,jugador_2"
                )

                st.success(
                    "✅ estadisticas_rivales actualizada con "
                    f"{len(registros_rivales)} registros."
                )

            except Exception as error:
                st.error("No se pudo actualizar estadisticas_rivales.")
                st.exception(error)

    st.divider()
    st.subheader("🌐 Acciones generales")
    st.info(
        "Estas acciones ejecutan el proceso sobre jugadores, parejas y equipos. "
        "Los backups siguen siendo opcionales."
    )

    datos_generales_listos = all(
        st.session_state.get(clave) is not None
        for clave in [
            "backup_registros",
            "jugadores_master_registros",
            "backup_parejas_registros",
            "estadisticas_parejas_registros",
            "backup_equipos_registros",
            "equipos_master_registros",
            "backup_rivales_registros",
            "estadisticas_rivales_registros"
        ]
    )

    col_backup_general, col_actualizar_general, col_verificar = st.columns(3)

    with col_backup_general:
        if st.button(
            "💾 Generar todos los backups",
            key="btn_generar_todos_backups",
            use_container_width=True,
            disabled=not datos_generales_listos
        ):
            try:
                with st.spinner("Generando todos los backups..."):
                    backup_jugadores = st.session_state.get(
                        "backup_registros",
                        []
                    )
                    backup_parejas = st.session_state.get(
                        "backup_parejas_registros",
                        []
                    )
                    backup_equipos = st.session_state.get(
                        "backup_equipos_registros",
                        []
                    )
                    backup_rivales = st.session_state.get(
                        "backup_rivales_registros",
                        []
                    )

                    (
                        supabase
                        .table("jugadores_master_backup")
                        .delete()
                        .neq("jugador", "")
                        .execute()
                    )
                    insertar_en_lotes(
                        "jugadores_master_backup",
                        backup_jugadores
                    )

                    (
                        supabase
                        .table("estadisticas_parejas_backup")
                        .delete()
                        .neq("jugador_1", "")
                        .execute()
                    )
                    insertar_en_lotes(
                        "estadisticas_parejas_backup",
                        backup_parejas
                    )

                    (
                        supabase
                        .table("equipos_master_backup")
                        .delete()
                        .neq("equipo", "")
                        .execute()
                    )
                    insertar_en_lotes(
                        "equipos_master_backup",
                        backup_equipos
                    )

                    (
                        supabase
                        .table("estadisticas_rivales_backup")
                        .delete()
                        .neq("jugador_1", "")
                        .execute()
                    )
                    insertar_en_lotes(
                        "estadisticas_rivales_backup",
                        backup_rivales
                    )

                    st.session_state["backup_generado"] = True
                    st.session_state["backup_parejas_generado"] = True
                    st.session_state["backup_equipos_generado"] = True
                    st.session_state["backup_rivales_generado"] = True

                st.success(
                    "✅ Todos los backups fueron actualizados. "
                    f"Jugadores: {len(backup_jugadores)}. "
                    f"Parejas: {len(backup_parejas)}. "
                    f"Equipos: {len(backup_equipos)}. "
                    f"Rivales: {len(backup_rivales)}."
                )

            except Exception as error:
                st.error("No se pudieron generar todos los backups.")
                st.exception(error)

    with col_actualizar_general:
        if st.button(
            "🚀 Actualizar todas las estadísticas",
            key="btn_actualizar_todas_estadisticas",
            use_container_width=True,
            disabled=not datos_generales_listos
        ):
            try:
                with st.spinner("Actualizando todas las tablas..."):
                    registros_jugadores = st.session_state.get(
                        "jugadores_master_registros",
                        []
                    )
                    registros_parejas = st.session_state.get(
                        "estadisticas_parejas_registros",
                        []
                    )
                    registros_equipos = st.session_state.get(
                        "equipos_master_registros",
                        []
                    )
                    registros_rivales = st.session_state.get(
                        "estadisticas_rivales_registros",
                        []
                    )

                    upsert_en_lotes(
                        "jugadores_master",
                        registros_jugadores,
                        "jugador"
                    )
                    upsert_en_lotes(
                        "estadisticas_parejas",
                        registros_parejas,
                        "jugador_1,jugador_2"
                    )
                    upsert_en_lotes(
                        "equipos_master",
                        registros_equipos,
                        "equipo"
                    )
                    upsert_en_lotes(
                        "estadisticas_rivales",
                        registros_rivales,
                        "jugador_1,jugador_2"
                    )

                st.success(
                    "✅ Todas las estadísticas fueron actualizadas. "
                    f"Jugadores: {len(registros_jugadores)}. "
                    f"Parejas: {len(registros_parejas)}. "
                    f"Equipos: {len(registros_equipos)}. "
                    f"Rivales: {len(registros_rivales)}."
                )

            except Exception as error:
                st.error("No se pudieron actualizar todas las estadísticas.")
                st.exception(error)

    with col_verificar:
        if st.button(
            "🔍 Verificar actualización",
            key="btn_verificar_actualizacion",
            use_container_width=True
        ):
            try:
                with st.spinner("Verificando tablas en Supabase..."):
                    jugadores_verificacion = leer_tabla_completa(
                        "jugadores_master"
                    )
                    parejas_verificacion = leer_tabla_completa(
                        "estadisticas_parejas"
                    )
                    equipos_verificacion = leer_tabla_completa(
                        "equipos_master"
                    )
                    rivales_verificacion = leer_tabla_completa(
                        "estadisticas_rivales"
                    )
                    partidos_verificacion = leer_tabla_completa(
                        "partidos"
                    )
                    participaciones_verificacion = leer_tabla_completa(
                        "participaciones"
                    )

                errores_verificacion = []

                if not jugadores_verificacion.empty:
                    for columna in ["PJ", "G", "E", "P"]:
                        jugadores_verificacion[columna] = pd.to_numeric(
                            jugadores_verificacion[columna],
                            errors="coerce"
                        )

                    jugadores_invalidos = jugadores_verificacion[
                        jugadores_verificacion["PJ"]
                        != (
                            jugadores_verificacion["G"]
                            + jugadores_verificacion["E"]
                            + jugadores_verificacion["P"]
                        )
                    ]

                    if not jugadores_invalidos.empty:
                        errores_verificacion.append(
                            "Hay jugadores donde PJ no coincide con G + E + P."
                        )

                    if jugadores_verificacion["jugador"].duplicated().any():
                        errores_verificacion.append(
                            "Hay jugadores duplicados en jugadores_master."
                        )

                if not parejas_verificacion.empty:
                    for columna in ["PJ", "G", "E", "P"]:
                        parejas_verificacion[columna] = pd.to_numeric(
                            parejas_verificacion[columna],
                            errors="coerce"
                        )

                    parejas_invalidas = parejas_verificacion[
                        parejas_verificacion["PJ"]
                        != (
                            parejas_verificacion["G"]
                            + parejas_verificacion["E"]
                            + parejas_verificacion["P"]
                        )
                    ]

                    if not parejas_invalidas.empty:
                        errores_verificacion.append(
                            "Hay parejas donde PJ no coincide con G + E + P."
                        )

                    if parejas_verificacion.duplicated(
                        subset=["jugador_1", "jugador_2"]
                    ).any():
                        errores_verificacion.append(
                            "Hay parejas duplicadas en estadisticas_parejas."
                        )

                if not equipos_verificacion.empty:
                    for columna in ["PJ", "G", "E", "P"]:
                        equipos_verificacion[columna] = pd.to_numeric(
                            equipos_verificacion[columna],
                            errors="coerce"
                        )

                    equipos_invalidos = equipos_verificacion[
                        equipos_verificacion["PJ"]
                        != (
                            equipos_verificacion["G"]
                            + equipos_verificacion["E"]
                            + equipos_verificacion["P"]
                        )
                    ]

                    if not equipos_invalidos.empty:
                        errores_verificacion.append(
                            "Hay equipos donde PJ no coincide con G + E + P."
                        )

                    if equipos_verificacion["equipo"].duplicated().any():
                        errores_verificacion.append(
                            "Hay equipos duplicados en equipos_master."
                        )

                if not rivales_verificacion.empty:
                    for columna in ["pj", "g_jugador_1", "g_jugador_2", "E"]:
                        rivales_verificacion[columna] = pd.to_numeric(
                            rivales_verificacion[columna],
                            errors="coerce"
                        )

                    rivales_invalidos = rivales_verificacion[
                        rivales_verificacion["pj"]
                        != (
                            rivales_verificacion["g_jugador_1"]
                            + rivales_verificacion["g_jugador_2"]
                            + rivales_verificacion["E"]
                        )
                    ]

                    if not rivales_invalidos.empty:
                        errores_verificacion.append(
                            "Hay rivales donde PJ no coincide con G_jugador_1 + G_jugador_2 + E."
                        )

                    if rivales_verificacion.duplicated(
                        subset=["jugador_1", "jugador_2"]
                    ).any():
                        errores_verificacion.append(
                            "Hay rivales duplicados en estadisticas_rivales."
                        )

                ultimo_partido_texto = "Sin fecha"

                if (
                    not partidos_verificacion.empty
                    and "fecha" in partidos_verificacion.columns
                ):
                    fechas_verificacion = pd.to_datetime(
                        partidos_verificacion["fecha"],
                        errors="coerce"
                    )
                    ultima_fecha = fechas_verificacion.max()

                    if pd.notnull(ultima_fecha):
                        ultimo_partido_texto = ultima_fecha.strftime(
                            "%d/%m/%Y"
                        )

                resumen_verificacion = pd.DataFrame(
                    {
                        "Tabla": [
                            "partidos",
                            "participaciones",
                            "jugadores_master",
                            "estadisticas_parejas",
                            "equipos_master",
                            "estadisticas_rivales"
                        ],
                        "Registros en Supabase": [
                            len(partidos_verificacion),
                            len(participaciones_verificacion),
                            len(jugadores_verificacion),
                            len(parejas_verificacion),
                            len(equipos_verificacion),
                            len(rivales_verificacion)
                        ],
                        "Registros calculados": [
                            None,
                            None,
                            len(st.session_state.get(
                                "jugadores_master_registros"
                            ) or []),
                            len(st.session_state.get(
                                "estadisticas_parejas_registros"
                            ) or []),
                            len(st.session_state.get(
                                "equipos_master_registros"
                            ) or []),
                            len(st.session_state.get(
                                "estadisticas_rivales_registros"
                            ) or [])
                        ]
                    }
                )

                st.dataframe(
                    resumen_verificacion,
                    use_container_width=True,
                    hide_index=True
                )

                st.write(
                    f"Último partido detectado: {ultimo_partido_texto}"
                )

                if errores_verificacion:
                    st.error("Se detectaron inconsistencias:")
                    for mensaje in errores_verificacion:
                        st.write(f"• {mensaje}")
                else:
                    st.success(
                        "✅ Verificación completada sin inconsistencias."
                    )

            except Exception as error:
                st.error("No se pudo verificar la actualización.")
                st.exception(error)
