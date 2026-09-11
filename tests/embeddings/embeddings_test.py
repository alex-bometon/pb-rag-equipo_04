# comprueba que el archivo embeddings.json es lo esperado

from pathlib import Path
import sys
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CHUNKS_JSON,
    EMBEDDINGS_JSON,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    MAX_CHUNKS_EMBED,
)


# =========================================================
# CARGA DE ARTEFACTOS
# =========================================================

def cargar_json(ruta):
    """
    Carga un archivo JSON.
    """

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {ruta}"
        )

    with ruta.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        return json.load(archivo)


# =========================================================
# COMPROBACIÓN
# =========================================================

def comprobar_embeddings():
    """
    Comprueba la integridad de embeddings.json.

    No realiza llamadas a Gemini.
    """

    chunks_payload = cargar_json(
        CHUNKS_JSON
    )

    embeddings_payload = cargar_json(
        EMBEDDINGS_JSON
    )

    chunks = chunks_payload["chunks"]
    items = embeddings_payload["items"]

    # -----------------------------------------------------
    # 1. CONFIGURACIÓN GENERAL
    # -----------------------------------------------------

    assert (
        embeddings_payload["embedding_model"]
        == EMBEDDING_MODEL
    ), (
        "El modelo guardado no coincide con "
        "EMBEDDING_MODEL."
    )

    assert (
        embeddings_payload["embedding_dimensions"]
        == EMBEDDING_DIMENSIONS
    ), (
        "Las dimensiones declaradas no coinciden "
        "con EMBEDDING_DIMENSIONS."
    )

    assert (
        embeddings_payload["total_chunks_origen"]
        == len(chunks)
    ), (
        "total_chunks_origen no coincide con "
        "chunks.json."
    )

    # -----------------------------------------------------
    # 2. NÚMERO ESPERADO DE EMBEDDINGS
    # -----------------------------------------------------

    if MAX_CHUNKS_EMBED is None:
        esperados = len(chunks)
    else:
        esperados = min(
            MAX_CHUNKS_EMBED,
            len(chunks),
        )

    assert len(items) == esperados, (
        f"Se esperaban {esperados} embeddings "
        f"y hay {len(items)}."
    )

    assert (
        embeddings_payload["total_embeddings"]
        == len(items)
    ), (
        "total_embeddings no coincide con "
        "el número real de items."
    )

    # -----------------------------------------------------
    # 3. COMPROBACIÓN ITEM A ITEM
    # -----------------------------------------------------

    for indice, item in enumerate(items):

        assert "text" in item, (
            f"Item {indice}: falta 'text'."
        )

        assert "vector" in item, (
            f"Item {indice}: falta 'vector'."
        )

        assert "metadata" in item, (
            f"Item {indice}: falta 'metadata'."
        )

        # El texto no debe estar vacío.
        assert isinstance(
            item["text"],
            str,
        ) and item["text"].strip(), (
            f"Item {indice}: texto vacío."
        )

        # -------------------------------------------------
        # VECTOR
        # -------------------------------------------------

        vector = item["vector"]

        assert isinstance(vector, list), (
            f"Item {indice}: vector no es una lista."
        )

        assert len(vector) == EMBEDDING_DIMENSIONS, (
            f"Item {indice}: tiene "
            f"{len(vector)} dimensiones; "
            f"se esperaban {EMBEDDING_DIMENSIONS}."
        )

        assert all(
            isinstance(valor, (int, float))
            for valor in vector
        ), (
            f"Item {indice}: el vector contiene "
            "valores no numéricos."
        )

        # -------------------------------------------------
        # CORRESPONDENCIA CON CHUNKS.JSON
        # -------------------------------------------------

        chunk_original = chunks[indice]

        assert (
            item["text"]
            == chunk_original["text"]
        ), (
            f"Item {indice}: el texto no coincide "
            "con chunks.json."
        )

        assert (
            item["metadata"]
            == chunk_original["metadata"]
        ), (
            f"Item {indice}: la metadata no coincide "
            "con chunks.json."
        )

    # -----------------------------------------------------
    # RESULTADO
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("COMPROBACIÓN DE EMBEDDINGS")
    print("=" * 70)

    print(
        f"Modelo:                  "
        f"{embeddings_payload['embedding_model']}"
    )

    print(
        f"Chunks en corpus:        "
        f"{len(chunks):,}"
    )

    print(
        f"Embeddings comprobados:  "
        f"{len(items):,}"
    )

    print(
        f"Dimensiones por vector:  "
        f"{EMBEDDING_DIMENSIONS}"
    )

    print()
    print("Correspondencia texto:   OK")
    print("Correspondencia metadata: OK")
    print("Dimensiones:             OK")
    print("Valores numéricos:       OK")
    print()
    print("RESULTADO: EMBEDDINGS VÁLIDOS")


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    comprobar_embeddings()