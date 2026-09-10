from pathlib import Path



# =========================================================
# RUTAS
# =========================================================

# Raíz del proyecto:
# pg-rag-equipo_04/
BASE_DIR = Path(__file__).resolve().parent

# Carpeta general de datos
DATA_DIR = BASE_DIR / "data"

# Datos originales, sin modificar
RAW_DIR = DATA_DIR / "raw"

# Tipos de fuente
CSV_DIR = RAW_DIR / "csv"
HTML_DIR = RAW_DIR / "html"

# Salidas generadas por el pipeline
OUTPUT_DIR = BASE_DIR / "output"


# =========================================================
# CHUNKING
# =========================================================

# Valores iniciales para la primera versión.
# Se podrán modificar posteriormente durante la evaluación.
CHUNK_SIZE = 1_000
CHUNK_OVERLAP = 100