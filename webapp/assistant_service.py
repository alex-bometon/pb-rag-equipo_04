from src.rag import responder


def ask_assistant(
    consulta: str,
) -> dict:
    """
    Ejecuta una consulta contra el sistema RAG.

    Actúa como puente entre la interfaz Streamlit
    y la lógica del asistente definida en src.rag.
    """

    consulta = consulta.strip()

    if not consulta:
        return {
            "success": False,
            "answer": None,
            "sources": [],
            "chunks": [],
            "metrics": {},
            "error": "La consulta no puede estar vacía.",
        }

    try:
        resultado = responder(pregunta=consulta,)

    except Exception as error:
        return {
            "success": False,
            "answer": None,
            "sources": [],
            "chunks": [],
            "metrics": {},
            "error": str(error),
        }

    return {
        "success": True,
        "answer": resultado["answer"],
        "sources": resultado["sources"],
        "chunks": resultado["chunks"],
        "metrics": resultado["metrics"],
        "error": None,
    }