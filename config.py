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

CHUNKS_JSON = OUTPUT_DIR / "chunks.json"


# =========================================================
# CHUNKING
# =========================================================

# Valores iniciales para la primera versión.
# Se podrán modificar posteriormente durante la evaluación.
CHUNK_SIZE = 1_000
CHUNK_OVERLAP = 100


# =========================================================
# EMBEDDINGS
# =========================================================

EMBEDDINGS_JSON = OUTPUT_DIR / "embeddings.json"

EMBEDDING_MODEL = "gemini-embedding-2"

EMBEDDING_DIMENSIONS = 768

# Tamaño de los grupos procesados por nuestro código.
# No corresponde a la Batch API de Google.
EMBED_BATCH_SIZE = 50

# Durante las primeras pruebas se procesará
# únicamente una parte del corpus.
# None = procesar todos los chunks.
MAX_CHUNKS_EMBED = 100