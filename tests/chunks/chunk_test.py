from collections import Counter
from pathlib import Path
import sys


# =========================================================
# IMPORTS DEL PROYECTO
# =========================================================

# chunk_test.py está en:
#
# pb-rag-equipo_04/tests/chunks/chunk_test.py
#
# parents[0] -> chunks/
# parents[1] -> tests/
# parents[2] -> pb-rag-equipo_04/

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config import CHUNK_SIZE, CHUNK_OVERLAP
from src.load import cargar_corpus
from src.clean import limpiar_corpus
from src.chunk import crear_chunks


# =========================================================
# PIPELINE
# =========================================================

corpus = cargar_corpus()

documentos = limpiar_corpus(corpus)

chunks = crear_chunks(documentos)


# =========================================================
# RESUMEN
# =========================================================

print("=" * 60)
print("RESUMEN DEL PIPELINE")
print("=" * 60)

print(f"Archivos originales: {len(corpus)}")
print(f"Documentos limpios: {len(documentos)}")
print(f"Chunks generados: {len(chunks)}")


# =========================================================
# MUESTRA DE CHUNKS
# =========================================================

print("\n" + "=" * 60)
print("PRIMEROS 5 CHUNKS")
print("=" * 60)

for i, chunk in enumerate(chunks[:5]):

    print(f"\n--- CHUNK {i} ---")

    print("\nTEXTO:")
    print(chunk["text"])

    print("\nMETADATOS:")
    print(chunk["metadata"])


# =========================================================
# DISTRIBUCIÓN POR TIPO DE DOCUMENTO
# =========================================================

tipos = Counter(
    chunk["metadata"]["document_type"]
    for chunk in chunks
)

print("\n" + "=" * 60)
print("CHUNKS POR TIPO")
print("=" * 60)

for tipo, cantidad in tipos.items():
    print(f"{tipo}: {cantidad}")


# =========================================================
# CHUNKS PROCEDENTES DE HTML
# =========================================================

chunks_html = [
    chunk
    for chunk in chunks
    if chunk["metadata"]["format"] == "html"
]

print("\n" + "=" * 60)
print(f"CHUNKS HTML: {len(chunks_html)}")
print("=" * 60)

for i, chunk in enumerate(chunks_html[:10]):

    print(f"\n--- HTML CHUNK {i} ---")

    print(f"Fuente: {chunk['metadata']['source']}")
    print(
        f"Chunk: "
        f"{chunk['metadata']['chunk_index'] + 1}"
        f"/{chunk['metadata']['chunk_count']}"
    )
    print(
        f"Tamaño: "
        f"{chunk['metadata']['chunk_size']}"
    )

    print("\nTEXTO:")
    print(chunk["text"])