import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

st.title("📥 Importar Históricos")

supabase = get_supabase()

# ==================================================
# CARGA DE CSV
# ==================================================

participaciones_historicas = pd.read_csv(
    "participaciones.csv"
)

partidos_historicos = pd.read_csv(
    "partidos.csv"
)

st.subheader("Control de calidad - Partidos")

st.write(
    f"Total filas partidos.csv: {len(partidos_historicos)}"
)

st.write(
    "Fechas no nulas:",
    partidos_historicos["Fecha"].notna().sum()
)

st.write(
    "Local no nulo:",
    partidos_historicos["Local"].notna().sum()
)

st.write(
    "Visitante no nulo:",
    partidos_historicos["Otros"].notna().sum()
)

st.subheader("Primeras 10 filas")

st.dataframe(
    partidos_historicos[
        [
            "Fecha",
            "Local",
            "Otros",
            "goles_local",
            "goles_visitante"
        ]
    ].head(10)
)

st.subheader("Últimas 10 filas")

st.dataframe(
    partidos_historicos[
        [
            "Fecha",
            "Local",
            "Otros",
            "goles_local",
            "goles_visitante"
        ]
    ].tail(10)
)

st.subheader("Filas con problemas")

st.write(
    partidos_historicos[
        partidos_historicos["Fecha"].isna()
    ].head(20)
)

st.subheader("Partidos sin visitante")

st.dataframe(
    partidos_historicos[
        partidos_historicos["Otros"].isna()
    ]
)

st.subheader("Partidos con fecha válida")

partidos_validos = partidos_historicos[
    (
        partidos_historicos["Fecha"].notna()
    )
    &
    (
        partidos_historicos["Local"].notna()
    )
    &
    (
        partidos_historicos["Otros"].notna()
    )
]

st.write(
    f"Partidos válidos: {len(partidos_validos)}"
)

st.subheader("Partidos válidos estimados")

partidos_validos = partidos_historicos[
    (
        partidos_historicos["Fecha"].notna()
    )
    &
    (
        partidos_historicos["Local"].notna()
    )
    &
    (
        partidos_historicos["Otros"].notna()
    )
    &
    (
        ~partidos_historicos["Local"]
        .astype(str)
        .str.contains(
            "NO SE JUGO|PARTIDO FALLIDO",
            case=False,
            na=False
        )
    )
]

st.write(
    f"Partidos válidos: {len(partidos_validos)}"
)

# ==================================================
# JUGADORES Y EQUIPOS
# ==================================================

jugadores_historicos = sorted(
    participaciones_historicas["jugador"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

equipos_historicos = sorted(
    participaciones_historicas["equipo"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

st.write(
    f"👤 Jugadores encontrados: {len(jugadores_historicos)}"
)

st.write(
    f"⚽ Equipos encontrados: {len(equipos_historicos)}"
)

st.write(
    f"🏆 Partidos encontrados: {len(partidos_historicos)}"
)

st.write(
    f"📋 Participaciones encontradas: {len(participaciones_historicas)}"
)

st.divider()

# ==================================================
# IMPORTAR JUGADORES
# ==================================================

if st.button("👤 Importar Jugadores"):

    actuales = (
        supabase
        .table("jugadores")
        .select("jugador")
        .execute()
    )

    existentes = {
        x["jugador"].strip().upper()
        for x in actuales.data
    }

    nuevos = 0

    for jugador in jugadores_historicos:

        nombre = jugador.strip()

        if nombre.upper() not in existentes:

            (
                supabase
                .table("jugadores")
                .insert(
                    {
                        "jugador": nombre
                    }
                )
                .execute()
            )

            nuevos += 1

    st.success(
        f"✅ {nuevos} jugadores importados"
    )

# ==================================================
# IMPORTAR EQUIPOS
# ==================================================

if st.button("⚽ Importar Equipos"):

    actuales = (
        supabase
        .table("equipos")
        .select("equipo")
        .execute()
    )

    existentes = {
        x["equipo"].strip().upper()
        for x in actuales.data
    }

    nuevos = 0

    for equipo in equipos_historicos:

        nombre = equipo.strip()

        if nombre.upper() not in existentes:

            (
                supabase
                .table("equipos")
                .insert(
                    {
                        "equipo": nombre
                    }
                )
                .execute()
            )

            nuevos += 1

    st.success(
        f"✅ {nuevos} equipos importados"
    )

# ==================================================
# IMPORTAR PARTIDOS
# ==================================================

if st.button("🏆 Importar Partidos"):

    actuales = (
        supabase
        .table("partidos")
        .select("*")
        .execute()
    )

    existentes = {
        (
            str(x["fecha"]),
            str(x["equipo_local"]),
            int(x["goles_local"]),
            str(x["equipo_visitante"]),
            int(x["goles_visitante"])
        )
        for x in actuales.data
    }

    nuevos = 0

    for _, fila in partidos_historicos.iterrows():

        try:

            clave = (
                str(fila["Fecha"])[:10],
                str(fila["Local"]),
                int(fila["goles_local"]),
                str(fila["Otros"]),
                int(fila["goles_visitante"])
            )

            if clave not in existentes:

                (
                    supabase
                    .table("partidos")
                    .insert(
                        {
                            "fecha": str(fila["Fecha"])[:10],
                            "equipo_local": str(fila["Local"]),
                            "goles_local": int(fila["goles_local"]),
                            "equipo_visitante": str(fila["Otros"]),
                            "goles_visitante": int(fila["goles_visitante"])
                        }
                    )
                    .execute()
                )

                nuevos += 1

        except Exception:

            continue

    st.success(
        f"✅ {nuevos} partidos importados"
    )

# ==================================================
# IMPORTAR PARTICIPACIONES
# ==================================================

if st.button("📋 Importar Participaciones"):

    partidos_supabase = (
        supabase
        .table("partidos")
        .select("*")
        .execute()
    )

    partidos_db = pd.DataFrame(
        partidos_supabase.data
    )

    if partidos_db.empty:

        st.error(
            "Primero importá los partidos."
        )

    else:

        registros = []

        for _, fila in participaciones_historicas.iterrows():

            try:

                fecha = str(
                    fila["id_partido"]
                )[:10]

                partido_match = partidos_db[
                    partidos_db["fecha"]
                    .astype(str)
                    ==
                    fecha
                ]

                if len(partido_match) == 0:
                    continue

                partido_id = (
                    partido_match
                    .iloc[0]["id"]
                )

                registros.append(
                    {
                        "partido_id": partido_id,
                        "jugador": str(
                            fila["jugador"]
                        ),
                        "equipo": str(
                            fila["equipo"]
                        )
                    }
                )

            except Exception:

                continue

        if len(registros) > 0:

            (
                supabase
                .table("participaciones")
                .insert(registros)
                .execute()
            )

        st.success(
            f"✅ {len(registros)} participaciones importadas"
        )
