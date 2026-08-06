import streamlit as st
import pandas as pd
from itertools import combinations

from supabase_utils import get_supabase

# ==================================================
# LOGIN
# ==================================================

st.title("🔄 Recalcular Estadísticas")

usuario = st.text_input("Usuario")

password = st.text_input(
    "Contraseña",
    type="password"
)

if (
    usuario != st.secrets["ADMIN_USER"]
    or
    password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning("Acceso restringido")
    st.stop()

st.success("✅ Acceso autorizado")

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

        registros.extend(
            respuesta.data
        )

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(registros)

# ==================================================
# BOTON
# ==================================================

if st.button("🔄 Ejecutar Chequeo"):

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

        # ==========================================
        # INFO
        # ==========================================

        st.subheader("📊 Datos leídos")

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
        # RESULTADO LOCAL
        # ==========================================

        partidos_df["resultado_local"] = "E"

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
        # MERGE
        # ==========================================

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
            suffixes=(
                "",
                "_partido"
            )
        )

        # ==========================================
        # RESULTADO JUGADOR
        # ==========================================

        participaciones_df[
            "resultado_jugador"
        ] = ""

        mask_local = (
            participaciones_df["equipo"]
            ==
            participaciones_df["equipo_local"]
        )

        participaciones_df.loc[
            mask_local,
            "resultado_jugador"
        ] = participaciones_df[
            "resultado_local"
        ]

        mask_visitante = (
            participaciones_df["equipo"]
            ==
            participaciones_df["equipo_visitante"]
        )

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "G"
            ),
            "resultado_jugador"
        ] = "P"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "P"
            ),
            "resultado_jugador"
        ] = "G"

        participaciones_df.loc[
            mask_visitante
            &
            (
                participaciones_df["resultado_local"]
                == "E"
            ),
            "resultado_jugador"
        ] = "E"

        # ==========================================
        # ESTADISTICAS BASICAS
        # ==========================================

        estadisticas_jugador = (
            participaciones_df
            .pivot_table(
                index="jugador",
                columns="resultado_jugador",
                aggfunc="size",
                fill_value=0
            )
            .reset_index()
        )

        for col in ["G", "E", "P"]:

            if col not in estadisticas_jugador.columns:
                estadisticas_jugador[col] = 0

        estadisticas_jugador["PJ"] = (
            estadisticas_jugador["G"]
            +
            estadisticas_jugador["E"]
            +
            estadisticas_jugador["P"]
        )

        estadisticas_jugador["WinRate"] = (
            estadisticas_jugador["G"]
            /
            estadisticas_jugador["PJ"]
            * 100
        ).round(2)

        # ==========================================
        # EQUIPO FAVORITO
        # ==========================================

        partidos_por_equipo = (
            participaciones_df
            .groupby(
                ["jugador", "equipo"]
            )
            .size()
            .reset_index(name="partidos")
        )

        partidos_por_equipo = (
            partidos_por_equipo
            .sort_values(
                ["jugador", "partidos"],
                ascending=[True, False]
            )
        )

        equipo_favorito = (
            partidos_por_equipo
            .groupby("jugador")
            .first()
            .reset_index()
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
        # ESTADISTICAS PAREJAS
        # ==========================================

        parejas_resultado = []

        for partido_id, grupo in participaciones_df.groupby("partido_id"):

            for equipo, jugadores_equipo in grupo.groupby("equipo"):

                lista_jugadores = sorted(
                    jugadores_equipo["jugador"].unique()
                )

                resultado = (
                    jugadores_equipo[
                        "resultado_jugador"
                    ]
                    .iloc[0]
                )

                for j1, j2 in combinations(
                    lista_jugadores,
                    2
                ):

                    parejas_resultado.append(
                        {
                            "jugador_1": j1,
                            "jugador_2": j2,
                            "resultado": resultado
                        }
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

        for col in ["G", "E", "P"]:

            if col not in estadisticas_parejas.columns:
                estadisticas_parejas[col] = 0

        estadisticas_parejas["PJ"] = (
            estadisticas_parejas["G"]
            +
            estadisticas_parejas["E"]
            +
            estadisticas_parejas["P"]
        )

        estadisticas_parejas["WinRate"] = (
            estadisticas_parejas["G"]
            /
            estadisticas_parejas["PJ"]
            * 100
        ).round(2)

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
            ]
        )

        mejor_companero = (
            parejas_bidireccional
            .sort_values(
                "PJ",
                ascending=False
            )
            .groupby("jugador")
            .first()
            .reset_index()
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
                ].rename(
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
        # RIVALES
        # ==========================================

        enfrentamientos = []

        for partido_id, grupo in participaciones_df.groupby("partido_id"):

            equipos = grupo["equipo"].unique()

            if len(equipos) != 2:
                continue

            equipo_1 = equipos[0]
            equipo_2 = equipos[1]

            jugadores_1 = grupo[
                grupo["equipo"] == equipo_1
            ]

            jugadores_2 = grupo[
                grupo["equipo"] == equipo_2
            ]

            for _, j1 in jugadores_1.iterrows():

                for _, j2 in jugadores_2.iterrows():

                    enfrentamientos.append({
                        "jugador": j1["jugador"],
                        "rival": j2["jugador"],
                        "resultado": j1["resultado_jugador"]
                    })

                    enfrentamientos.append({
                        "jugador": j2["jugador"],
                        "rival": j1["jugador"],
                        "resultado": j2["resultado_jugador"]
                    })

        enfrentamientos_df = pd.DataFrame(
            enfrentamientos
        )

        rivales_frecuentes = (
            enfrentamientos_df
            .groupby(
                ["jugador", "rival"]
            )
            .size()
            .reset_index(name="partidos")
        )

        rival_principal = (
            rivales_frecuentes
            .sort_values(
                "partidos",
                ascending=False
            )
            .groupby("jugador")
            .first()
            .reset_index()
        )

        rival_principal = rival_principal.rename(
            columns={
                "rival": "rival_mas_frecuente",
                "partidos": "pj_vs_rival_mas_frecuente"
            }
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
        # MEJOR RACHA GANADORA
        # ==========================================

        partidos_df["fecha"] = pd.to_datetime(
            partidos_df["fecha"],
            errors="coerce"
        )

        partidos_ordenados = (
            participaciones_df[
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
        )

        partidos_ordenados["fecha"] = pd.to_datetime(
            partidos_ordenados["fecha"],
            errors="coerce"
        )

        partidos_ordenados = (
            partidos_ordenados
            .sort_values(
                [
                    "jugador",
                    "fecha"
                ]
            )
        )

        mejores_rachas = []

        for jugador, grupo in partidos_ordenados.groupby(
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
        "jugador": jugador,
        "mejor_racha_ganadora":
            mejor_racha,
        "racha_desde":
            (
                mejor_desde.date()
                if pd.notnull(mejor_desde)
                else None
            ),
        "racha_hasta":
            (
                mejor_hasta.date()
                if pd.notnull(mejor_hasta)
                else None
            )
    }
)
            

        mejores_rachas_df = pd.DataFrame(
            mejores_rachas
        )

        estadisticas_jugador = (
            estadisticas_jugador
            .merge(
                mejores_rachas_df,
                on="jugador",
                how="left"
            )
        )
        
                # ==========================================
        # RACHA ACTIVA
        # ==========================================

        partidos_df["fecha"] = pd.to_datetime(
            partidos_df["fecha"],
            errors="coerce"
        )

        fecha_maxima = partidos_df["fecha"].max()

        fecha_corte = (
            fecha_maxima -
            pd.Timedelta(days=365)
        )

        jugadores_activos = (
            partidos_ordenados[
                partidos_ordenados["fecha"]
                >=
                fecha_corte
            ]["jugador"]
            .unique()
        )

        jugadores_activos = set(
            jugadores_activos
        )

        rachas_activas = []

        for jugador, grupo in partidos_ordenados.groupby(
            "jugador"
        ):

            if jugador not in jugadores_activos:

                rachas_activas.append(
                    {
                        "jugador": jugador,
                        "racha_activa": None,
                        "tipo_racha_activa": "Inactivo"
                    }
                )

                continue

            grupo = grupo.sort_values(
                "fecha"
            )

            resultados = list(
                grupo["resultado_jugador"]
            )

            ultimo_resultado = resultados[-1]

            contador = 0

            for resultado in reversed(
                resultados
            ):

                if resultado == ultimo_resultado:

                    contador += 1

                else:

                    break

            rachas_activas.append(
                {
                    "jugador": jugador,
                    "racha_activa": contador,
                    "tipo_racha_activa":
                        ultimo_resultado
                }
            )

        rachas_activas_df = pd.DataFrame(
            rachas_activas
        )

        estadisticas_jugador = (
            estadisticas_jugador
            .merge(
                rachas_activas_df,
                on="jugador",
                how="left"
            )
        )

         # ==========================================
        # DATASET FINAL JUGADORES_MASTER
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
            "racha_activa",
            "tipo_racha_activa"
        ]

        jugadores_master_nuevo = (
            estadisticas_jugador[
                columnas_finales
            ]
            .copy()
        )

        st.write(
            f"Jugadores recalculados: {len(jugadores_master_nuevo)}"
        )

        backup_actual = leer_tabla_completa(
            "jugadores_master"
        )

        backup_actual = (
            backup_actual
            .astype(object)
        )

        backup_actual = backup_actual.where(
            pd.notnull(backup_actual),
            None
        )

        backup_registros = (
            backup_actual
            .to_dict("records")
        )

        st.write(
            f"Backup preparado: {len(backup_registros)} registros"
        )

        supabase.table(
            "jugadores_master_backup"
        ).delete().neq(
            "jugador",
            ""
        ).execute()

        for i in range(
            0,
            len(backup_registros),
            500
        ):

            lote = backup_registros[
                i:i + 500
            ]

            supabase.table(
                "jugadores_master_backup"
            ).insert(
                lote
            ).execute()

        st.success(
            "✅ Backup actualizado"
        )
        # ==========================================
        # COMPARACION
        # ==========================================

        columnas = [
            "jugador",
            "PJ",
            "G",
            "E",
            "P",
            "WinRate"
        ]

        comparacion = (
            estadisticas_jugador[columnas]
            .merge(
                jugadores_master_df[columnas],
                on="jugador",
                how="outer",
                suffixes=(
                    "_nuevo",
                    "_actual"
                )
            )
        )

        comparacion["OK"] = (
            (comparacion["PJ_nuevo"] == comparacion["PJ_actual"])
            &
            (comparacion["G_nuevo"] == comparacion["G_actual"])
            &
            (comparacion["E_nuevo"] == comparacion["E_actual"])
            &
            (comparacion["P_nuevo"] == comparacion["P_actual"])
            &
            (
                comparacion["WinRate_nuevo"].round(2)
                ==
                comparacion["WinRate_actual"].round(2)
            )
        )

        diferencias = comparacion[
            comparacion["OK"] == False
        ]

                # ==========================================
        # DATASET FINAL JUGADORES MASTER
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
            "racha_activa",
            "tipo_racha_activa"
        ]

        jugadores_master_nuevo = (
            estadisticas_jugador[
                columnas_finales
            ]
            .copy()
        )

        st.subheader(
            "✅ jugadores_master_nuevo"
        )

        st.dataframe(
            jugadores_master_nuevo.head(20)
        )

              # ==========================================
        # RESULTADO
        # ==========================================

        st.subheader("✅ Resultado")

        st.write(
            f"Parejas calculadas: {len(estadisticas_parejas)}"
        )

        if len(diferencias) == 0:

            st.success(
                "✅ PJ / G / E / P / WinRate coinciden"
            )

        else:

            st.warning(
                f"⚠️ Diferencias encontradas: {len(diferencias)}"
            )

            st.dataframe(
                diferencias
            )

        # ==========================================
        # MEJOR COMPAÑERO
        # ==========================================

        st.subheader(
            "🤝 Mejor Compañero"
        )

        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "mejor_companero",
                    "pj_mejor_companero",
                    "wr_mejor_companero"
                ]
            ]
            .sort_values(
                "pj_mejor_companero",
                ascending=False
            )
            .head(30)
        )

        # ==========================================
        # RIVAL MAS FRECUENTE
        # ==========================================

        st.subheader(
            "⚔️ Rival Más Frecuente"
        )

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
            .head(30)
        )

        st.subheader(
            "🏆 Mejor Racha Ganadora"
        )

        st.dataframe(
            estadisticas_jugador[
                [
                    "jugador",
                    "mejor_racha_ganadora",
                    "racha_desde",
                    "racha_hasta"
                ]
            ]
            .sort_values(
                "mejor_racha_ganadora",
                ascending=False
            )
            .head(30)
        )
        
        st.subheader(
            "🔥 Racha Activa"
        )

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
            .head(30)
        )

        
        # ==========================================
        # PREVIEW
        # ==========================================

        st.subheader(
            "👀 Vista previa"
        )

        st.dataframe(
            estadisticas_jugador
            .sort_values(
                "PJ",
                ascending=False
            )
            .head(30)
        )

        # ==========================================
        # PREVIEW
        # ==========================================

        st.subheader(
            "👀 Vista previa"
        )

        st.dataframe(
            estadisticas_jugador
            .sort_values(
                "PJ",
                ascending=False
            )
            .head(30)
        )

    except Exception as e:

        st.exception(e)

