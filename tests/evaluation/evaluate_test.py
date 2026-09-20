import argparse
import json
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


from config import (
    CHROMA_COLLECTION_NAME,
    EVAL_QUERIES_JSON,
    EVALUATION_RESULTS_DIR,
    TOP_K,
)

from query_embeddings import cargar_embeddings_queries
from src.gemini_client import crear_cliente_gemini
from src.generate import ABSTENTION_MESSAGE
from src.index import crear_cliente_chroma
from src.rag import responder


# =========================================================
# DATASET
# =========================================================

def cargar_preguntas() -> list[dict]:
    """
    Carga el dataset canónico de evaluación.
    """

    with EVAL_QUERIES_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        payload = json.load(archivo)

    queries = payload.get("queries")

    if not isinstance(queries, list):
        raise ValueError(
            "eval_queries.json debe contener una lista "
            "en la clave 'queries'."
        )

    if payload.get("total_queries") != len(queries):
        raise ValueError(
            "total_queries no coincide con el número "
            "real de preguntas."
        )

    return queries


# =========================================================
# EVALUACIÓN DE FUENTES
# =========================================================

def fuente_esperada_recuperada(
    fuentes: list[dict],
    fuentes_esperadas: list[str],
) -> bool | None:
    """
    Comprueba si aparece al menos una fuente esperada.

    Para preguntas fuera de dominio devuelve None.
    """

    if not fuentes_esperadas:
        return None

    fuentes_recuperadas = {
        fuente.get("source")
        for fuente in fuentes
        if fuente.get("source")
    }

    return any(
        fuente in fuentes_recuperadas
        for fuente in fuentes_esperadas
    )


# =========================================================
# EVALUACIÓN
# =========================================================

def evaluar(
    queries: list[dict],
    embeddings: dict[int, list[float]],
    k: int,
) -> list[dict]:
    """
    Ejecuta el flujo RAG completo sobre las preguntas
    de evaluación reutilizando los embeddings persistidos.
    """

    client = crear_cliente_gemini()

    chroma_client = crear_cliente_chroma()

    collection = chroma_client.get_collection(
        name=CHROMA_COLLECTION_NAME
    )

    resultados = []

    try:

        for posicion, query in enumerate(
            queries,
            start=1,
        ):

            query_id = query["id"]
            pregunta = query["pregunta"]

            print()
            print("=" * 70)
            print(
                f"[{posicion}/{len(queries)}] "
                f"ID {query_id}"
            )
            print("=" * 70)
            print(pregunta)

            try:

                resultado = responder(
                    pregunta=pregunta,
                    k=k,
                    client=client,
                    collection=collection,
                    query_embedding=embeddings[
                        query_id
                    ],
                )

                respuesta = resultado["answer"]
                fuentes = resultado["sources"]
                chunks = resultado["chunks"]

                abstained = (
                    respuesta.strip()
                    == ABSTENTION_MESSAGE
                )

                abstencion_esperada = (
                    not query["es_respondible"]
                )

                abstencion_correcta = (
                    abstained
                    == abstencion_esperada
                )

                retrieval_hit = (
                    fuente_esperada_recuperada(
                        fuentes,
                        query["fuentes_esperadas"],
                    )
                )

                print()
                print("RESPUESTA:")
                print(respuesta)

                print()
                print("FUENTES:")

                for fuente in fuentes:
                    print(
                        f"- {fuente.get('source')}"
                    )

                if retrieval_hit is not None:
                    print(
                        "\nFuente esperada recuperada: "
                        f"{'SÍ' if retrieval_hit else 'NO'}"
                    )

                print(
                    "Comportamiento de abstención: "
                    f"{'CORRECTO' if abstencion_correcta else 'INCORRECTO'}"
                )

                resultados.append(
                    {
                        "id": query_id,
                        "categoria": query["categoria"],
                        "pregunta": pregunta,
                        "es_respondible": query[
                            "es_respondible"
                        ],
                        "fuentes_esperadas": query[
                            "fuentes_esperadas"
                        ],
                        "answer": respuesta,
                        "sources": fuentes,
                        "chunks": chunks,
                        "retrieval_hit": retrieval_hit,
                        "abstained": abstained,
                        "abstention_correct": (
                            abstencion_correcta
                        ),
                    }
                )

            except Exception as error:

                print(
                    f"\nERROR: {error}"
                )

                resultados.append(
                    {
                        "id": query_id,
                        "categoria": query["categoria"],
                        "pregunta": pregunta,
                        "error": str(error),
                    }
                )

    finally:
        client.close()

    return resultados


# =========================================================
# RESUMEN
# =========================================================

def mostrar_resumen(
    resultados: list[dict],
) -> None:

    validos = [
        resultado
        for resultado in resultados
        if "error" not in resultado
    ]

    errores = (
        len(resultados)
        - len(validos)
    )

    respondibles = [
        resultado
        for resultado in validos
        if resultado["es_respondible"]
    ]

    fuera_dominio = [
        resultado
        for resultado in validos
        if not resultado["es_respondible"]
    ]

    retrieval_hits = sum(
        resultado["retrieval_hit"] is True
        for resultado in respondibles
    )

    respuestas_correctas = sum(
        not resultado["abstained"]
        for resultado in respondibles
    )

    abstenciones_correctas = sum(
        resultado["abstention_correct"]
        for resultado in fuera_dominio
    )

    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Preguntas totales:             "
        f"{len(resultados)}"
    )

    print(
        f"Errores de ejecución:           "
        f"{errores}"
    )

    print(
        f"Preguntas respondibles:         "
        f"{len(respondibles)}"
    )

    print(
        f"Fuente esperada recuperada:     "
        f"{retrieval_hits}/{len(respondibles)}"
    )

    print(
        f"Respondidas sin abstención:     "
        f"{respuestas_correctas}/{len(respondibles)}"
    )

    print(
        f"Preguntas fuera de dominio:     "
        f"{len(fuera_dominio)}"
    )

    print(
        f"Abstenciones correctas OOD:     "
        f"{abstenciones_correctas}/{len(fuera_dominio)}"
    )


# =========================================================
# GUARDADO
# =========================================================

def guardar_resultados(
    resultados: list[dict],
    k: int,
) -> Path:

    EVALUATION_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta = (
        EVALUATION_RESULTS_DIR
        / f"results_k{k}.json"
    )

    with ruta.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            resultados,
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    return ruta


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Evaluación end-to-end del sistema RAG."
        )
    )

    parser.add_argument(
        "--k",
        type=int,
        default=TOP_K,
        help="Número de chunks recuperados.",
    )

    args = parser.parse_args()

    if args.k <= 0:
        raise ValueError(
            "k debe ser mayor que 0."
        )

    queries = cargar_preguntas()
    embeddings = cargar_embeddings_queries()

    faltantes = [
        query["id"]
        for query in queries
        if query["id"] not in embeddings
    ]

    if faltantes:
        raise ValueError(
            "Faltan embeddings para las preguntas: "
            f"{faltantes}"
        )

    print("=" * 70)
    print("EVALUACIÓN END-TO-END DEL RAG")
    print("=" * 70)

    print(
        f"Preguntas: {len(queries)}"
    )

    print(
        f"K: {args.k}"
    )

    resultados = evaluar(
        queries=queries,
        embeddings=embeddings,
        k=args.k,
    )

    mostrar_resumen(
        resultados
    )

    ruta = guardar_resultados(
        resultados=resultados,
        k=args.k,
    )

    print()
    print(
        f"Resultados guardados en: {ruta}"
    )


if __name__ == "__main__":
    main()