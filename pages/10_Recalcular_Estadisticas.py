import streamlit as st
import pandas as pd

from datetime import date, datetime
from itertools import combinations
from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION Y LOGIN
# ==================================================

st.title("🔄 Recalcular Estadísticas")

usuario = st.text_input("Usuario")

password = st.text_input(
    "Contraseña",
    type="password"
)

if (
    usuario != st.secrets["ADMIN_USER"]
    or password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning("Acceso restringido")
    st.stop()

st.success("✅ Acceso autorizado")

supabase = get_supabase()


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
            .range(
                desde,
                desde + lote - 1
            )
            .execute()
        )

        if not respuesta.data:
            break

        registros.extend(
            respuesta.data
        )

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(
        registros
    )


def valor_json(valor):

    if valor is None:
        return None

    try:

        if pd.isna(valor):
            return None

    except (TypeError, ValueError):

        pass

    if isinstance(
        valor,
        (
            pd.Timestamp,
            datetime,
            date
        )
    ):

        return valor.isoformat()

    if hasattr(valor, "item"):

        try:

            return valor.item()

        except (
            ValueError,
            AttributeError
        ):

            pass

    return valor


def dataframe_a_registros(df):

    registros = []

    for fila in df.to_dict("records"):

        registro = {
            columna: valor_json(valor)
            for columna, valor in fila.items()
        }

        registros.append(
            registro
        )

    return registros


def insertar_en_lotes(
    tabla,
    registros,
    lote=500
):

    for inicio in range(
        0,
        len(registros),
        lote
    ):

        bloque = registros[
            inicio:inicio + lote
        ]

        (
            supabase
            .table(tabla)
            .insert(bloque)
            .execute()
        )


def upsert_en_lotes(
    tabla,
    registros,
    conflicto,
    lote=500
):

    for inicio in range(
        0,
        len(registros),
        lote
    ):

        bloque = registros[
            inicio:inicio + lote
        ]

        (
            supabase
            .table(tabla)
            .upsert(
                bloque,
                on_conflict=conflicto
            )
            .execute()
        )


# ==================================================
# CHEQUEO Y RECALCULO
# ==================================================

if st.button(
    "🔄 Ejecutar Chequeo",
    key="btn_ejecutar_chequeo"
):

    try:

        # ==========================================
        # LECTURA
        # ==========================================

        partidos_df = leer_tabla_completa(
            "partidos"
        )

        participaciones_df = leer_tabla_completa(
            "participaciones"
        )

        jugadores_master_df = leer_tabla_completa(
            "jugadores_master"
        )

        if partidos_df.empty:

            raise ValueError(
                "La tabla partidos está vacía."
            )

        if participaciones_df.empty:

            raise ValueError(
                "La tabla participaciones está vacía."
            )

        st.subheader(
            "📊 Datos leídos"
        )

        st.write(
            f"Partidos: {len(partidos_df)}"
        )

        st.write(
            f"Participaciones: {len(participaciones_df)}"
        )

        st.write(
            f"Jugadores Master: {len(jugadores_master_df)}"
        )

        # ==========================================
        # PREPARACION DE PARTIDOS
        # ==========================================

        partidos_df[
            "goles_local"
        ] = pd.to_numeric(
            partidos_df["goles_local"],
            errors="coerce"
        )

        partidos_df[
            "goles_visitante"
        ] = pd.to_numeric(
            partidos_df["goles_visitante"],
            errors="coerce"
        )

        partidos_df[
            "fecha"
        ] = pd.to_datetime(
            partidos_df["fecha"],
            errors="coerce"
        )

        # ==========================================
        # RESULTADO LOCAL
        # ==========================================

        partidos_df[
            "resultado_local"
        ] = "E"

        partidos_df.loc[
            partidos_df["goles_local"]
            >
            partidos_df["goles_visitante"],
            "resultado_local"
        ] = "G"

        partidos_df.loc[
            partidos_df["goles_local"]
            <
            partidos_df["goles_visitante"],
            "resultado_local"
        ] = "P"

        # ==========================================
        # MERGE PARTICIPACIONES Y PARTIDOS
        # ==========================================

        participaciones_df = (
            participaciones_df
            .merge(
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
                suffixes=(
                    "",
                    "_partido"
                )
            )
        )

        # ==========================================
        # RESULTADO POR JUGADOR
        # ==========================================

        participaciones_df[
            "resultado_jugador"
        ] = ""

        mask_local = (
            participaciones_df["equipo"]
            ==
            participaciones_df["equipo_local"]
        )

        mask_visitante = (
            participaciones_df["equipo"]
            ==
            participaciones_df["equipo_visitante"]
        )

        participaciones_df.loc[
            mask_local,
            "resultado_jugador"
        ] = participaciones_df[
            "resultado_local"
        ]

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ] == "G"
            ),
            "resultado_jugador"
        ] = "P"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ] == "P"
            ),
            "resultado_jugador"
        ] = "G"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df[
                    "resultado_local"
                ] == "E"
            ),
            "resultado_jugador"
        ] = "E"

        sin_resultado = (
            participaciones_df[
                ~participaciones_df[
                    "resultado_jugador"
                ].isin(
                    [
                        "G",
                        "E",
                        "P"
                    ]
                )
            ]
        )

        if not sin_resultado.empty:

            st.warning(
                f"Hay {len(sin_resultado)} participaciones "
                "sin resultado válido. No se incluirán "
                "en PJ, G, E y P."
            )

        participaciones_validas = (
            participaciones_df[
                participaciones_df[
                    "resultado_jugador"
                ].isin(
                    [
                        "G",
                        "E",
                        "P"
                    ]
                )
            ]
            .copy()
        )

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

        for columna in [
            "G",
            "E",
            "P"
        ]:

            if (
                columna
                not in estadisticas_jugador.columns
            ):

                estadisticas_jugador[
                    columna
                ] = 0

        estadisticas_jugador[
            "PJ"
        ] = (
            estadisticas_jugador["G"]
            +
            estadisticas_jugador["E"]
            +
            estadisticas_jugador["P"]
        )

        estadisticas_jugador[
            "WinRate"
        ] = (
            estadisticas_jugador["G"]
            /
            estadisticas_jugador[
                "PJ"
            ].replace(
                0,
                pd.NA
            )
            * 100
        ).round(2).fillna(0)

        # ==========================================
        # EQUIPO FAVORITO
        # ==========================================

        partidos_por_equipo = (
            participaciones_validas
            .groupby(
                [
                    "jugador",
                    "equipo"
                ]
            )
            .size()
            .reset_index(
                name="partidos"
            )
            .sort_values(
                [
                    "jugador",
                    "partidos",
                    "equipo"
                ],
                ascending=[
                    True,
                    False,
                    True
                ]
            )
        )

        equipo_favorito = (
            partidos_por_equipo
            .groupby(
                "jugador",
                as_index=False
            )
            .first()
            .rename(
                columns={
                    "equipo":
                        "equipo_favorito",
                    "partidos":
                        "partidos_equipo_favorito"
                }
            )
        )

        estadisticas_jugador = (
            estadisticas_jugador
            .merge(
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
        )

        # ==========================================
        # ESTADISTICAS DE PAREJAS
        # ==========================================

        parejas_resultado = []

        for (
            partido_id,
            grupo
        ) in participaciones_validas.groupby(
            "partido_id"
        ):

            for (
                equipo,
                jugadores_equipo
            ) in grupo.groupby(
                "equipo"
            ):

                lista_jugadores = sorted(
                    jugadores_equipo[
                        "jugador"
                    ]
                    .dropna()
                    .unique()
                )

                if len(lista_jugadores) < 2:
                    continue

                resultado = (
                    jugadores_equipo[
                        "resultado_jugador"
                    ]
                    .iloc[0]
                )

                for (
                    jugador_1,
                    jugador_2
                ) in combinations(
                    lista_jugadores,
                    2
                ):

                    parejas_resultado.append(
                        {
                            "jugador_1":
                                jugador_1,
                            "jugador_2":
                                jugador_2,
                            "resultado":
                                resultado
                        }
                    )

        if not parejas_resultado:

            raise ValueError(
                "No se pudieron calcular "
                "estadísticas de parejas."
            )

        parejas_df = pd.DataFrame(
            parejas_resultado
        )

        estadisticas_parejas = (
            parejas_df
            .pivot_table(
                index=[
                    "jugador_1",
                    "jugador_2"
                ],
                columns="resultado",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        estadisticas_parejas.columns.name = None

        for columna in [
            "G",
            "E",
            "P"
        ]:

            if (
                columna
                not in estadisticas_parejas.columns
            ):

                estadisticas_parejas[
                    columna
                ] = 0

        estadisticas_parejas[
            "PJ"
        ] = (
            estadisticas_parejas["G"]
            +
            estadisticas_parejas["E"]
            +
            estadisticas_parejas["P"]
        )

        estadisticas_parejas[
            "WinRate"
        ] = (
            estadisticas_parejas["G"]
            /
            estadisticas_parejas[
                "PJ"
            ].replace(
                0,
                pd.NA
            )
            * 100
        ).round(2).fillna(0)

        # ==========================================
        # MEJOR COMPAÑERO
        # ==========================================

        parejas_bidireccional = pd.concat(
            [
                estadisticas_parejas.rename(
                    columns={
                        "jugador_1":
                            "jugador",
                        "jugador_2":
                            "companero"
                    }
                ),
                estadisticas_parejas.rename(
                    columns={
                        "jugador_2":
                            "jugador",
                        "jugador_1":
                            "companero"
                    }
                )
            ],
            ignore_index=True
        )

        mejor_companero = (
            parejas_bidireccional
            .sort_values(
                [
                    "jugador",
                    "PJ",
                    "companero"
                ],
                ascending=[
                    True,
                    False,
                    True
                ]
            )
            .groupby(
                "jugador",
                as_index=False
            )
            .first()
        )

        estadisticas_jugador = (
            estadisticas_jugador
            .merge(
                mejor_companero[
                    [
                        "jugador",
                        "companero",
                        "PJ",
                        "WinRate"
                    ]
                ]
                .rename(
                    columns={
                        "companero":
                            "mejor_companero",
                        "PJ":
                            "pj_mejor_companero",
                        "WinRate":
                            "wr_mejor_companero"
                    }
                ),
                on="jugador",
                how="left"
            )
        )

        # ==========================================
        # RIVAL MAS FRECUENTE
        # ==========================================

        enfrentamientos = []

        for (
            partido_id,
            grupo
        ) in participaciones_validas.groupby(
            "partido_id"
        ):

            equipos = (
                grupo["equipo"]
                .dropna()
                .unique()
            )

            if len(equipos) != 2:
                continue

            jugadores_1 = (
                grupo[
                    grupo["equipo"]
                    == equipos[0]
                ]["jugador"]
                .dropna()
                .unique()
            )

            jugadores_2 = (
                grupo[
                    grupo["equipo"]
                    == equipos[1]
                ]["jugador"]
                .dropna()
                .unique()
            )

            for jugador_1 in jugadores_1:

                for jugador_2 in jugadores_2:

                    enfrentamientos.append(
                        {
                            "jugador":
                                jugador_1,
                            "rival":
                                jugador_2
                        }
                    )

                    enfrentamientos.append(
                        {
                            "jugador":
                                jugador_2,
                            "rival":
                                jugador_1
                        }
                    )

        if not enfrentamientos:

            raise ValueError(
                "No se pudieron calcular "
                "rivales frecuentes."
            )

        enfrentamientos_df = pd.DataFrame(
            enfrentamientos
        )

        rival_principal = (
            enfrentamientos_df
            .groupby(
                [
                    "jugador",
                    "rival"
                ]
            )
            .size()
            .reset_index(
                name="partidos"
            )
            .sort_values(
                [
                    "jugador",
                    "partidos",
                    "rival"
                ],
                ascending=[
                    True,
                    False,
                    True
                ]
            )
            .groupby(
                "jugador",
                as_index=False
            )
            .first()
            .rename(
                columns={
                    "rival":
                        "rival_mas_frecuente",
                    "partidos":
                        "pj_vs_rival_mas_frecuente"
                }
            )
        )

        estadisticas_jugador = (
            estadisticas_jugador
            .merge(
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
        )

        # ==========================================
        # PARTIDOS ORDENADOS
        # ==========================================

        partidos_ordenados = (
            participaciones_validas[
                [
                    "jugador",
                    "partido_id",
                    "resultado_jugador"
                ]
            ]
            .merge(
                partidos_df[
                    [
                        "id",
                        "fecha"
                    ]
                ],
                left_on="partido_id",
                right_on="id",
                how="left"
            )
            .dropna(
                subset=[
                    "fecha"
                ]
            )
            .sort_values(
                [
                    "jugador",
                    "fecha",
                    "partido_id"
                ]
            )
        )

        # ==========================================
        # MEJOR RACHA GANADORA
        # ==========================================

        mejores_rachas = []

        for (
            jugador,
            grupo
        ) in partidos_ordenados.groupby(
            "jugador"
        ):

            mejor_racha = 0
            mejor_desde = None
            mejor_hasta = None

            racha_actual = 0
            fecha_inicio_actual = None

            for _, fila in grupo.iterrows():

                resultado = fila[
                    "resultado_jugador"
                ]

                fecha = fila[
                    "fecha"
                ]

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

            mejores_rachas.append(
                {
                    "jugador":
                        jugador,
                    "mejor_racha_ganadora":
                        mejor_racha,
                    "racha_desde":
                        (
                            mejor_desde.date()
                            if pd.notnull(
                                mejor_desde
                            )
                            else None
                        ),
                    "racha_hasta":
                        (
            
     
      
