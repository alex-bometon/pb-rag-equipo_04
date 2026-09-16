# Test de chunks para generar la estadística y conocer
# antes de hacer los embeddings qué es lo que va a pasar
# por la API y poder evaluar costes previamente

from collections import defaultdict
from statistics import mean, median
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load import cargar_corpus
from src.clean import limpiar_corpus
from src.chunk import crear_chunks


# =========================================================
# ESTADÍSTICAS GENERALES
# =========================================================

def calcular_estadisticas(chunks: list[dict]) -> dict:
    """
    Calcula estadísticas generales sobre los chunks.

    No modifica ningún dato.
    """

    tamanos = [
        len(chunk["text"])
        for chunk in chunks
    ]

    palabras = [
        len(chunk["text"].split())
        for chunk in chunks
    ]

    if not tamanos:
        return {
            "total_chunks": 0,
            "total_caracteres": 0,
            "total_palabras": 0,
        }

    return {
        "total_chunks": len(chunks),

        "total_caracteres": sum(tamanos),
        "media_caracteres": mean(tamanos),
        "mediana_caracteres": median(tamanos),
        "min_caracteres": min(tamanos),
        "max_caracteres": max(tamanos),

        "total_palabras": sum(palabras),
        "media_palabras": mean(palabras),
        "mediana_palabras": median(palabras),
    }


# =========================================================
# ESTADÍSTICAS POR TIPO DE DOCUMENTO
# =========================================================

def estadisticas_por_tipo(
    chunks: list[dict],
) -> dict[str, dict]:
    """
    Agrupa los chunks según metadata['document_type'].
    """

    grupos = defaultdict(list)

    for chunk in chunks:

        tipo = chunk["metadata"].get(
            "document_type",
            "desconocido",
        )

        grupos[tipo].append(
            len(chunk["text"])
        )

    resultado = {}

    for tipo, tamanos in grupos.items():

        resultado[tipo] = {
            "chunks": len(tamanos),
            "caracteres": sum(tamanos),
            "media": mean(tamanos),
            "mediana": median(tamanos),
            "min": min(tamanos),
            "max": max(tamanos),
        }

    return resultado


# =========================================================
# ESTADÍSTICAS POR FUENTE
# =========================================================

def estadisticas_por_fuente(
    chunks: list[dict],
) -> dict[str, dict]:
    """
    Agrupa los chunks según el archivo de origen.
    """

    grupos = defaultdict(list)

    for chunk in chunks:

        source = chunk["metadata"].get(
            "source",
            "desconocido",
        )

        grupos[source].append(
            len(chunk["text"])
        )

    resultado = {}

    for source, tamanos in grupos.items():

        resultado[source] = {
            "chunks": len(tamanos),
            "caracteres": sum(tamanos),
            "media": mean(tamanos),
            "min": min(tamanos),
            "max": max(tamanos),
        }

    return resultado


# =========================================================
# ESTIMACIÓN ORIENTATIVA DE TOKENS
# =========================================================

def estimar_tokens(
    total_caracteres: int,
) -> tuple[int, int]:
    """
    Estimación aproximada del número de tokens.

    No representa el tokenizer real de Gemini.

    Como referencia orientativa usamos un rango:
        3 caracteres/token
        4 caracteres/token
    """

    tokens_max = total_caracteres // 3
    tokens_min = total_caracteres // 4

    return tokens_min, tokens_max


# =========================================================
# IMPRESIÓN DEL INFORME
# =========================================================

def imprimir_estadisticas(
    chunks: list[dict],
) -> None:

    generales = calcular_estadisticas(
        chunks
    )

    por_tipo = estadisticas_por_tipo(
        chunks
    )

    por_fuente = estadisticas_por_fuente(
        chunks
    )

    print()
    print("=" * 70)
    print("ESTADÍSTICAS DEL CORPUS PARA EMBEDDINGS")
    print("=" * 70)

    print(
        f"Total chunks:              "
        f"{generales['total_chunks']:,}"
    )

    print(
        f"Total caracteres:          "
        f"{generales['total_caracteres']:,}"
    )

    print(
        f"Media caracteres/chunk:    "
        f"{generales['media_caracteres']:.2f}"
    )

    print(
        f"Mediana caracteres/chunk:  "
        f"{generales['mediana_caracteres']:.2f}"
    )

    print(
        f"Chunk más pequeño:         "
        f"{generales['min_caracteres']:,}"
    )

    print(
        f"Chunk más grande:          "
        f"{generales['max_caracteres']:,}"
    )

    print()

    print(
        f"Total palabras:            "
        f"{generales['total_palabras']:,}"
    )

    print(
        f"Media palabras/chunk:      "
        f"{generales['media_palabras']:.2f}"
    )

    print(
        f"Mediana palabras/chunk:    "
        f"{generales['mediana_palabras']:.2f}"
    )

    # -----------------------------------------------------
    # ESTIMACIÓN DE TOKENS
    # -----------------------------------------------------

    tokens_min, tokens_max = estimar_tokens(
        generales["total_caracteres"]
    )

    print()
    print("--- ESTIMACIÓN ORIENTATIVA DE TOKENS ---")

    print(
        f"Entre aproximadamente "
        f"{tokens_min:,} y {tokens_max:,} tokens"
    )

    print(
        "(estimación por caracteres, "
        "no tokenizer real de Gemini)"
    )

    # -----------------------------------------------------
    # POR TIPO
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("POR TIPO DE DOCUMENTO")
    print("=" * 70)

    for tipo, datos in sorted(
        por_tipo.items()
    ):

        print()
        print(tipo)

        print(
            f"  Chunks:       "
            f"{datos['chunks']:,}"
        )

        print(
            f"  Caracteres:   "
            f"{datos['caracteres']:,}"
        )

        print(
            f"  Media:        "
            f"{datos['media']:.2f}"
        )

        print(
            f"  Mediana:      "
            f"{datos['mediana']:.2f}"
        )

        print(
            f"  Mínimo:       "
            f"{datos['min']:,}"
        )

        print(
            f"  Máximo:       "
            f"{datos['max']:,}"
        )

    # -----------------------------------------------------
    # POR FUENTE
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("POR ARCHIVO DE ORIGEN")
    print("=" * 70)

    for source, datos in sorted(
        por_fuente.items()
    ):

        print()
        print(source)

        print(
            f"  Chunks:       "
            f"{datos['chunks']:,}"
        )

        print(
            f"  Caracteres:   "
            f"{datos['caracteres']:,}"
        )

        print(
            f"  Media:        "
            f"{datos['media']:.2f}"
        )

        print(
            f"  Mínimo:       "
            f"{datos['min']:,}"
        )

        print(
            f"  Máximo:       "
            f"{datos['max']:,}"
        )


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":

    corpus = cargar_corpus()

    documentos_limpios = limpiar_corpus(
        corpus
    )

    chunks = crear_chunks(
        documentos_limpios
    )

    imprimir_estadisticas(
        chunks
    )