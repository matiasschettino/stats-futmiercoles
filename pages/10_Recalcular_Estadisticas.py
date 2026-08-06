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
            return valor.item()
        except (ValueError, AttributeError):
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
        # PARTIDOS ORDENADOS Y RACHA GANADORA
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
            mejor_racha = 0
            mejor_desde = None
            mejor_hasta = None
            racha_actual = 0
            fecha_inicio_actual = None

            for _, fila in grupo.iterrows():
                resultado = fila["resultado_jugador"]
                fecha = fila["fecha"]

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
            "racha_activa",
            "tipo_racha_activa"
        ]

        jugadores_master_nuevo = estadisticas_jugador[
            columnas_finales
        ].copy()

        # Supabase define estas columnas como bigint.
        # Se convierten explícitamente para evitar valores como "2.0".
        columnas_enteras = [
            "PJ",
            "G",
            "E",
            "P",
            "partidos_equipo_favorito",
            "pj_mejor_companero",
            "pj_vs_rival_mas_frecuente",
            "mejor_racha_ganadora",
            "racha_activa"
        ]

        for columna in columnas_enteras:
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
        st.session_state["chequeo_realizado"] = True
        st.session_state["backup_generado"] = False
        st.session_state["backup_parejas_generado"] = False

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

        st.subheader("👀 Vista previa")
        st.dataframe(
            jugadores_master_nuevo
            .sort_values("PJ", ascending=False)
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
    st.info(
        "El backup de parejas y la actualización son acciones independientes."
    )

    col_backup_parejas, col_actualizar_parejas = st.columns(2)

    with col_backup_parejas:
        if st.button(
            "💾 Backup estadísticas de parejas",
            key="btn_backup_estadisticas_parejas",
            use_container_width=True
        ):
            try:
                backup_parejas = st.session_state[
                    "backup_parejas_registros"
                ]

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
            use_container_width=True
        ):
            try:
                registros_parejas = st.session_state[
                    "estadisticas_parejas_registros"
                ]

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

