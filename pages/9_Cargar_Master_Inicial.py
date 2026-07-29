import streamlit as st
import pandas as pd

# ==================================================
# LOGIN
# ==================================================

st.title("🔍 Diagnóstico Master Inicial")

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

# ==================================================
# LEER CSV
# ==================================================

jugadores_master = pd.read_csv(
    "jugadores_master.csv"
)

equipos_master = pd.read_csv(
    "equipos_master.csv"
)

estadisticas_parejas = pd.read_csv(
    "estadisticas_parejas.csv"
)

# ==================================================
# JUGADORES
# ==================================================

st.header("👤 JUGADORES MASTER")

st.write("Columnas:")

st.write(
    jugadores_master.columns.tolist()
)

st.write("Tipos:")

st.write(
    jugadores_master.dtypes.astype(str)
)

for col in jugadores_master.columns:

    try:

        if str(jugadores_master[col].dtype) == "float64":

            st.warning(
                f"FLOAT EN JUGADORES: {col}"
            )

            st.write(
                jugadores_master[
                    [col]
                ].head(20)
            )

    except:
        pass

# ==================================================
# EQUIPOS
# ==================================================

st.header("⚽ EQUIPOS MASTER")

st.write("Columnas:")

st.write(
    equipos_master.columns.tolist()
)

st.write("Tipos:")

st.write(
    equipos_master.dtypes.astype(str)
)

for col in equipos_master.columns:

    try:

        if str(equipos_master[col].dtype) == "float64":

            st.warning(
                f"FLOAT EN EQUIPOS: {col}"
            )

            st.write(
                equipos_master[
                    [col]
                ].head(20)
            )

    except:
        pass

# ==================================================
# PAREJAS
# ==================================================

st.header("🤝 PAREJAS")

st.write("Columnas:")

st.write(
    estadisticas_parejas.columns.tolist()
)

st.write("Tipos:")

st.write(
    estadisticas_parejas.dtypes.astype(str)
)

for col in estadisticas_parejas.columns:

    try:

        if str(estadisticas_parejas[col].dtype) == "float64":

            st.warning(
                f"FLOAT EN PAREJAS: {col}"
            )

            st.write(
                estadisticas_parejas[
                    [col]
                ].head(20)
            )

    except:
        pass
