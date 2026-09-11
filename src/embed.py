# Se encarga de producir los vectores, embeddings

from google.genai import types

from config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
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