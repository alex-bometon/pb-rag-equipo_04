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
MAX_CHUNKS_EMBED = None

# Pausa entre lotes para respetar el límite del Free Tier.
# Con 50 embeddings por lote y un máximo de 100/minuto,
# dejamos margen respecto al límite.
EMBED_BATCH_PAUSE_SECONDS = 32

# Reintentos adicionales si la API devuelve 429.
EMBED_MAX_RETRIES = 5

# Espera tras alcanzar temporalmente la cuota.
EMBED_RETRY_SECONDS = 60


# =========================================================
# CHROMADB
# =========================================================

# Base de datos vectorial persistente.
CHROMA_DIR = OUTPUT_DIR / "chroma_db"

# Nombre de la colección utilizada por el RAG.
CHROMA_COLLECTION_NAME = "residuos_madrid"

# Métrica utilizada para comparar embeddings.
CHROMA_DISTANCE = "cosine"

# Número máximo de registros que intentaremos insertar
# en una misma operación.
INDEX_BATCH_SIZE = 100