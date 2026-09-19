from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.load import cargar_corpus
from src.clean import limpiar_corpus
from src.chunk import (
    _chunk_documentacion,
    _chunk_documento_estructurado,
)


CONFIGURACIONES = [
    {
        "nombre": "A",
        "chunk_size": 500,
        "chunk_overlap": 50,
    },
    {
        "nombre": "B",
        "chunk_size": 1000,
        "chunk_overlap": 100,
    },
    {
        "nombre": "C",
        "chunk_size": 1500,
        "chunk_overlap": 150,
    },
]


def generar_chunks_experimento(documentos, chunk_size, chunk_overlap):
    """
    Genera los chunks usando una configuración concreta
    sin modificar config.py ni los chunks actuales.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
        length_function=len,
    )

    chunks = []

    for documento in documentos:

        tipo = documento["metadata"].get(
            "document_type"
        )

        if tipo == "documentacion_municipal":

            chunks_documento = _chunk_documentacion(
                documento,
                splitter,
            )

        else:

            chunks_documento = _chunk_documento_estructurado(
                documento
            )

        chunks.extend(chunks_documento)

    return chunks


def main():

    print("=" * 80)
    print("EXPERIMENTO DE CHUNKING")
    print("=" * 80)

    corpus = cargar_corpus()
    documentos = limpiar_corpus(corpus)

    print(f"\nDocumentos después de limpieza: {len(documentos)}")

    for config in CONFIGURACIONES:

        chunks = generar_chunks_experimento(
            documentos=documentos,
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
        )

        tamanos = [
            len(chunk["text"])
            for chunk in chunks
        ]

        media = sum(tamanos) / len(tamanos)
        minimo = min(tamanos)
        maximo = max(tamanos)

        print("\n" + "-" * 80)
        print(f"CONFIGURACIÓN {config['nombre']}")
        print("-" * 80)

        print(
            f"Chunk size: {config['chunk_size']}"
        )

        print(
            f"Chunk overlap: {config['chunk_overlap']}"
        )

        print(
            f"Número total de chunks: {len(chunks)}"
        )

        print(
            f"Tamaño medio: {media:.1f} caracteres"
        )

        print(
            f"Tamaño mínimo: {minimo} caracteres"
        )

        print(
            f"Tamaño máximo: {maximo} caracteres"
        )


if __name__ == "__main__":
    main()