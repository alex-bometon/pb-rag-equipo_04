# Configuración general de lo que tenga que ver con la webapp
# Llegado a algún punto de madurez habrá un único archivo config.py
# para todo el proyecto.

# Afecta a: SQLite, Streamlit, usuarios, sesiones,
# modos de consulta (por interfaz), configuración visual...

from pathlib import Path

# RUTAS
WEBAPP_DIR = Path(__file__).resolve().parent

STORAGE_DIR = WEBAPP_DIR / "storage"

DB_PATH = STORAGE_DIR / "webapp.db"

# Configuración visual
APP_NAME = "ReciclaTIA"
# APP_ICON

# Opciones del asistente
QUERY_MODES = {
    "auto": "Automático",
    "classification": "Clasificar residuo",
    "recycling": "Cómo reciclarlo",
    "containers": "Información sobre contenedores",
    "clean_points": "Información sobre puntos limpios",
}

# Configuración de sesión
# SESSION_KEYS