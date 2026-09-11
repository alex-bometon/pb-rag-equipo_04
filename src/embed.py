# Se encarga de producir los vectores, embeddings

from google.genai import types

from config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    EMBED_BATCH_SIZE
)
from src.gemini_client import crear_cliente_gemini


# =========================================================
# PREPARACIÓN DEL TEXTO
# =========================================================

def preparar_documento_embedding(
    chunk: dict,
) -> str:
    """
    Prepara un chunk para generar su embedding.

    Gemini Embedding 2 recomienda representar los
    documentos destinados a retrieval con la forma:

        title: {title} | text: {content}

    Si el documento no dispone de título, se utiliza
    'none', tal como indica la documentación de Google.
    """

    texto = chunk["text"]

    metadata = chunk.get(
        "metadata",
        {},
    )

    titulo = metadata.get(
        "title"
    )

    if not titulo:
        titulo = "none"

    return (
        f"title: {titulo} | "
        f"text: {texto}"
    )


# =========================================================
# GENERACIÓN DE UN EMBEDDING
# =========================================================

def embeddear_documento(
    client,
    chunk: dict,
) -> list[float]:
    """
    Genera el embedding de un único chunk.

    Devuelve solamente el vector numérico.
    """

    contenido = preparar_documento_embedding(
        chunk
    )

    resultado = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=contenido,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS
        ),
    )

    if not resultado.embeddings:
        raise ValueError(
            "Gemini no ha devuelto ningún embedding."
        )

    vector = resultado.embeddings[0].values

    if vector is None:
        raise ValueError(
            "El embedding recibido no contiene valores."
        )

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            "Dimensión inesperada del embedding: "
            f"{len(vector)}. "
            f"Se esperaban {EMBEDDING_DIMENSIONS}."
        )

    return vector


# =========================================================
# GENERACIÓN DE EMBEDDINGS POR LOTES
# =========================================================

def embeddear_documentos(
    client,
    chunks: list[dict],
) -> list[list[float]]:
    """
    Genera los embeddings de varios chunks.

    Los chunks se procesan en grupos definidos por
    EMBED_BATCH_SIZE para evitar enviar todo el corpus
    en una única llamada.

    Mantiene el mismo orden de entrada:

        chunks[0] -> embeddings[0]
        chunks[1] -> embeddings[1]
        ...

    Devuelve una lista de vectores.
    """

    embeddings = []

    for inicio in range(
        0,
        len(chunks),
        EMBED_BATCH_SIZE,
    ):

        fin = inicio + EMBED_BATCH_SIZE

        lote = chunks[inicio:fin]

        contenidos = [
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=preparar_documento_embedding(chunk)
                    )
                ]
            )
            for chunk in lote
        ]

        resultado = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=contenidos,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSIONS
            ),
        )

        # Comprobamos que Gemini devuelve exactamente
        # un embedding por cada chunk enviado.
        if len(resultado.embeddings) != len(lote):
            raise ValueError(
                "Número de embeddings inesperado. "
                f"Se enviaron {len(lote)} chunks "
                f"y se recibieron "
                f"{len(resultado.embeddings)} embeddings."
            )

        for embedding in resultado.embeddings:

            vector = embedding.values

            if vector is None:
                raise ValueError(
                    "Uno de los embeddings no contiene valores."
                )

            if len(vector) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    "Dimensión inesperada del embedding: "
                    f"{len(vector)}. "
                    f"Se esperaban {EMBEDDING_DIMENSIONS}."
                )

            embeddings.append(
                vector
            )

    return embeddings