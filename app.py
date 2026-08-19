import os
import streamlit as st
import pandas as pd

from supabase_utils import get_supabase


# ==================================================
# CONFIGURACION DE PAGINA
# ==================================================

st.set_page_config(
    page_title="Stats FutMiércoles",
    page_icon="⚽",
    layout="wide"
)

supabase = get_supabase()


# ==================================================
# ESTILOS
# ==================================================

st.markdown(
    """
    <style>
    .hero-title {
        font-size: 54px;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        font-size: 19px;
        line-height: 1.5;
        color: #E5E7EB;
        margin-bottom: 24px;
        max-width: 980px;
    }
    .section-title {
        font-size: 28px;
        font-weight: 800;
        margin-top: 8px;
        margin-bottom: 14px;
    }
    .nav-card {
        background-color: #14304a;
        border-radius: 12px;
        padding: 20px 18px;
        min-height: 190px;
        height: 190px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        box-sizing: border-box;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .nav-card-title {
        color: #2D9CFF;
        font-size: 20px;
        line-height: 1.25;
        font-weight: 800;
        margin-bottom: 12px;
    }
    .nav-card-text {
        color: #E5E7EB;
        font-size: 15px;
        line-height: 1.45;
        font-weight: 500;
    }
    .guide-box {
        background-color: rgba(20,48,74,0.75);
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid rgba(255,255,255,0.08);
        color: #E5E7EB;
        font-size: 16px;
        line-height: 1.55;
    }
    .cover-caption {
        color: #9CA3AF;
        font-size: 13px;
        margin-top: -6px;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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

        registros.extend(respuesta.data)

        if len(respuesta.data) < lote:
            break

        desde += lote

    return pd.DataFrame(registros)


def mostrar_entero(valor):
    if valor is None or pd.isna(valor):
        return 0

    return int(valor)


def numero_formato(valor):
    return f"{mostrar_entero(valor):,}".replace(",", ".")


def render_nav_card(titulo, descripcion):
    st.markdown(
        f"""
        <div class="nav-card">
            <div class="nav-card-title">{titulo}</div>
            <div class="nav-card-text">{descripcion}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# CARGA DESDE SUPABASE
# ==================================================

try:
    jugadores = leer_tabla_completa("jugadores_master")
    equipos = leer_tabla_completa("equipos_master")
    partidos = leer_tabla_completa("partidos")
except Exception as error:
    st.error("No se pudieron cargar los datos desde Supabase.")
    st.exception(error)
    st.stop()

if jugadores.empty:
    st.warning("La tabla jugadores_master no contiene registros.")
    st.stop()

if equipos.empty:
    st.warning("La tabla equipos_master no contiene registros.")
    st.stop()

if partidos.empty:
    st.warning("La tabla partidos no contiene registros.")
    st.stop()


# ==================================================
# VALIDACION DE COLUMNAS
# ==================================================

columnas_jugadores = ["jugador"]
columnas_equipos = ["equipo"]
columnas_partidos = [
    "fecha",
    "equipo_local",
    "equipo_visitante",
    "goles_local",
    "goles_visitante"
]

for nombre_tabla, dataframe, columnas_requeridas in [
    ("jugadores_master", jugadores, columnas_jugadores),
    ("equipos_master", equipos, columnas_equipos),
    ("partidos", partidos, columnas_partidos)
]:
    columnas_faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in dataframe.columns
    ]

    if columnas_faltantes:
        st.error(
            f"Faltan columnas en {nombre_tabla}: "
            + ", ".join(columnas_faltantes)
        )
        st.stop()


# ==================================================
# LIMPIEZA
# ==================================================

partidos["fecha"] = pd.to_datetime(partidos["fecha"], errors="coerce")
partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")

jugadores = jugadores.dropna(subset=["jugador"]).copy()
equipos = equipos.dropna(subset=["equipo"]).copy()
partidos_validos = partidos.dropna(
    subset=[
        "fecha",
        "equipo_local",
        "equipo_visitante",
        "goles_local",
        "goles_visitante"
    ]
).copy()

marcas_invalidas = "PARTIDO FALLIDO|NO SE JUGO|NO SE JUGÓ"
partidos_validos = partidos_validos[
    ~partidos_validos["equipo_local"]
    .astype(str)
    .str.contains(marcas_invalidas, case=False, na=False)
    &
    ~partidos_validos["equipo_visitante"]
    .astype(str)
    .str.contains(marcas_invalidas, case=False, na=False)
].copy()

if partidos_validos.empty:
    st.warning("No hay partidos válidos para mostrar.")
    st.stop()

ultimo_partido = partidos_validos["fecha"].max()


# ==================================================
# PORTADA
# ==================================================

st.markdown(
    """
    <div class="hero-title">⚽ Stats FutMiércoles</div>
    <div class="hero-subtitle">
        Estadísticas históricas de los partidos desde 2007. Un espacio para recorrer jugadores,
        equipos, rankings, rachas, duplas, rivalidades y datos curiosos de toda la historia de FutMiércoles.
    </div>
    """,
    unsafe_allow_html=True
)

imagen_portada = "IMG-20260814-WA0018.jpg"

if os.path.exists(imagen_portada):
    st.image(imagen_portada, use_container_width=True)
elif os.path.exists(os.path.join(".", imagen_portada)):
    st.image(os.path.join(".", imagen_portada), use_container_width=True)
else:
    st.warning(
        "No se encontró la imagen de portada. Guardá la foto como "
        "IMG-20260814-WA0018.jpg en la misma carpeta del archivo principal."
    )

st.divider()


# ==================================================
# INDICADORES PRINCIPALES
# ==================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric("Jugadores", numero_formato(len(jugadores)))
c2.metric("Equipos", numero_formato(len(equipos)))
c3.metric("Partidos Históricos", numero_formato(len(partidos_validos)))
c4.metric("Último Partido", ultimo_partido.strftime("%d/%m/%Y"))

st.divider()


# ==================================================
# GUIA DE NAVEGACION
# ==================================================

st.markdown('<div class="section-title">🧭 Cómo navegar la app</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="guide-box">
        Usá el menú lateral de Streamlit para moverte entre las páginas. Cada sección está pensada para responder
        una pregunta distinta: quiénes jugaron más, qué equipos rindieron mejor, qué duplas funcionaron, qué mano a mano
        fue más parejo y qué récords históricos dejó cada partido.
    </div>
    """,
    unsafe_allow_html=True
)

st.write("")

fila_1_col_1, fila_1_col_2, fila_1_col_3 = st.columns(3)
fila_2_col_1, fila_2_col_2, fila_2_col_3 = st.columns(3)

with fila_1_col_1:
    render_nav_card(
        "👤 Jugadores",
        "Perfil completo de cada jugador: partidos, victorias, Win Rate, rachas, rivales destacados, evolución histórica y comparación contra otros jugadores."
    )

with fila_1_col_2:
    render_nav_card(
        "⚽ Equipos",
        "Lectura por equipo: rendimiento histórico, forma reciente, distribución de resultados, evolución por año, jugadores destacados y últimos partidos."
    )

with fila_1_col_3:
    render_nav_card(
        "🏆 Rankings",
        "Tablero competitivo general con rankings de jugadores, equipos, duplas, rivalidades y rachas. Incluye filtros para ajustar mínimos y cantidades."
    )

with fila_2_col_1:
    render_nav_card(
        "📚 Datos Curiosos",
        "Récords e hitos: partidos con más goles, mayor goleada, empates destacados, jugadores en partidos especiales y curiosidades por mes."
    )

with fila_2_col_2:
    render_nav_card(
        "🔄 Recalcular estadísticas",
        "Página operativa para actualizar las estadísticas base después de cargar nuevos partidos o participaciones en la base."
    )

with fila_2_col_3:
    render_nav_card(
        "📌 Recomendación de uso",
        "Empezá por Rankings para una vista general, seguí por Jugadores o Equipos para investigar detalles y cerrá con Datos Curiosos para récords históricos."
    )

st.divider()

st.caption(
    "Tip: si cargaste nuevos partidos, primero ejecutá la página de recálculo y después revisá Jugadores, Equipos, Rankings y Datos Curiosos."
)
