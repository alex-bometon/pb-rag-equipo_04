import re
import unicodedata

import chromadb
from google.genai import types

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)

from src.gemini_client import crear_cliente_gemini


DEFAULT_CANDIDATE_K = 50


def crear_cliente_chroma():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def obtener_coleccion():
    client = crear_cliente_chroma()
    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    return collection


def preparar_query(pregunta: str) -> str:
    return (
        f"task: question answering | "
        f"query: {pregunta}"
    )


def generar_embedding_query(pregunta: str) -> list[float]:
    client = crear_cliente_gemini()

    try:
        contenido = preparar_query(pregunta)

        resultado = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=contenido,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSIONS
            ),
        )
    finally:
        client.close()

    if not resultado.embeddings:
        raise ValueError(
            "Gemini no ha devuelto ningún embedding para la pregunta."
        )

    vector = resultado.embeddings[0].values

    if vector is None:
        raise ValueError(
            "El embedding de la pregunta no contiene valores."
        )

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            "Dimensión inesperada del embedding de la pregunta: "
            f"{len(vector)}. "
            f"Se esperaban {EMBEDDING_DIMENSIONS}."
        )

    return vector


def normalizar_texto(texto: str) -> str:
    """
    Convierte el texto a minúsculas, elimina acentos
    y normaliza espacios.
    """
    texto = str(texto).lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def extraer_palabras_importantes(texto: str) -> set[str]:
    """
    Extrae palabras relevantes de la consulta eliminando
    palabras muy comunes.
    """
    stopwords = {
        "a",
        "al",
        "con",
        "como",
        "cual",
        "cuales",
        "de",
        "del",
        "donde",
        "el",
        "en",
        "es",
        "hay",
        "la",
        "las",
        "lo",
        "los",
        "me",
        "para",
        "por",
        "que",
        "se",
        "un",
        "una",
        "y",
    }

    palabras = normalizar_texto(texto).split()

    return {
        palabra
        for palabra in palabras
        if palabra not in stopwords and len(palabra) > 2
    }


def construir_texto_busqueda(
    documento: str,
    metadata: dict,
) -> str:
    """
    Construye el texto que utilizamos para el reranking.

    Además del contenido del chunk, incluimos algunos campos
    de metadata que pueden ser importantes para distinguir
    documentos similares.
    """
    campos_metadata = [
        metadata.get("source", ""),
        metadata.get("document_type", ""),
        metadata.get("district", ""),
        metadata.get("neighborhood", ""),
    ]

    return " ".join(
        [documento] + [str(campo) for campo in campos_metadata]
    )


def calcular_coincidencia_lexica(
    pregunta: str,
    documento: str,
    metadata: dict,
) -> float:
    """
    Calcula qué proporción de las palabras importantes
    de la pregunta aparecen en el documento o metadata.
    """
    palabras_pregunta = extraer_palabras_importantes(pregunta)

    if not palabras_pregunta:
        return 0.0

    texto_busqueda = construir_texto_busqueda(
        documento,
        metadata,
    )

    texto_normalizado = normalizar_texto(texto_busqueda)

    palabras_documento = set(texto_normalizado.split())

    coincidencias = palabras_pregunta.intersection(
        palabras_documento
    )

    return len(coincidencias) / len(palabras_pregunta)


def calcular_score(
    distancia: float,
    coincidencia_lexica: float,
) -> float:
    """
    Combina similitud semántica y coincidencia textual.

    Chroma devuelve distancia coseno:
        menor distancia = mayor similitud.

    Convertimos la distancia en una similitud aproximada.
    """
    similitud_semantica = 1 - distancia

    return (
        0.70 * similitud_semantica
        + 0.30 * coincidencia_lexica
    )


def recuperar_chunks(
    pregunta: str,
    k: int = 5,
) -> list[dict]:

    if not pregunta or not pregunta.strip():
        raise ValueError(
            "La pregunta no puede estar vacía."
        )

    if k <= 0:
        raise ValueError(
            "k debe ser mayor que 0."
        )

    query_embedding = generar_embedding_query(pregunta)

    collection = obtener_coleccion()

    total_documentos = collection.count()

    if total_documentos == 0:
        raise ValueError(
            "La colección de ChromaDB está vacía."
        )

    # Recuperamos más candidatos de los que finalmente
    # vamos a devolver para poder reordenarlos.
    candidate_k = min(
        max(k * 10, DEFAULT_CANDIDATE_K),
        total_documentos,
    )

    resultados = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documentos = resultados.get(
        "documents",
        [[]],
    )[0]

    metadatas = resultados.get(
        "metadatas",
        [[]],
    )[0]

    distancias = resultados.get(
        "distances",
        [[]],
    )[0]

    candidatos = []

    for documento, metadata, distancia in zip(
        documentos,
        metadatas,
        distancias,
    ):
        metadata = metadata or {}

        coincidencia_lexica = calcular_coincidencia_lexica(
            pregunta,
            documento,
            metadata,
        )

        score = calcular_score(
            distancia,
            coincidencia_lexica,
        )

        candidatos.append(
            {
                "text": documento,
                "metadata": metadata,
                "distance": distancia,
                "lexical_score": coincidencia_lexica,
                "score": score,
            }
        )

    # Reordenamos de mayor score a menor.
    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidatos[:k]


if __name__ == "__main__":

    pregunta = (
        "¿Dónde hay un punto limpio fijo "
        "en el distrito de Arganzuela?"
    )

    resultados = recuperar_chunks(
        pregunta,
        k=5,
    )

    print()
    print("RESULTADOS DEL RETRIEVAL")
    print("=" * 70)

    for i, chunk in enumerate(
        resultados,
        start=1,
    ):
        metadata = chunk["metadata"]

        print()
        print(f"CHUNK {i}")
        print("-" * 70)
        print(
            f"Score final: {chunk['score']:.4f}"
        )
        print(
            f"Distancia semántica: "
            f"{chunk['distance']:.4f}"
        )
        print(
            f"Coincidencia léxica: "
            f"{chunk['lexical_score']:.4f}"
        )
        print(
            f"Fuente: "
            f"{metadata.get('source')}"
        )
        print(
            f"Tipo: "
            f"{metadata.get('document_type')}"
        )
        print(
            f"Distrito: "
            f"{metadata.get('district')}"
        )
        print(
            f"Texto: "
            f"{chunk['text'][:500]}"
        )
