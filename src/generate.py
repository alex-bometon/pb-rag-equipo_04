# Se encarga de generar la respuesta final del sistema RAG
# utilizando exclusivamente el contexto recuperado.

import time

from google.genai import errors, types

from config import (
    GENERATION_MODEL,
    GENERATION_MAX_RETRIES,
    GENERATION_RETRY_SECONDS,
)

from src.gemini_client import crear_cliente_gemini


# =========================================================
# RESPUESTA DE ABSTENCIÓN
# =========================================================

ABSTENTION_MESSAGE = (
    "No puedo responder con la información disponible "
    "en los documentos."
)


# =========================================================
# CONSTRUCCIÓN DEL PROMPT
# =========================================================

def construir_prompt(
    pregunta: str,
    contexto: str,
) -> str:
    """
    Construye el prompt utilizado para generar la respuesta.

    El modelo debe responder exclusivamente a partir del
    contexto recuperado por el sistema RAG.
    """

    return f"""
Eres un asistente especializado en gestión de residuos y
puntos de recogida de Madrid.

Debes responder utilizando ÚNICAMENTE la información incluida
en el CONTEXTO.

INSTRUCCIONES:

- Utiliza únicamente información presente en el CONTEXTO.
- No utilices conocimiento externo.
- No inventes datos.
- No completes información que no aparezca en los documentos.
- Responde de forma clara y directa a la pregunta.
- Si el contexto contiene varias informaciones relevantes,
  combínalas únicamente cuando sean compatibles.
- Si el CONTEXTO no contiene información suficiente para
  responder a la pregunta, responde exactamente:

  "{ABSTENTION_MESSAGE}"

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}
""".strip()


# =========================================================
# LLAMADA AL MODELO
# =========================================================

def _generar_con_reintentos(
    client,
    prompt: str,
) -> str:
    """
    Ejecuta la llamada al modelo de generación.

    Los errores temporales de disponibilidad o cuota se
    reintentan utilizando espera exponencial.
    """

    errores_reintentables = {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }

    for intento in range(
        GENERATION_MAX_RETRIES
    ):
        try:

            respuesta = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(
                            disable=True
                        )
                    ),
                ),
            )

            texto = respuesta.text

            if not texto:
                raise ValueError(
                    "Gemini ha devuelto una respuesta vacía."
                )

            return texto.strip()

        except errors.APIError as error:

            if (
                error.code not in errores_reintentables
                or intento
                == GENERATION_MAX_RETRIES - 1
            ):
                raise

            espera = (
                GENERATION_RETRY_SECONDS
                * (2 ** intento)
            )

            print(
                "Error temporal de Gemini "
                f"({error.code}). "
                f"Reintentando en {espera} segundos..."
            )

            time.sleep(
                espera
            )

    # Esta línea no debería alcanzarse, pero evita que la
    # función pueda finalizar sin devolver un valor.
    raise RuntimeError(
        "No se pudo generar una respuesta."
    )


# =========================================================
# GENERACIÓN DE LA RESPUESTA
# =========================================================

def generar_respuesta(
    pregunta: str,
    contexto: str,
    client=None,
) -> str:
    """
    Genera una respuesta fundamentada exclusivamente en los
    chunks recuperados por el RAG.

    Parameters
    ----------
    pregunta : str
        Pregunta realizada por el usuario.

    contexto : str
        Contexto construido a partir de los chunks recuperados.

    client : opcional
        Cliente Gemini ya creado. Permite reutilizar el mismo
        cliente durante evaluaciones con múltiples preguntas.

    Returns
    -------
    str
        Respuesta generada por Gemini o mensaje explícito de
        abstención cuando no existe contexto suficiente.
    """

    if not pregunta or not pregunta.strip():
        raise ValueError(
            "La pregunta no puede estar vacía."
        )

    # Si retrieval no ha proporcionado ningún contexto,
    # no tiene sentido consumir una llamada al modelo.
    if not contexto or not contexto.strip():
        return ABSTENTION_MESSAGE

    prompt = construir_prompt(
        pregunta=pregunta.strip(),
        contexto=contexto.strip(),
    )

    cliente_propio = (
        client is None
    )

    if cliente_propio:
        client = crear_cliente_gemini()

    try:
        return _generar_con_reintentos(
            client,
            prompt,
        )

    finally:
        if cliente_propio:
            client.close()