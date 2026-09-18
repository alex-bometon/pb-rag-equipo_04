# Se encarga de recuperar, para una pregunta dada, los chunks
# más relevantes almacenados en ChromaDB.

from google.genai import types

from config import (
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    TOP_K,
)

from src.gemini_client import crear_cliente_gemini
from src.index import crear_cliente_chroma


# =========================================================
# EMBEDDING DE LA PREGUNTA
# =========================================================

def embeddear_pregunta(
    client,
    pregunta: str,
) -> list[float]:
    """
    Genera el embedding de la pregunta del usuario.

    Se utiliza el mismo modelo y las mismas dimensiones que
    en embed.py, para que la pregunta y los chunks del corpus
    vivan en el mismo espacio vectorial y sean comparables
    mediante similitud coseno.
    """

    resultado = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=pregunta,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS
        ),
    )

    if not resultado.embeddings:
        raise ValueError(
            "Gemini no ha devuelto ningún embedding "
            "para la pregunta."
        )

    vector = resultado.embeddings[0].values

    if vector is None:
        raise ValueError(
            "El embedding de la pregunta no contiene valores."
        )

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            "Dimensión inesperada del embedding: "
            f"{len(vector)}. "
            f"Se esperaban {EMBEDDING_DIMENSIONS}."
        )

    return vector


# =========================================================
# BÚSQUEDA EN CHROMADB
# =========================================================

def buscar_chunks_relevantes(
    pregunta: str,
    top_k: int = TOP_K,
    client=None,
    collection=None,
) -> list[dict]:
    """
    Recupera los `top_k` chunks más relevantes para una
    pregunta.

    Flujo:

        pregunta
            -> embedding de la pregunta
            -> búsqueda por similitud en ChromaDB
            -> lista de chunks con texto, metadata y distancia

    Parameters
    ----------
    pregunta : str
        Pregunta del usuario, en lenguaje natural.
    top_k : int
        Número de chunks a recuperar. Por defecto, TOP_K
        de config.py.
    client, collection : opcional
        Permiten reutilizar un cliente de Gemini y una
        colección de ChromaDB ya abiertos (por ejemplo,
        desde rag.py o desde los tests), en vez de abrir
        una conexión nueva en cada llamada.

    Returns
    -------
    list[dict]
        Cada elemento contiene:
            text, distance, metadata
        ordenados del más al menos relevante (menor
        distancia = más relevante).
    """

    cliente_propio = client is None
    coleccion_propia = collection is None

    if cliente_propio:
        client = crear_cliente_gemini()

    if coleccion_propia:
        chroma_client = crear_cliente_chroma()

        collection = chroma_client.get_collection(
            name=CHROMA_COLLECTION_NAME
        )

    try:
        vector_pregunta = embeddear_pregunta(
            client,
            pregunta,
        )

        resultado = collection.query(
            query_embeddings=[vector_pregunta],
            n_results=top_k,
        )

    finally:
        if cliente_propio:
            client.close()

    documentos = resultado["documents"][0]
    metadatas = resultado["metadatas"][0]
    distancias = resultado["distances"][0]

    chunks = []

    for texto, metadata, distancia in zip(
        documentos,
        metadatas,
        distancias,
    ):

        chunks.append(
            {
                "text": texto,
                "distance": distancia,
                "metadata": metadata,
            }
        )

    return chunks


# =========================================================
# EVALUACIÓN DE FUENTES
# =========================================================

def resumir_fuentes(
    chunks: list[dict],
) -> list[dict]:
    """
    Extrae, para un conjunto de chunks recuperados, un
    resumen de las fuentes utilizadas: de qué documento
    procede cada uno y a qué distancia quedó de la pregunta.

    Sirve para:
        - poder citar las fuentes en la respuesta final
          (generate.py / rag.py las necesitará);
        - evaluar si el retrieval está trayendo documentos
          del dominio correcto (ver tests/retrieval).
    """

    fuentes = []

    for chunk in chunks:

        metadata = chunk["metadata"]

        fuentes.append(
            {
                "source": metadata.get("source"),
                "document_type": metadata.get("document_type"),
                "district": metadata.get("district"),
                "distance": chunk["distance"],
            }
        )

    return fuentes


# =========================================================
# EJECUCIÓN MANUAL / PRUEBA RÁPIDA
# =========================================================

def ejecutar_retrieval(
    pregunta: str,
    top_k: int = TOP_K,
) -> list[dict]:
    """
    Ejecuta el retrieval completo para una pregunta y
    muestra el resultado por pantalla.

    Pensado para probar retrieve.py de forma manual, sin
    depender todavía de generate.py / rag.py.
    """

    print(f"Pregunta: {pregunta}")
    print(f"TOP_K: {top_k}")
    print()

    chunks = buscar_chunks_relevantes(
        pregunta,
        top_k=top_k,
    )

    for posicion, chunk in enumerate(chunks, start=1):

        metadata = chunk["metadata"]

        print(
            f"[{posicion}] distancia={chunk['distance']:.4f} "
            f"fuente={metadata.get('source')}"
        )

        print(f"    {chunk['text'][:200]}...")
        print()

    return chunks


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":
    ejecutar_retrieval(
        "¿Dónde puedo tirar aceite vegetal usado?"
    )
