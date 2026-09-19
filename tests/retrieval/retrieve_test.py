# Comprueba el retrieval: para cada pregunta de evaluación,
# valida que ChromaDB devuelve resultados coherentes y mide
# si las fuentes esperadas aparecen entre los recuperados.
#
# También ejecuta el "experimento K": compara la tasa de
# acierto del retrieval con distintos valores de TOP_K.

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    EVAL_QUERIES_JSON,
)

from src.gemini_client import crear_cliente_gemini
from src.index import crear_cliente_chroma
from src.retrieve import buscar_chunks_relevantes


# =========================================================
# UTILIDADES
# =========================================================

def mostrar_resultado(
    nombre: str,
    correcto: bool,
    detalle: str = "",
) -> bool:
    """
    Muestra el resultado de una comprobación.
    """

    estado = "OK" if correcto else "ERROR"

    print(f"[{estado}] {nombre}")

    if detalle:
        print(f"       {detalle}")

    return correcto


def cargar_eval_queries() -> list[dict]:
    """
    Carga las preguntas de evaluación desde
    queries/eval_queries.json.
    """

    if not EVAL_QUERIES_JSON.exists():
        raise FileNotFoundError(
            f"No existe el archivo de preguntas: "
            f"{EVAL_QUERIES_JSON}"
        )

    with EVAL_QUERIES_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:

        payload = json.load(
            archivo
        )

    return payload.get(
        "queries",
        [],
    )


def alguna_fuente_esperada(
    chunks: list[dict],
    fuentes_esperadas: list[str],
) -> bool:
    """
    Comprueba si al menos una de las fuentes esperadas
    aparece entre los chunks recuperados.

    Si la pregunta no declara fuentes esperadas
    (p. ej. preguntas fuera de dominio), se considera
    superada automáticamente: no hay nada que comprobar.
    """

    if not fuentes_esperadas:
        return True

    fuentes_recuperadas = {
        chunk["metadata"].get("source")
        for chunk in chunks
    }

    return any(
        fuente in fuentes_recuperadas
        for fuente in fuentes_esperadas
    )


# =========================================================
# TEST PRINCIPAL
# =========================================================

def main() -> None:

    print("=" * 70)
    print("COMPROBACIÓN DE RETRIEVAL")
    print("=" * 70)
    print()

    errores = 0


    # =====================================================
    # 1. CONEXIÓN CON CHROMADB
    # =====================================================

    print("1. CONEXIÓN CON CHROMADB")
    print("-" * 70)

    if not CHROMA_DIR.exists():

        mostrar_resultado(
            "Existe la base de datos persistente",
            False,
            f"No existe: {CHROMA_DIR}. "
            f"Ejecuta antes src/index.py.",
        )

        return

    if not mostrar_resultado(
        "Existe la base de datos persistente",
        True,
        str(CHROMA_DIR),
    ):
        errores += 1

    print()


    # =====================================================
    # 2. CARGAR PREGUNTAS DE EVALUACIÓN
    # =====================================================

    print("2. PREGUNTAS DE EVALUACIÓN")
    print("-" * 70)

    queries = cargar_eval_queries()

    if not mostrar_resultado(
        "Existen preguntas de evaluación",
        len(queries) > 0,
        f"Preguntas cargadas: {len(queries)}",
    ):
        errores += 1
        return

    print()


    # =====================================================
    # 3. RETRIEVAL PREGUNTA A PREGUNTA (TOP_K de config.py)
    # =====================================================

    print("3. RETRIEVAL POR PREGUNTA")
    print("-" * 70)

    client = crear_cliente_gemini()
    chroma_client = crear_cliente_chroma()

    collection = chroma_client.get_collection(
        name=CHROMA_COLLECTION_NAME
    )

    try:

        resultados_por_query = []

        for query in queries:

            pregunta = query["pregunta"]
            fuentes_esperadas = query.get(
                "fuentes_esperadas",
                [],
            )
            es_respondible = query.get(
                "es_respondible",
                True,
            )

            chunks = buscar_chunks_relevantes(
                pregunta,
                client=client,
                collection=collection,
            )

            distancias = [
                chunk["distance"]
                for chunk in chunks
            ]

            ordenado_correctamente = distancias == sorted(
                distancias
            )

            if not mostrar_resultado(
                f"[{query['id']}] devuelve resultados ordenados: "
                f"{pregunta}",
                len(chunks) > 0 and ordenado_correctamente,
                f"chunks={len(chunks)} "
                f"top_distancia={distancias[0]:.4f}"
                if chunks else "sin resultados",
            ):
                errores += 1

            if es_respondible:

                acierto = alguna_fuente_esperada(
                    chunks,
                    fuentes_esperadas,
                )

                if not mostrar_resultado(
                    f"       fuente esperada entre los recuperados",
                    acierto,
                    f"esperadas={fuentes_esperadas}",
                ):
                    errores += 1

            else:

                # Preguntas fuera de dominio: no exigimos ninguna
                # fuente concreta. Sirven para que generate.py
                # decida más adelante si debe responder "no sé".
                print(
                    f"       fuera de dominio -> "
                    f"top_distancia={distancias[0]:.4f} "
                    f"(criterio de abstención lo aplicará "
                    f"generate.py)"
                )

            resultados_por_query.append(
                {
                    "id": query["id"],
                    "es_respondible": es_respondible,
                    "acierto": (
                        alguna_fuente_esperada(
                            chunks,
                            fuentes_esperadas,
                        )
                        if es_respondible
                        else None
                    ),
                }
            )

        print()


        # =================================================
        # 4. EXPERIMENTO K
        # =================================================

        print("4. EXPERIMENTO K")
        print("-" * 70)

        print(
            "Comparamos la tasa de acierto (fuente esperada "
            "presente en el top_k) para distintos valores de K, "
            "usando solo las preguntas respondibles."
        )
        print()

        queries_respondibles = [
            query
            for query in queries
            if query.get(
                "es_respondible",
                True,
            )
        ]

        for k in (3, 5, 8, 10):

            aciertos = 0

            for query in queries_respondibles:

                chunks = buscar_chunks_relevantes(
                    query["pregunta"],
                    top_k=k,
                    client=client,
                    collection=collection,
                )

                if alguna_fuente_esperada(
                    chunks,
                    query.get(
                        "fuentes_esperadas",
                        [],
                    ),
                ):
                    aciertos += 1

            total = len(queries_respondibles)

            tasa = (
                aciertos / total * 100
                if total
                else 0
            )

            print(
                f"K={k:<3} -> "
                f"aciertos {aciertos}/{total} "
                f"({tasa:.0f}%)"
            )

        print()

    finally:
        client.close()


    # =====================================================
    # 5. RESUMEN
    # =====================================================

    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Colección:            {CHROMA_COLLECTION_NAME}"
    )

    print(
        f"Preguntas evaluadas:  {len(queries)}"
    )

    print()


    # =====================================================
    # 6. RESULTADO FINAL
    # =====================================================

    if errores == 0:

        print(
            "RESULTADO: RETRIEVAL VÁLIDO"
        )

    else:

        print(
            f"RESULTADO: RETRIEVAL CON INCIDENCIAS "
            f"({errores} errores)"
        )


if __name__ == "__main__":
    main()
