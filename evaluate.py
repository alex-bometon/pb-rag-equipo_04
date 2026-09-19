import argparse
import json
from pathlib import Path

from src.rag import responder


def cargar_preguntas(ruta_archivo):
    """
    Carga las preguntas de evaluación desde un archivo JSON.
    """
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluar_preguntas(preguntas, k):
    """
    Ejecuta el sistema RAG para cada pregunta.
    """
    resultados = []

    for i, item in enumerate(preguntas, start=1):
        pregunta = item["question"]

        print("\n" + "=" * 80)
        print(f"PREGUNTA {i}/{len(preguntas)}")
        print("=" * 80)
        print(pregunta)

        try:
            resultado = responder(
                pregunta=pregunta,
                k=k
            )

            print("\nRESPUESTA:")
            print(resultado["answer"])

            print("\nFUENTES:")
            if resultado["sources"]:
                for fuente in resultado["sources"]:
                    print(f"- {fuente}")
            else:
                print("- Ninguna")

            print("\nCHUNKS RECUPERADOS:")

            for j, chunk in enumerate(resultado["chunks"], start=1):
                print(f"\n  CHUNK {j}")
                print(f"  Score: {chunk.get('score', 'N/A')}")
                print(f"  Distance: {chunk.get('distance', 'N/A')}")
                print(f"  Lexical score: {chunk.get('lexical_score', 'N/A')}")

                metadata = chunk.get("metadata", {})

                print(f"  Fuente: {metadata.get('source', 'N/A')}")
                print(
                    f"  Tipo: "
                    f"{metadata.get('document_type', 'N/A')}"
                )
                print(
                    f"  Distrito: "
                    f"{metadata.get('district', 'N/A')}"
                )

            resultados.append(
                {
                    "id": item.get("id"),
                    "question": pregunta,
                    "answer": resultado["answer"],
                    "sources": resultado["sources"],
                    "chunks": resultado["chunks"],
                }
            )

        except Exception as e:
            print("\nERROR:")
            print(str(e))

            resultados.append(
                {
                    "id": item.get("id"),
                    "question": pregunta,
                    "error": str(e),
                }
            )

    return resultados


def guardar_resultados(resultados, k):
    """
    Guarda los resultados de la evaluación en un archivo JSON.
    """
    ruta_salida = Path(f"queries/results_stress_k{k}.json")

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(
            resultados,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 80)
    print("EVALUACIÓN FINALIZADA")
    print("=" * 80)
    print(f"Resultados guardados en: {ruta_salida}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluación del sistema RAG."
    )

    parser.add_argument(
        "--file",
        type=str,
        default="queries/eval_queries.json",
        help="Archivo JSON con las preguntas de evaluación."
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Número de chunks recuperados."
    )

    args = parser.parse_args()

    preguntas = cargar_preguntas(args.file)

    print("=" * 80)
    print("EVALUACIÓN DEL SISTEMA RAG")
    print("=" * 80)
    print(f"Archivo: {args.file}")
    print(f"Número de preguntas: {len(preguntas)}")
    print(f"K: {args.k}")

    resultados = evaluar_preguntas(
        preguntas=preguntas,
        k=args.k
    )

    guardar_resultados(
        resultados=resultados,
        k=args.k
    )


if __name__ == "__main__":
    main()