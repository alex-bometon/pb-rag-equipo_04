from src.retrieve import recuperar_chunks
from src.generate import generar_respuesta


# =========================================================
# CONFIGURACIÓN
# =========================================================

DEFAULT_TOP_K = 5


# =========================================================
# CONSTRUCCIÓN DEL CONTEXTO
# =========================================================

def construir_contexto(chunks: list[dict]) -> str:
    """
    Construye el contexto que se enviará al modelo de generación
    a partir de los chunks recuperados.

    Cada chunk se incluye por separado para facilitar que el
    modelo identifique la información utilizada.
    """

    if not chunks:
        return ""

    partes = []

    for i, chunk in enumerate(chunks, start=1):

        texto = chunk.get("text", "")

        metadata = chunk.get(
            "metadata",
            {},
        )

        source = metadata.get(
            "source",
            "fuente desconocida",
        )

        partes.append(
            f"[CHUNK {i}]\n"
            f"Fuente: {source}\n"
            f"{texto}"
        )

    return "\n\n".join(partes)


# =========================================================
# EXTRACCIÓN DE FUENTES
# =========================================================

def extraer_fuentes(chunks: list[dict]) -> list[dict]:
    """
    Extrae la información de fuente de los chunks recuperados.

    Devuelve una lista de fuentes sin duplicados.
    """

    fuentes = []
    vistas = set()

    for chunk in chunks:

        metadata = chunk.get(
            "metadata",
            {},
        )

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

        vistas.add(clave)

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
    k: int = DEFAULT_TOP_K,
) -> dict:
    """
    Ejecuta el flujo completo del sistema RAG.

    Flujo:

        pregunta
            ↓
        retrieval
            ↓
        chunks
            ↓
        contexto
            ↓
        generación
            ↓
        respuesta + fuentes + chunks
    """

    if not pregunta or not pregunta.strip():
        raise ValueError(
            "La pregunta no puede estar vacía."
        )

    # -----------------------------------------------------
    # 1. RETRIEVAL
    # -----------------------------------------------------

    chunks = recuperar_chunks(
        pregunta,
        k=k,
    )

    # -----------------------------------------------------
    # 2. CONSTRUIR CONTEXTO
    # -----------------------------------------------------

    contexto = construir_contexto(
        chunks
    )

    # -----------------------------------------------------
    # 3. GENERACIÓN
    # -----------------------------------------------------

    respuesta = generar_respuesta(
        pregunta=pregunta,
        contexto=contexto,
    )

    # -----------------------------------------------------
    # 4. FUENTES
    # -----------------------------------------------------

    fuentes = extraer_fuentes(
        chunks
    )

    # -----------------------------------------------------
    # 5. DEVOLVER RESULTADO
    # -----------------------------------------------------

    return {
        "answer": respuesta,
        "sources": fuentes,
        "chunks": chunks,
    }


# =========================================================
# PRUEBA DIRECTA
# =========================================================

if __name__ == "__main__":

    pregunta = (
        "¿Dónde hay un punto limpio fijo "
        "en el distrito de Arganzuela?"
    )

    resultado = responder(
        pregunta,
        k=5,
    )

    print()
    print("RESPUESTA RAG")
    print("=" * 60)
    print(resultado["answer"])

    print()
    print("FUENTES")
    print("=" * 60)

    for fuente in resultado["sources"]:
        print(fuente)

    print()
    print("CHUNKS RECUPERADOS")
    print("=" * 60)

    for i, chunk in enumerate(
        resultado["chunks"],
        start=1,
    ):
        print()
        print(f"CHUNK {i}")
        print("-" * 60)
        print(
            f"Distancia: {chunk['distance']}"
        )
        print(
            f"Fuente: {chunk['metadata'].get('source')}"
        )
        print(
            chunk["text"]
        )