import argparse
import json
import sys
from pathlib import Path


# =========================================================
# PATH DEL PROYECTO
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from config import (
    CHROMA_COLLECTION_NAME,
    EVAL_QUERIES_JSON,
    EVALUATION_RESULTS_DIR,
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
    ruta_archivo: Path = EVAL_QUERIES_JSON,
) -> list[dict]:
    """
    Carga y valida el dataset canónico de evaluación.

    El archivo contiene preguntas utilizadas tanto para
    evaluar retrieval como el flujo RAG completo.
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
        payload = json.load(
            archivo
        )

    if not isinstance(payload, dict):
        raise ValueError(
            "El dataset de evaluación debe ser "
            "un objeto JSON."
        )

    preguntas = payload.get(
        "queries"
    )

    if not isinstance(preguntas, list):
        raise ValueError(
            "El dataset debe contener una lista "
            "en la clave 'queries'."
        )

    total_declarado = payload.get(
        "total_queries"
    )

    if (
        total_declarado is not None
        and total_declarado != len(preguntas)
    ):
        raise ValueError(
            "total_queries no coincide con el "
            "número real de preguntas."
        )

    ids_vistos = set()

    for posicion, item in enumerate(
        preguntas,
        start=1,
    ):

        if not isinstance(item, dict):
            raise ValueError(
                "Cada consulta debe ser un objeto JSON. "
                f"Error en posición {posicion}."
            )

        query_id = item.get(
            "id"
        )

        if query_id is None:
            raise ValueError(
                f"Falta 'id' en la posición {posicion}."
            )

        if query_id in ids_vistos:
            raise ValueError(
                f"ID duplicado: {query_id}"
            )

        ids_vistos.add(
            query_id
        )

        pregunta = item.get(
            "pregunta"
        )

        if (
            not isinstance(pregunta, str)
            or not pregunta.strip()
        ):
            raise ValueError(
                f"La consulta {query_id} no contiene "
                "una 'pregunta' válida."
            )

        if not isinstance(
            item.get("es_respondible"),
            bool,
        ):
            raise ValueError(
                f"La consulta {query_id} no contiene "
                "'es_respondible' válido."
            )

        fuentes = item.get(
            "fuentes_esperadas"
        )

        if not isinstance(fuentes, list):
            raise ValueError(
                f"La consulta {query_id} no contiene "
                "'fuentes_esperadas' válido."
            )

    return preguntas


# =========================================================
# RUTA DE RESULTADOS
# =========================================================

def crear_ruta_salida(
    k: int,
) -> Path:
    """
    Devuelve la ruta estándar para los resultados
    de evaluación.
    """

    return (
        EVALUATION_RESULTS_DIR
        / f"results_k{k}.json"
    )


# =========================================================
# COMPROBACIÓN DE EVIDENCIA
# =========================================================

def comprobar_fuentes(
    fuentes_recuperadas: list[dict],
    fuentes_esperadas: list[str],
) -> bool | None:
    """
    Comprueba si al menos una de las fuentes esperadas
    aparece entre las fuentes recuperadas.

    Para preguntas fuera de dominio no aplica.
    """

    if not fuentes_esperadas:
        return None

    nombres_recuperados = {
        fuente.get("source")
        for fuente in fuentes_recuperadas
        if fuente.get("source")
    }

    return any(
        fuente in nombres_recuperados
        for fuente in fuentes_esperadas
    )


# =========================================================
# PRESENTACIÓN
# =========================================================

def mostrar_resultado(
    posicion: int,
    total: int,
    item: dict,
    resultado: dict,
    retrieval_hit: bool | None,
    abstencion_correcta: bool,
) -> None:

    print()
    print("=" * 80)
    print(
        f"PREGUNTA {posicion}/{total} "
        f"[ID {item['id']}]"
    )
    print("=" * 80)

    print(
        item["pregunta"]
    )

    print()
    print(
        f"Respondible esperada: "
        f"{item['es_respondible']}"
    )

    print()
    print("RESPUESTA:")
    print(
        resultado["answer"]
    )

    print()
    print("FUENTES:")

    fuentes = resultado.get(
        "sources",
        [],
    )

    if fuentes:
        for fuente in fuentes:
            print(
                f"- {fuente.get('source')}"
            )
    else:
        print("- Ninguna")

    print()
    print(
        "Comportamiento de abstención correcto: "
        f"{abstencion_correcta}"
    )

    if retrieval_hit is not None:
        print(
            "Fuente esperada recuperada: "
            f"{retrieval_hit}"
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
    Ejecuta el RAG completo sobre todas las preguntas
    del dataset canónico.
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
            "pregunta"
        ].strip()

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

            abstained = (
                respuesta.strip()
                == ABSTENTION_MESSAGE
            )

            abstencion_esperada = (
                not item["es_respondible"]
            )

            abstencion_correcta = (
                abstained
                == abstencion_esperada
            )

            retrieval_hit = comprobar_fuentes(
                resultado.get(
                    "sources",
                    [],
                ),
                item[
                    "fuentes_esperadas"
                ],
            )

            mostrar_resultado(
                posicion=posicion,
                total=total,
                item=item,
                resultado=resultado,
                retrieval_hit=retrieval_hit,
                abstencion_correcta=abstencion_correcta,
            )

            resultados.append(
                {
                    "id": item["id"],
                    "categoria": item["categoria"],
                    "pregunta": pregunta,
                    "es_respondible": item[
                        "es_respondible"
                    ],
                    "fuentes_esperadas": item[
                        "fuentes_esperadas"
                    ],
                    "answer": respuesta,
                    "abstained": abstained,
                    "abstention_expected": (
                        abstencion_esperada
                    ),
                    "abstention_correct": (
                        abstencion_correcta
                    ),
                    "retrieval_hit": (
                        retrieval_hit
                    ),
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
            print("=" * 80)
            print(
                f"PREGUNTA {posicion}/{total} "
                f"[ID {item['id']}]"
            )
            print("=" * 80)

            print(
                pregunta
            )

            print()
            print(
                f"ERROR: {error}"
            )

            resultados.append(
                {
                    "id": item["id"],
                    "categoria": item["categoria"],
                    "pregunta": pregunta,
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

    total = len(
        resultados
    )

    errores = sum(
        "error" in resultado
        for resultado in resultados
    )

    completadas = (
        total - errores
    )

    respondibles = [
        resultado
        for resultado in resultados
        if (
            "error" not in resultado
            and resultado.get(
                "es_respondible"
            )
        )
    ]

    fuera_dominio = [
        resultado
        for resultado in resultados
        if (
            "error" not in resultado
            and not resultado.get(
                "es_respondible"
            )
        )
    ]

    retrieval_hits = sum(
        resultado.get(
            "retrieval_hit"
        ) is True
        for resultado in respondibles
    )

    abstenciones_correctas = sum(
        resultado.get(
            "abstention_correct"
        ) is True
        for resultado in fuera_dominio
    )

    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)

    print(
        f"Preguntas totales:       {total}"
    )

    print(
        f"Ejecuciones completadas: {completadas}"
    )

    print(
        f"Errores:                 {errores}"
    )

    print(
        f"Preguntas respondibles:  {len(respondibles)}"
    )

    print(
        f"Fuentes recuperadas:     "
        f"{retrieval_hits}/{len(respondibles)}"
    )

    print(
        f"Fuera de dominio:        "
        f"{len(fuera_dominio)}"
    )

    print(
        f"Abstenciones correctas:  "
        f"{abstenciones_correctas}/"
        f"{len(fuera_dominio)}"
    )


# =========================================================
# GUARDADO
# =========================================================

def guardar_resultados(
    resultados: list[dict],
    ruta_salida: Path,
) -> None:

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
            EVAL_QUERIES_JSON
        ),
        help=(
            "Dataset JSON de evaluación."
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
            "Ruta opcional para los resultados."
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
            args.k
        )

    preguntas = cargar_preguntas(
        ruta_entrada
    )

    print("=" * 80)
    print(
        "EVALUACIÓN END-TO-END DEL SISTEMA RAG"
    )
    print("=" * 80)

    print(
        f"Dataset: {ruta_entrada}"
    )

    print(
        f"Preguntas: {len(preguntas)}"
    )

    print(
        f"K: {args.k}"
    )

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

    mostrar_resumen(
        resultados
    )

    guardar_resultados(
        resultados=resultados,
        ruta_salida=ruta_salida,
    )


if __name__ == "__main__":
    main()