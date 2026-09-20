# Orquestación del flujo completo del sistema RAG.

from config import TOP_K

from src.gemini_client import crear_cliente_gemini

from src.retrieve import (
    embeddear_pregunta_original,
    buscar_chunks_relevantes,
)

from src.generate import generar_respuesta


# =========================================================
# CONSTRUCCIÓN DEL CONTEXTO
# =========================================================

def construir_contexto(
    chunks: list[dict],
) -> str:
    """
    Construye el contexto que se enviará al modelo de
    generación a partir de los chunks recuperados.

    Cada chunk se mantiene separado e incluye su fuente para
    facilitar la trazabilidad de la respuesta.
    """

    if not chunks:
        return ""

    partes = []

    for i, chunk in enumerate(
        chunks,
        start=1,
    ):

        texto = (
            chunk.get(
                "text",
                "",
            )
            or ""
        ).strip()

        if not texto:
            continue

        metadata = chunk.get(
            "metadata",
            {},
        ) or {}

        source = metadata.get(
            "source",
            "fuente desconocida",
        )

        partes.append(
            f"[CHUNK {i}]\n"
            f"Fuente: {source}\n"
            f"{texto}"
        )

    return "\n\n".join(
        partes
    )


# =========================================================
# EXTRACCIÓN DE FUENTES
# =========================================================

def extraer_fuentes(
    chunks: list[dict],
) -> list[dict]:
    """
    Extrae las fuentes utilizadas por los chunks recuperados.

    Las fuentes duplicadas se eliminan conservando el orden
    de aparición.
    """

    fuentes = []
    vistas = set()

    for chunk in chunks:

        metadata = chunk.get(
            "metadata",
            {},
        ) or {}

        source = metadata.get(
            "source"
        )

        path = metadata.get(
            "path"
        )

        clave = (
            source,
            path,
        )

        if clave in vistas:
            continue

        vistas.add(
            clave
        )

        fuentes.append(
            {
                "source": source,
                "path": path,
            }
        )

    return fuentes


# =========================================================
# FUNCIÓN PRINCIPAL DEL RAG
# =========================================================

def responder(
    pregunta: str,
    k: int = TOP_K,
    client=None,
    collection=None,
    query_embedding: list[float] | None = None,
) -> dict:
    """
    Ejecuta el flujo completo del sistema RAG.

    Flujo:

        pregunta
            ↓
        embedding de consulta
            ↓
        retrieval semántico
            ↓
        chunks
            ↓
        contexto
            ↓
        generación
            ↓
        respuesta + fuentes + chunks

    Parameters
    ----------
    pregunta : str
        Pregunta realizada por el usuario.

    k : int
        Número máximo de chunks recuperados.

    client : opcional
        Cliente Gemini existente.

        Permite reutilizar el mismo cliente durante
        evaluaciones o ejecuciones múltiples.

    collection : opcional
        Colección ChromaDB existente.

        Permite evitar recuperar repetidamente la colección
        durante evaluaciones con varias preguntas.
    
    query_embedding : list[float] | None
        Embedding de la pregunta ya calculado.

        Permite reutilizar embeddings persistidos durante
        las evaluaciones y evitar llamadas repetidas a la
        API de embeddings.

    Returns
    -------
    dict
        Diccionario con:

            answer
            sources
            chunks
    """

    if not pregunta or not pregunta.strip():
        raise ValueError(
            "La pregunta no puede estar vacía."
        )

    if k <= 0:
        raise ValueError(
            "k debe ser mayor que 0."
        )

    pregunta = pregunta.strip()

    cliente_propio = (
        client is None
    )

    if cliente_propio:
        client = crear_cliente_gemini()

    try:

        # -------------------------------------------------
        # 1. EMBEDDING DE LA CONSULTA
        # -------------------------------------------------

        # Utilizamos de momento el embedding original porque
        # es la variante que ha obtenido mejores resultados
        # en la evaluación actual del retrieval.
        if query_embedding is None:

            query_embedding = (
                embeddear_pregunta_original(
                    client,
                    pregunta,
                )
            )

        # -------------------------------------------------
        # 2. RETRIEVAL
        # -------------------------------------------------

        # Baseline de producción actual:
        #
        #     retrieval semántico original
        #     + TOP_K definido en config.py
        #
        # Las variantes QA e híbrida se conservan en
        # retrieve.py para evaluación y futura optimización.
        chunks = buscar_chunks_relevantes(
            pregunta=pregunta,
            top_k=k,
            collection=collection,
            query_embedding=query_embedding,
        )

        # -------------------------------------------------
        # 3. CONSTRUCCIÓN DEL CONTEXTO
        # -------------------------------------------------

        contexto = construir_contexto(
            chunks
        )

        # -------------------------------------------------
        # 4. GENERACIÓN
        # -------------------------------------------------

        respuesta = generar_respuesta(
            pregunta=pregunta,
            contexto=contexto,
            client=client,
        )

        # -------------------------------------------------
        # 5. FUENTES
        # -------------------------------------------------

        fuentes = extraer_fuentes(
            chunks
        )

        # -------------------------------------------------
        # 6. RESULTADO
        # -------------------------------------------------

        return {
            "answer": respuesta,
            "sources": fuentes,
            "chunks": chunks,
        }

    finally:

        if cliente_propio:
            client.close()


# =========================================================
# PRUEBA DIRECTA
# =========================================================

if __name__ == "__main__":

    pregunta = (
        "¿Dónde hay un punto limpio fijo "
        "en el distrito de Arganzuela?"
    )

    resultado = responder(
        pregunta
    )

    print()
    print(
        "RESPUESTA RAG"
    )
    print(
        "=" * 60
    )
    print(
        resultado["answer"]
    )

    print()
    print(
        "FUENTES"
    )
    print(
        "=" * 60
    )

    for fuente in resultado[
        "sources"
    ]:
        print(
            fuente
        )

    print()
    print(
        "CHUNKS RECUPERADOS"
    )
    print(
        "=" * 60
    )

    for i, chunk in enumerate(
        resultado["chunks"],
        start=1,
    ):

        print()
        print(
            f"CHUNK {i}"
        )
        print(
            "-" * 60
        )

        print(
            "Distancia: "
            f"{chunk['distance']}"
        )

        print(
            "Fuente: "
            f"{chunk['metadata'].get('source')}"
        )

        print(
            chunk["text"]
        )