import streamlit as st
import pandas as pd

# =====================================
# CARGA DE DATOS
# =====================================

partidos = pd.read_csv("partidos.csv")

# =====================================
# PREPARACIÓN
# =====================================

partidos["Fecha"] = pd.to_datetime(
    partidos["Fecha"]
)

partidos["goles_totales"] = (
    partidos["goles_local"]
    +
    partidos["goles_visitante"]
)

partidos["diferencia_goles"] = (
    partidos["goles_local"]
    -
    partidos["goles_visitante"]
).abs()

# =====================================
# RECORDS
# =====================================

mas_goles = partidos.loc[
    partidos["goles_totales"].idxmax()
]

menos_goles = partidos.loc[
    partidos["goles_totales"].idxmin()
]

mayor_diferencia = partidos.loc[
    partidos["diferencia_goles"].idxmax()
]

primer_partido = partidos.loc[
    partidos["Fecha"].idxmin()
]

ultimo_partido = partidos.loc[
    partidos["Fecha"].idxmax()
]

# =====================================
# TITULO
# =====================================

st.title("📚 Datos Curiosos")

st.markdown(
    "Récords e hitos históricos de FutMiércoles."
)

# =====================================
# KPIS
# =====================================

c1, c2, c3 = st.columns(3)

c1.metric(
    "Partidos Históricos",
    len(partidos)
)

c2.metric(
    "Primer Partido",
    primer_partido["Fecha"].strftime("%d/%m/%Y")
)

c3.metric(
    "Último Partido",
    ultimo_partido["Fecha"].strftime("%d/%m/%Y")
)

st.divider()

# =====================================
# PARTIDO CON MÁS GOLES
# =====================================

st.subheader("🔥 Partido con más goles")

st.success(
    f"{mas_goles['Local']} "
    f"{int(mas_goles['goles_local'])} - "
    f"{int(mas_goles['goles_visitante'])} "
    f"{mas_goles['Otros']}"
)

st.write(
    f"📅 Fecha: {mas_goles['Fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    f"⚽ Total de goles: {int(mas_goles['goles_totales'])}"
)

st.divider()

# =====================================
# PARTIDO CON MENOS GOLES
# =====================================

st.subheader("🧤 Partido con menos goles")

st.info(
    f"{menos_goles['Local']} "
    f"{int(menos_goles['goles_local'])} - "
    f"{int(menos_goles['goles_visitante'])} "
    f"{menos_goles['Otros']}"
)

st.write(
    f"📅 Fecha: {menos_goles['Fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    f"⚽ Total de goles: {int(menos_goles['goles_totales'])}"
)

st.divider()

# =====================================
# MAYOR GOLEADA
# =====================================

st.subheader("💥 Mayor diferencia de goles")

st.warning(
    f"{mayor_diferencia['Local']} "
    f"{int(mayor_diferencia['goles_local'])} - "
    f"{int(mayor_diferencia['goles_visitante'])} "
    f"{mayor_diferencia['Otros']}"
)

st.write(
    f"📅 Fecha: {mayor_diferencia['Fecha'].strftime('%d/%m/%Y')}"
)

st.write(
    f"📊 Diferencia: {int(mayor_diferencia['diferencia_goles'])} goles"
)

st.divider()

# =====================================
# TABLA RESUMEN
# =====================================

st.subheader("🏆 Resumen de récords")

resumen = pd.DataFrame({
    "Récord": [
        "Partido con más goles",
        "Partido con menos goles",
        "Mayor diferencia de goles"
    ],
    "Valor": [
        int(mas_goles["goles_totales"]),
        int(menos_goles["goles_totales"]),
        int(mayor_diferencia["diferencia_goles"])
    ],
    "Fecha": [
        mas_goles["Fecha"].strftime("%d/%m/%Y"),
        menos_goles["Fecha"].strftime("%d/%m/%Y"),
        mayor_diferencia["Fecha"].strftime("%d/%m/%Y")
    ]
})

st.dataframe(
    resumen,
    use_container_width=True,
    hide_index=True
)
