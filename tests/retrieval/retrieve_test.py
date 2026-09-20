import sys
from pathlib import Path


# =========================================================
# PATH DEL PROYECTO
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests"

for path in (PROJECT_ROOT, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from config import CHROMA_COLLECTION_NAME
from query_embeddings import (
    cargar_embeddings_queries,
    cargar_queries,
)
from src.index import crear_cliente_chroma
from src.retrieve import buscar_chunks_relevantes


# Valores comparados durante la evaluación de retrieval.
K_VALUES = (3, 5, 8, 10)


def fuente_esperada_recuperada(
    chunks: list[dict],
    fuentes_esperadas: list[str],
) -> bool:
    """
    Comprueba si al menos una fuente esperada aparece
    entre los chunks recuperados.
    """

    fuentes = {
        chunk.get("metadata", {}).get("source")
        for chunk in chunks
    }

    return any(
        fuente in fuentes
        for fuente in fuentes_esperadas
    )


def evaluar_k(
    queries: list[dict],
    embeddings: dict[int, list[float]],
    collection,
    k: int,
) -> tuple[int, int]:
    """
    Evalúa retrieval para un valor concreto de K.

    Las preguntas fuera de dominio se ejecutan para observar
    qué recupera el sistema, pero no cuentan en la tasa de
    acierto de fuentes.
    """

    aciertos = 0
    respondibles = 0

    print()
    print("=" * 70)
    print(f"K = {k}")
    print("=" * 70)

    for query in queries:

        query_id = query["id"]
        pregunta = query["pregunta"]

        chunks = buscar_chunks_relevantes(
            pregunta=pregunta,
            top_k=k,
            collection=collection,
            query_embedding=embeddings[query_id],
        )

        top = chunks[0]

        top_source = (
            top.get("metadata", {}).get("source")
        )

        top_distance = top.get("distance")

        print()
        print(f"[{query_id}] {pregunta}")
        print(f"    Top fuente:    {top_source}")
        print(f"    Top distancia: {top_distance:.4f}")

        if query["es_respondible"]:

            respondibles += 1

            hit = fuente_esperada_recuperada(
                chunks,
                query["fuentes_esperadas"],
            )

            if hit:
                aciertos += 1

            print(
                "    Fuente esperada recuperada: "
                f"{'SÍ' if hit else 'NO'}"
            )

        else:
            print(
                "    Fuera de dominio "
                "(no puntúa retrieval)"
            )

    return aciertos, respondibles


def main() -> None:

    queries = cargar_queries()
    embeddings = cargar_embeddings_queries()

    ids_sin_embedding = [
        query["id"]
        for query in queries
        if query["id"] not in embeddings
    ]

    if ids_sin_embedding:
        raise ValueError(
            "Faltan embeddings para las preguntas: "
            f"{ids_sin_embedding}"
        )

    chroma_client = crear_cliente_chroma()

    collection = chroma_client.get_collection(
        name=CHROMA_COLLECTION_NAME
    )

    print("=" * 70)
    print("EVALUACIÓN DE RETRIEVAL")
    print("=" * 70)

    print(
        f"Preguntas totales: {len(queries)}"
    )

    print(
        f"Registros ChromaDB: {collection.count()}"
    )

    resumen = []

    for k in K_VALUES:

        aciertos, respondibles = evaluar_k(
            queries=queries,
            embeddings=embeddings,
            collection=collection,
            k=k,
        )

        resumen.append(
            (k, aciertos, respondibles)
        )

    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    for k, aciertos, total in resumen:

        porcentaje = (
            aciertos / total * 100
            if total
            else 0
        )

        print(
            f"K={k:<2} -> "
            f"{aciertos}/{total} "
            f"({porcentaje:.1f} %)"
        )


if __name__ == "__main__":
    main()