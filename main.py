import argparse

from src.rag import responder


def main():
    parser = argparse.ArgumentParser(
        description="Sistema RAG sobre puntos limpios de Madrid."
    )

    parser.add_argument(
        "--ask",
        type=str,
        help="Pregunta que quieres hacer al sistema RAG.",
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Número de chunks recuperados.",
    )

    args = parser.parse_args()

    if not args.ask:
        parser.error(
            "Debes indicar una pregunta usando --ask."
        )

    resultado = responder(
        pregunta=args.ask,
        k=args.k,
    )

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
            print(
                f"- {fuente.get('source')} "
                f"({fuente.get('path')})"
            )
    else:
        print("No se han recuperado fuentes.")


if __name__ == "__main__":
    main()