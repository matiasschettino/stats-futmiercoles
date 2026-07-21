import streamlit as st
from supabase_utils import get_supabase
import traceback

st.title("Debug Supabase")

try:

    supabase = get_supabase()

    st.success("✅ Cliente creado")

    respuesta = (
        supabase
        .table("equipos")
        .select("*")
        .execute()
    )

    st.success("✅ Consulta ejecutada")

    st.write(respuesta.data)

except Exception as e:

    st.error(type(e).__name__)

    st.code(str(e))

    st.code(traceback.format_exc())
