import argparse

from config import TOP_K
from src.index import ejecutar_indexacion
from src.retrieve import ejecutar_retrieval
from src.rag import responder


def main():
    parser = argparse.ArgumentParser(
        description=(
            "==========\n"
            "ReciclaTIA\n"
            "==========\n"
            "Sistema RAG sobre gestión de residuos "
            "de Madrid."
        )
    )

    acciones = parser.add_mutually_exclusive_group(required=True)

    acciones.add_argument(
        "--index",
        action="store_true",
        help=(
            "Construye el índice persistente de ChromaDB "
            "a partir de los embeddings."
        ),
    )

    acciones.add_argument(
        "--query",
        type=str,
        help=(
            "Realiza únicamente retrieval y muestra "
            "los chunks recuperados."
        ),
    )

    acciones.add_argument(
        "--ask",
        type=str,
        help=(
            "Realiza una consulta RAG completa y muestra "
            "la respuesta junto con sus fuentes."
        ),
    )

    parser.add_argument(
        "--k",
        type=int,
        default=TOP_K,
        help=(
            "Número de chunks recuperados "
            f"(por defecto: {TOP_K})."
        ),
    )

    args = parser.parse_args()

    if args.k <= 0:
        parser.error("--k debe ser mayor que 0.")

    # =====================================================
    # INDEXACIÓN
    # =====================================================

    if args.index:
        ejecutar_indexacion()
        return

    # =====================================================
    # RETRIEVAL
    # =====================================================

    if args.query:
        ejecutar_retrieval(pregunta=args.query, top_k=args.k)
        return

    # =====================================================
    # RAG COMPLETO
    # =====================================================

    resultado = responder(pregunta=args.ask, k=args.k)

    print()
    print("=" * 70)
    print("RESPUESTA")
    print("=" * 70)
    print(resultado["answer"])

    print()
    print("=" * 70)
    print("FUENTES")
    print("=" * 70)

    if resultado["sources"]:
        for fuente in resultado["sources"]:
            print(f"- {fuente.get('source')}")
    else:
        print("No se han recuperado fuentes.")

    print()
    print("=" * 70)
    print("CONTEXTO RECUPERADO")
    print("=" * 70)

    if resultado["chunks"]:
        for i, chunk in enumerate(resultado["chunks"], start=1):
            print()
            print(f"[{i}]")

            metadata = chunk.get("metadata", {})

            print("Fuente:", metadata.get("source"))
            print(chunk.get("text", ""))
    else:
        print("No se han recuperado chunks.")


if __name__ == "__main__":
    main()