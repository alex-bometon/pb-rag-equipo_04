# Puente entre webapp y asistente RAG
# Recibe petición desde interfaz
# Transforma petición en llamada al asistente

# Más adelante hara imports como:
# from src.rag import ...

def ask_assistant(
    consulta: str,
    modo: str = "auto",
) -> dict:
    """
    Punto de entrada de la webapp hacia el asistente.

    Por ahora devuelve una respuesta simulada.
    Más adelante esta función llamará al RAG real.
    """

    return {
        "success": True,
        "answer": (
            f"Respuesta provisional para la consulta: "
            f"'{consulta}'"
        ),
        "mode": modo,
    }