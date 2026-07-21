import streamlit as st

st.title("🔒 Administración")

usuario = st.text_input(
    "Usuario"
)

password = st.text_input(
    "Contraseña",
    type="password"
)

if (
    usuario != st.secrets["ADMIN_USER"]
    or
    password != st.secrets["ADMIN_PASSWORD"]
):
    st.warning(
        "Acceso restringido"
    )
    st.stop()

st.success(
    "✅ Acceso autorizado"
)

st.write(
    "Panel de administración habilitado."
)
