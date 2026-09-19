from src.gemini_client import crear_cliente_gemini


# Modelo utilizado para generar las respuestas del RAG
GENERATION_MODEL = "gemini-3.1-flash-lite"


def generar_respuesta(pregunta: str, contexto: str) -> str:
    """
    Genera una respuesta utilizando únicamente la información
    proporcionada en el contexto recuperado.

    Args:
        pregunta: Pregunta realizada por el usuario.
        contexto: Fragmentos recuperados de los documentos.

    Returns:
        Respuesta generada por Gemini.
    """

    cliente = crear_cliente_gemini()

    prompt = f"""
Eres un asistente que responde preguntas utilizando únicamente
la información proporcionada en el CONTEXTO.

INSTRUCCIONES:
- Responde únicamente utilizando la información del CONTEXTO.
- No inventes información.
- No utilices conocimientos externos al CONTEXTO.
- Si el CONTEXTO no contiene información suficiente para responder,
  indica claramente que no puedes responder con la información
  disponible en los documentos.

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}
"""

    respuesta = cliente.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt
    )

    return respuesta.text