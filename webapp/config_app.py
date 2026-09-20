# Configuración general de lo que tenga que ver con la webapp
# Llegado a algún punto de madurez habrá un único archivo config.py
# para todo el proyecto.

# Afecta a: SQLite, Streamlit, usuarios, sesiones,
# modos de consulta (por interfaz), configuración visual...

# ¿Cómo se llama la app? ¿Qué descripción tiene? ¿Qué modos tiene?
# ¿Cómo se llaman visualmente los modos? ¿En qué ruta está cada cosa, como la BBDD?

from pathlib import Path


# -------------------------
# Rutas de la webapp
# -------------------------

WEBAPP_DIR = Path(__file__).resolve().parent
STORAGE_DIR = WEBAPP_DIR / "storage"
DB_PATH = STORAGE_DIR / "webapp.db"


# -------------------------
# Configuración general
# -------------------------

APP_NAME = "ReciclaTIA"

APP_DESCRIPTION = (
    "Consulta cómo gestionar correctamente tus residuos "
    "y obtén información sobre reciclaje y puntos de recogida "
    "en la ciudad de Madrid."
)