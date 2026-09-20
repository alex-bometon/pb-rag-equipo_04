# Se encarga de recuperar, para una pregunta dada, los chunks
# más relevantes almacenados en ChromaDB.
#
# El retrieval se realiza en dos fases:
#
#   1. Recuperación semántica mediante embeddings + ChromaDB.
#   2. Reranking híbrido combinando similitud semántica
#      y coincidencia léxica.
#
# La primera fase conserva la implementación base del retrieval
# y la segunda incorpora la mejora de reranking desarrollada
# durante la evaluación del sistema.

import re
import unicodedata

from google.genai import types

from config import (
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    TOP_K,
    RETRIEVAL_MIN_CANDIDATES,
    RETRIEVAL_SEMANTIC_WEIGHT,
    RETRIEVAL_LEXICAL_WEIGHT,
)

from src.gemini_client import crear_cliente_gemini
from src.index import crear_cliente_chroma


# =========================================================
# PREPARACIÓN DE LA CONSULTA
# =========================================================

def preparar_query(pregunta: str) -> str:
    """
    Prepara una pregunta para generar su embedding.

    Los documentos del corpus se representan durante la fase
    de embeddings con el formato:

        title: {title} | text: {text}

    Para las consultas utilizamos el formato específico de
    question answering:

        task: question answering | query: {pregunta}
    """

    pregunta = pregunta.strip()

    return f"task: question answering | query: {pregunta}"


# =========================================================
# EMBEDDING DE LA PREGUNTA
# =========================================================

def embeddear_pregunta_original(client, pregunta: str) -> list[float]:
    """
    Genera el embedding de una pregunta utilizando exactamente
    el procedimiento empleado en la primera versión del
    retrieval.

    A diferencia de la versión posterior para question
    answering, aquí la pregunta se envía directamente al modelo
    sin añadir un prefijo de tarea.

    Esta función se conserva para poder reproducir y evaluar de
    forma independiente el retrieval semántico original.
    """

    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    resultado = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=pregunta.strip(),
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
    )

    if not resultado.embeddings:
        raise ValueError("Gemini no ha devuelto ningún embedding para la pregunta.")

    vector = resultado.embeddings[0].values

    if vector is None:
        raise ValueError("El embedding de la pregunta no contiene valores.")

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Dimensión inesperada del embedding: {len(vector)}. "
            f"Se esperaban {EMBEDDING_DIMENSIONS}."
        )

    return vector

def embeddear_pregunta(client, pregunta: str) -> list[float]:
    """
    Genera el embedding de una pregunta.

    Se utiliza el mismo modelo y dimensionalidad empleados
    para los documentos del corpus, de manera que consultas
    y chunks puedan compararse mediante similitud coseno.

    El cliente Gemini se recibe como parámetro para permitir
    reutilizarlo durante evaluaciones con múltiples preguntas.
    """

    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    contenido = preparar_query(pregunta)

    resultado = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=contenido,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
    )

    if not resultado.embeddings:
        raise ValueError("Gemini no ha devuelto ningún embedding para la pregunta.")

    vector = resultado.embeddings[0].values

    if vector is None:
        raise ValueError("El embedding de la pregunta no contiene valores.")

    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Dimensión inesperada del embedding: {len(vector)}. "
            f"Se esperaban {EMBEDDING_DIMENSIONS}."
        )

    return vector


# =========================================================
# COMPATIBILIDAD CON LA IMPLEMENTACIÓN DE GENERACIÓN/EVAL
# =========================================================

def generar_embedding_query(pregunta: str) -> list[float]:
    """
    Genera el embedding de una consulta creando internamente
    el cliente Gemini.

    Se conserva esta función como interfaz sencilla para usos
    aislados, aunque las evaluaciones deberían reutilizar el
    cliente mediante embeddear_pregunta().
    """

    client = crear_cliente_gemini()

    try:
        return embeddear_pregunta(client, pregunta)

    finally:
        client.close()


# =========================================================
# RETRIEVAL SEMÁNTICO
# =========================================================

def buscar_chunks_relevantes(
    pregunta: str,
    top_k: int = TOP_K,
    client=None,
    collection=None,
    query_embedding: list[float] | None = None,
) -> list[dict]:
    """
    Recupera los chunks semánticamente más próximos a una
    pregunta utilizando embeddings y ChromaDB.

    Esta función representa la primera fase del retrieval:
    únicamente similitud vectorial, sin reranking léxico.

    Si se proporciona query_embedding, se reutiliza ese vector
    y no se realiza ninguna llamada a la API de embeddings.

    Parameters
    ----------
    pregunta : str
        Pregunta del usuario.

    top_k : int
        Número de candidatos semánticos a recuperar.

    client : opcional
        Cliente Gemini reutilizable. Solo es necesario cuando
        no se proporciona query_embedding.

    collection : opcional
        Colección ChromaDB reutilizable.

    query_embedding : list[float] | None
        Embedding de la pregunta ya calculado. Permite evitar
        llamadas repetidas a la API durante las evaluaciones.

    Returns
    -------
    list[dict]
        Lista de chunks ordenados según la distancia devuelta
        por ChromaDB, del más próximo al menos próximo.
    """

    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    if top_k <= 0:
        raise ValueError("top_k debe ser mayor que 0.")

    # Si ya tenemos el embedding de la pregunta, no necesitamos
    # crear ningún cliente Gemini.
    necesita_embedding = query_embedding is None

    cliente_propio = necesita_embedding and client is None

    if cliente_propio:
        client = crear_cliente_gemini()

    if collection is None:
        chroma_client = crear_cliente_chroma()
        collection = chroma_client.get_collection(name=CHROMA_COLLECTION_NAME)

    try:
        total_documentos = collection.count()

        if total_documentos == 0:
            raise ValueError("La colección de ChromaDB está vacía.")

        numero_resultados = min(top_k, total_documentos)

        if query_embedding is None:
            vector_pregunta = embeddear_pregunta(client, pregunta)

        else:

            if len(query_embedding) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    "Dimensión inesperada del embedding "
                    f"de la pregunta: {len(query_embedding)}. "
                    f"Se esperaban {EMBEDDING_DIMENSIONS}."
                )

            vector_pregunta = query_embedding

        resultado = collection.query(
            query_embeddings=[vector_pregunta],
            n_results=numero_resultados,
            include=["documents", "metadatas", "distances"]
        )

    finally:
        if cliente_propio:
            client.close()

    documentos = resultado.get("documents", [[]])[0]
    metadatas = resultado.get("metadatas", [[]])[0]
    distancias = resultado.get("distances", [[]])[0]
    chunks = []

    for texto, metadata, distancia in zip(documentos, metadatas, distancias):
        chunks.append(
            {
                "text": texto,
                "distance": distancia,
                "metadata": metadata or {},
            }
        )

    return chunks


# =========================================================
# NORMALIZACIÓN PARA EL RERANKING LÉXICO
# =========================================================

def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto para facilitar las comparaciones
    léxicas.

    - convierte a minúsculas;
    - elimina diacríticos;
    - elimina signos de puntuación;
    - normaliza espacios.
    """

    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caracter for caracter in texto if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def extraer_palabras_importantes(texto: str) -> set[str]:
    """
    Extrae los términos relevantes de una consulta eliminando
    palabras funcionales frecuentes que aportan poca
    información al reranking.
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
        palabra for palabra in palabras
        if palabra not in stopwords and len(palabra) > 2
    }


# =========================================================
# TEXTO UTILIZADO PARA EL RERANKING
# =========================================================

def construir_texto_busqueda(documento: str, metadata: dict) -> str:
    """
    Combina el texto del chunk con metadata relevante.

    Algunos términos importantes para recuperar correctamente
    puntos de recogida se encuentran también en campos como
    distrito, barrio o tipo de documento.
    """

    campos_metadata = [
        metadata.get("source", ""),
        metadata.get("document_type", ""),
        metadata.get("district", ""),
        metadata.get("neighborhood", ""),
    ]

    return " ".join([documento] + [str(campo) for campo in campos_metadata])


# =========================================================
# COINCIDENCIA LÉXICA
# =========================================================

def calcular_coincidencia_lexica(
    pregunta: str,
    documento: str,
    metadata: dict,
) -> float:
    """
    Calcula la proporción de palabras importantes de la
    consulta que aparecen en el documento o en su metadata.

    El valor resultante está comprendido entre 0 y 1.
    """

    palabras_pregunta = extraer_palabras_importantes(pregunta)

    if not palabras_pregunta:
        return 0.0

    texto_busqueda = construir_texto_busqueda(documento, metadata)

    palabras_documento = set(normalizar_texto(texto_busqueda).split())

    coincidencias = palabras_pregunta.intersection(palabras_documento)

    return len(coincidencias) / len(palabras_pregunta)


# =========================================================
# SCORE HÍBRIDO
# =========================================================

def calcular_score(distancia: float, coincidencia_lexica: float) -> float:
    """
    Combina la similitud semántica y la coincidencia léxica.

    ChromaDB devuelve distancia coseno:

        menor distancia = mayor similitud

    Por ello transformamos la distancia en:

        similitud_semantica = 1 - distancia

    La ponderación se encuentra centralizada en config.py.
    """

    similitud_semantica = 1 - distancia

    return (
        RETRIEVAL_SEMANTIC_WEIGHT * similitud_semantica
        +
        RETRIEVAL_LEXICAL_WEIGHT * coincidencia_lexica
    )


# =========================================================
# RERANKING DE CANDIDATOS
# =========================================================

def rerankear_chunks(pregunta: str, chunks: list[dict]) -> list[dict]:
    """
    Aplica el reranking híbrido a una lista de candidatos
    obtenidos previamente mediante retrieval semántico.

    Añade a cada chunk:

        lexical_score
        score

    y devuelve los chunks ordenados por score descendente.
    """

    candidatos = []

    for chunk in chunks:

        documento = chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        distancia = chunk.get("distance")

        if distancia is None:
            raise ValueError("Uno de los chunks no contiene distancia.")

        coincidencia_lexica = calcular_coincidencia_lexica(
            pregunta,
            documento,
            metadata,
        )

        score = calcular_score(distancia, coincidencia_lexica)

        candidato = {
            **chunk,
            "lexical_score": coincidencia_lexica,
            "score": score,
        }

        candidatos.append(candidato)

    candidatos.sort(key=lambda item: item["score"], reverse=True)

    return candidatos


# =========================================================
# RETRIEVAL FINAL
# =========================================================

def recuperar_chunks(
    pregunta: str,
    k: int = TOP_K,
    client=None,
    collection=None,
    query_embedding: list[float] | None = None,
) -> list[dict]:
    """
    Ejecuta el retrieval completo utilizado por el RAG.

    Flujo:

        pregunta
            ↓
        embedding de la consulta
        o embedding reutilizado
            ↓
        retrieval semántico
            ↓
        conjunto ampliado de candidatos
            ↓
        reranking semántico + léxico
            ↓
        top K final

    Si se proporciona query_embedding, se reutiliza el vector
    existente y no se vuelve a llamar a la API de embeddings.
    """

    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    if k <= 0:
        raise ValueError("k debe ser mayor que 0.")

    candidate_k = max(k * 10, RETRIEVAL_MIN_CANDIDATES)

    candidatos_semanticos = buscar_chunks_relevantes(
        pregunta=pregunta,
        top_k=candidate_k,
        client=client,
        collection=collection,
        query_embedding=query_embedding
    )

    candidatos_rerankeados = rerankear_chunks(pregunta, candidatos_semanticos)

    return candidatos_rerankeados[:k]


# =========================================================
# RESUMEN DE FUENTES
# =========================================================

def resumir_fuentes(chunks: list[dict]) -> list[dict]:
    """
    Extrae información de las fuentes recuperadas.

    Resulta útil tanto para mostrar trazabilidad como para
    las pruebas de evaluación del retrieval.
    """

    fuentes = []

    for chunk in chunks:
        metadata = chunk.get("metadata", {})

        fuentes.append(
            {
                "source": metadata.get("source"),
                "document_type": metadata.get("document_type"),
                "district": metadata.get("district"),
                "distance": chunk.get("distance"),
                "lexical_score": chunk.get("lexical_score"),
                "score": chunk.get("score")
            }
        )

    return fuentes


# =========================================================
# EJECUCIÓN MANUAL / PRUEBA RÁPIDA
# =========================================================

def ejecutar_retrieval(pregunta: str, top_k: int = TOP_K) -> list[dict]:
    """
    Ejecuta el retrieval completo y muestra por consola los
    resultados principales.

    Esta función sirve únicamente como prueba manual rápida.
    """

    print(f"Pregunta: {pregunta}")
    print(f"TOP_K: {top_k}")
    print()

    chunks = recuperar_chunks(pregunta, k=top_k)

    for posicion, chunk in enumerate(chunks, start=1):

        metadata = chunk.get("metadata", {})

        print(
            f"[{posicion}] "
            f"score={chunk['score']:.4f} "
            f"distancia={chunk['distance']:.4f} "
            f"lexical={chunk['lexical_score']:.4f}"
        )

        print(f"    fuente={metadata.get('source')}")
        print(f"    tipo={metadata.get('document_type')}")
        print(f"    distrito={metadata.get('district')}")
        print(f"    {chunk['text'][:200]}...")
        print()

    return chunks


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":
    ejecutar_retrieval("¿Dónde hay un punto limpio fijo en el distrito de Arganzuela?")