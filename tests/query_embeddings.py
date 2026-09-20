# Genera los embeddings del test UNA vez
# El test los puede reutilizar sin llamar a la API cada vez

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EVAL_QUERIES_JSON,
    EVAL_QUERY_EMBEDDINGS_JSON,
)

from src.gemini_client import crear_cliente_gemini
from src.retrieve import embeddear_pregunta_original


def cargar_queries() -> list[dict]:
    with EVAL_QUERIES_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        payload = json.load(archivo)

    return payload["queries"]


def cargar_embeddings_queries() -> dict[int, list[float]]:
    """
    Carga los embeddings ya generados de las preguntas.
    """

    if not EVAL_QUERY_EMBEDDINGS_JSON.exists():
        raise FileNotFoundError(
            "No existe la caché de embeddings de evaluación. "
            "Ejecuta primero: python tests/query_embeddings.py"
        )

    with EVAL_QUERY_EMBEDDINGS_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        payload = json.load(archivo)

    if payload["model"] != EMBEDDING_MODEL:
        raise ValueError(
            "La caché utiliza otro modelo de embeddings."
        )

    if payload["dimensions"] != EMBEDDING_DIMENSIONS:
        raise ValueError(
            "La caché utiliza otra dimensionalidad."
        )

    return {
        item["id"]: item["vector"]
        for item in payload["queries"]
    }


def generar_embeddings_queries() -> None:
    """
    Regenera desde cero los embeddings de todas las
    preguntas de evaluación y los persiste en disco.
    """

    queries = cargar_queries()

    client = crear_cliente_gemini()

    items = []

    try:
        for posicion, query in enumerate(
            queries,
            start=1,
        ):
            print(
                f"[{posicion}/{len(queries)}] "
                f"{query['pregunta']}"
            )

            vector = embeddear_pregunta_original(
                client,
                query["pregunta"],
            )

            items.append(
                {
                    "id": query["id"],
                    "pregunta": query["pregunta"],
                    "vector": vector,
                }
            )

    finally:
        client.close()

    payload = {
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        "queries": items,
    }

    EVAL_QUERY_EMBEDDINGS_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with EVAL_QUERY_EMBEDDINGS_JSON.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            payload,
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Embeddings generados: {len(items)}"
    )
    print(
        f"Guardados en: {EVAL_QUERY_EMBEDDINGS_JSON}"
    )


if __name__ == "__main__":
    generar_embeddings_queries()