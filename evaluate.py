# Evaluación end-to-end del sistema RAG.
#
# Este script ejecuta:
#
#     pregunta
#         ↓
#     retrieval
#         ↓
#     contexto
#         ↓
#     generación
#         ↓
#     respuesta + fuentes + chunks
#
# No contiene lógica específica de retrieval ni de generación.
# Ambas responsabilidades pertenecen a src/rag.py y a los
# módulos que este orquesta.

import argparse
import json
from pathlib import Path

from config import (
    CHROMA_COLLECTION_NAME,
    EVAL_RAG_JSON,
    TOP_K,
)

from src.gemini_client import crear_cliente_gemini
from src.index import crear_cliente_chroma

from src.generate import ABSTENTION_MESSAGE
from src.rag import responder


# =========================================================
# CARGA DEL DATASET
# =========================================================

def cargar_preguntas(
    ruta_archivo: Path,
) -> list[dict]:
    """
    Carga y valida un dataset de evaluación end-to-end.

    El formato esperado es una lista JSON:

    [
        {
            "id": ...,
            "question": "..."
        }
    ]
    """

    if not ruta_archivo.exists():
        raise FileNotFoundError(
            "No existe el archivo de evaluación: "
            f"{ruta_archivo}"
        )

    with ruta_archivo.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        preguntas = json.load(
            archivo
        )

    if not isinstance(
        preguntas,
        list,
    ):
        raise ValueError(
            "El archivo de evaluación debe contener "
            "una lista JSON."
        )

    ids_vistos = set()

    for posicion, item in enumerate(
        preguntas,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Cada pregunta de evaluación debe ser "
                "un objeto JSON. "
                f"Error en posición {posicion}."
            )

        if "id" not in item:
            raise ValueError(
                "Falta el campo 'id' en la pregunta "
                f"de posición {posicion}."
            )

        query_id = item[
            "id"
        ]

        if query_id in ids_vistos:
            raise ValueError(
                "Se ha encontrado un id duplicado: "
                f"{query_id}"
            )

        ids_vistos.add(
            query_id
        )

        pregunta = item.get(
            "question"
        )

        if (
            not isinstance(
                pregunta,
                str,
            )
            or not pregunta.strip()
        ):
            raise ValueError(
                "La pregunta con id "
                f"{query_id} no contiene un campo "
                "'question' válido."
            )

    return preguntas


# =========================================================
# RUTA DE RESULTADOS
# =========================================================

def crear_ruta_salida(
    ruta_entrada: Path,
    k: int,
) -> Path:
    """
    Genera automáticamente el nombre del archivo de salida.

    Ejemplos:

        eval_rag.json
            -> results_rag_k5.json

        eval_stress.json
            -> results_stress_k5.json
    """

    nombre = ruta_entrada.stem

    if nombre.startswith(
        "eval_"
    ):
        nombre = nombre[
            len("eval_"):
        ]

    return (
        ruta_entrada.parent
        / f"results_{nombre}_k{k}.json"
    )


# =========================================================
# PRESENTACIÓN DE UNA PREGUNTA
# =========================================================

def mostrar_resultado(
    posicion: int,
    total: int,
    pregunta: str,
    resultado: dict,
) -> None:
    """
    Muestra en terminal un resultado individual de forma
    legible.
    """

    print()
    print(
        "=" * 80
    )

    print(
        f"PREGUNTA {posicion}/{total}"
    )

    print(
        "=" * 80
    )

    print(
        pregunta
    )

    print()
    print(
        "RESPUESTA:"
    )

    print(
        resultado["answer"]
    )

    print()
    print(
        "FUENTES:"
    )

    fuentes = resultado.get(
        "sources",
        [],
    )

    if fuentes:

        for fuente in fuentes:

            source = fuente.get(
                "source"
            )

            print(
                f"- {source}"
            )

    else:

        print(
            "- Ninguna"
        )

    print()
    print(
        "CHUNKS RECUPERADOS:"
    )

    chunks = resultado.get(
        "chunks",
        [],
    )

    if not chunks:

        print(
            "- Ninguno"
        )

        return

    for indice, chunk in enumerate(
        chunks,
        start=1,
    ):

        metadata = (
            chunk.get(
                "metadata",
                {},
            )
            or {}
        )

        print()
        print(
            f"  CHUNK {indice}"
        )

        print(
            "  "
            + "-" * 50
        )

        print(
            "  Distancia: "
            f"{chunk.get('distance', 'N/A')}"
        )

        print(
            "  Fuente: "
            f"{metadata.get('source', 'N/A')}"
        )

        print(
            "  Tipo: "
            f"{metadata.get('document_type', 'N/A')}"
        )

        print(
            "  Distrito: "
            f"{metadata.get('district', 'N/A')}"
        )


# =========================================================
# EVALUACIÓN
# =========================================================

def evaluar_preguntas(
    preguntas: list[dict],
    k: int,
    client,
    collection,
) -> list[dict]:
    """
    Ejecuta el sistema RAG completo para todas las preguntas.

    El mismo cliente Gemini y la misma colección ChromaDB se
    reutilizan durante toda la evaluación.
    """

    resultados = []

    total = len(
        preguntas
    )

    for posicion, item in enumerate(
        preguntas,
        start=1,
    ):

        pregunta = item[
            "question"
        ].strip()

        query_id = item[
            "id"
        ]

        try:

            resultado = responder(
                pregunta=pregunta,
                k=k,
                client=client,
                collection=collection,
            )

            respuesta = resultado[
                "answer"
            ]

            abstencion = (
                respuesta.strip()
                == ABSTENTION_MESSAGE
            )

            mostrar_resultado(
                posicion=posicion,
                total=total,
                pregunta=pregunta,
                resultado=resultado,
            )

            resultados.append(
                {
                    "id": query_id,
                    "question": pregunta,
                    "answer": respuesta,
                    "abstained": abstencion,
                    "sources": resultado[
                        "sources"
                    ],
                    "chunks": resultado[
                        "chunks"
                    ],
                }
            )

        except Exception as error:

            print()
            print(
                "=" * 80
            )

            print(
                f"PREGUNTA {posicion}/{total}"
            )

            print(
                "=" * 80
            )

            print(
                pregunta
            )

            print()
            print(
                "ERROR:"
            )

            print(
                str(error)
            )

            resultados.append(
                {
                    "id": query_id,
                    "question": pregunta,
                    "error": str(error),
                }
            )

    return resultados


# =========================================================
# RESUMEN
# =========================================================

def mostrar_resumen(
    resultados: list[dict],
) -> None:
    """
    Muestra un resumen técnico de la ejecución.

    No intenta determinar automáticamente si las respuestas
    son correctas, ya que eso requiere información esperada
    explícita en el dataset.
    """

    total = len(
        resultados
    )

    errores = sum(
        1
        for resultado in resultados
        if "error" in resultado
    )

    completadas = (
        total - errores
    )

    abstenciones = sum(
        1
        for resultado in resultados
        if resultado.get(
            "abstained",
            False,
        )
    )

    print()
    print(
        "=" * 80
    )

    print(
        "RESUMEN"
    )

    print(
        "=" * 80
    )

    print(
        f"Preguntas totales: "
        f"{total}"
    )

    print(
        f"Ejecuciones completadas: "
        f"{completadas}"
    )

    print(
        f"Errores: "
        f"{errores}"
    )

    print(
        f"Abstenciones: "
        f"{abstenciones}"
    )


# =========================================================
# GUARDADO
# =========================================================

def guardar_resultados(
    resultados: list[dict],
    ruta_salida: Path,
) -> None:
    """
    Guarda los resultados completos de la evaluación.
    """

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with ruta_salida.open(
        "w",
        encoding="utf-8",
    ) as archivo:

        json.dump(
            resultados,
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Resultados guardados en: "
        f"{ruta_salida}"
    )


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
        "--file",
        type=str,
        default=str(
            EVAL_RAG_JSON
        ),
        help=(
            "Archivo JSON con las preguntas "
            "de evaluación."
        ),
    )

    parser.add_argument(
        "--k",
        type=int,
        default=TOP_K,
        help=(
            "Número de chunks recuperados."
        ),
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "Ruta opcional para guardar los resultados. "
            "Si no se especifica, se genera automáticamente."
        ),
    )

    args = parser.parse_args()

    if args.k <= 0:
        raise ValueError(
            "k debe ser mayor que 0."
        )

    ruta_entrada = Path(
        args.file
    ).resolve()

    if args.output:

        ruta_salida = Path(
            args.output
        ).resolve()

    else:

        ruta_salida = crear_ruta_salida(
            ruta_entrada,
            args.k,
        )

    # -----------------------------------------------------
    # DATASET
    # -----------------------------------------------------

    preguntas = cargar_preguntas(
        ruta_entrada
    )

    print(
        "=" * 80
    )

    print(
        "EVALUACIÓN END-TO-END DEL SISTEMA RAG"
    )

    print(
        "=" * 80
    )

    print(
        f"Archivo: "
        f"{ruta_entrada}"
    )

    print(
        f"Número de preguntas: "
        f"{len(preguntas)}"
    )

    print(
        f"K: "
        f"{args.k}"
    )

    # -----------------------------------------------------
    # RECURSOS COMPARTIDOS
    # -----------------------------------------------------

    client = crear_cliente_gemini()

    chroma_client = (
        crear_cliente_chroma()
    )

    collection = (
        chroma_client.get_collection(
            name=CHROMA_COLLECTION_NAME
        )
    )

    try:

        resultados = evaluar_preguntas(
            preguntas=preguntas,
            k=args.k,
            client=client,
            collection=collection,
        )

    finally:

        client.close()

    # -----------------------------------------------------
    # RESULTADOS
    # -----------------------------------------------------

    mostrar_resumen(
        resultados
    )

    guardar_resultados(
        resultados=resultados,
        ruta_salida=ruta_salida,
    )


if __name__ == "__main__":
    main()