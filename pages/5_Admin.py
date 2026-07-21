import streamlit as st
import pandas as pd
from supabase_utils import get_supabase

st.title("Admin")

supabase = get_supabase()

equipos = (
    supabase
    .table("equipos")
    .select("*")
    .execute()
)

st.success("Conexión OK")

st.dataframe(
    pd.DataFrame(equipos.data)
)
