from pathlib import Path
import sys


# =========================================================
# IMPORTS DEL PROYECTO
# =========================================================

# generate_test.py está en:
#
# pb-rag-equipo_04/tests/generation/generate_test.py
#
# parents[0] -> generation/
# parents[1] -> tests/
# parents[2] -> pb-rag-equipo_04/

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.generate import (
    ABSTENTION_MESSAGE,
    generar_respuesta,
)


# =========================================================
# CLIENTE GEMINI SIMULADO
# =========================================================

class FakeResponse:
    """
    Simula la respuesta devuelta por Gemini.
    """

    def __init__(self, text: str):
        self.text = text


class FakeModels:
    """
    Simula client.models de Gemini.

    Además registra las llamadas realizadas para poder
    comprobar posteriormente que generate.py utiliza
    correctamente el cliente.
    """

    def __init__(self):
        self.calls = []

    def generate_content(
        self,
        model,
        contents,
    ):
        self.calls.append(
            {
                "model": model,
                "contents": contents,
            }
        )

        return FakeResponse(
            "Los envases de vidrio deben depositarse "
            "en el contenedor verde."
        )


class FakeClient:
    """
    Cliente mínimo compatible con la interfaz utilizada
    por generar_respuesta().
    """

    def __init__(self):
        self.models = FakeModels()


# =========================================================
# TEST 1
# GENERACIÓN CON CONTEXTO
# =========================================================

def test_generacion_con_contexto():
    """
    Comprueba que generar_respuesta():

    - utiliza el cliente recibido;
    - realiza una única llamada al modelo;
    - incluye pregunta y contexto en el prompt;
    - devuelve el texto generado.
    """

    contexto = """
En Madrid, los residuos de envases de vidrio deben depositarse
en el contenedor verde.
"""

    pregunta = (
        "¿Dónde deben depositarse los envases de vidrio?"
    )

    client = FakeClient()

    respuesta = generar_respuesta(
        pregunta=pregunta,
        contexto=contexto,
        client=client,
    )

    assert respuesta == (
        "Los envases de vidrio deben depositarse "
        "en el contenedor verde."
    )

    assert len(client.models.calls) == 1

    prompt = client.models.calls[0]["contents"]

    assert pregunta in prompt

    assert "contenedor verde" in prompt


# =========================================================
# TEST 2
# ABSTENCIÓN SIN CONTEXTO
# =========================================================

def test_abstencion_sin_contexto():
    """
    Comprueba que, si no existe contexto recuperado,
    el sistema devuelve directamente el mensaje de
    abstención sin llamar a Gemini.
    """

    client = FakeClient()

    respuesta = generar_respuesta(
        pregunta="¿Dónde debo depositar una televisión?",
        contexto="",
        client=client,
    )

    assert respuesta == ABSTENTION_MESSAGE

    assert len(client.models.calls) == 0


# =========================================================
# TEST 3
# VALIDACIÓN DE PREGUNTA VACÍA
# =========================================================

def test_pregunta_vacia():
    """
    Comprueba que una pregunta vacía no se envía al modelo.
    """

    client = FakeClient()

    try:
        generar_respuesta(
            pregunta="   ",
            contexto="Contexto de prueba.",
            client=client,
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Se esperaba ValueError para una pregunta vacía."
        )

    assert len(client.models.calls) == 0


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":

    test_generacion_con_contexto()
    print(
        "OK - generación con contexto"
    )

    test_abstencion_sin_contexto()
    print(
        "OK - abstención sin contexto"
    )

    test_pregunta_vacia()
    print(
        "OK - validación de pregunta vacía"
    )

    print()
    print(
        "Todos los tests de generación "
        "han pasado correctamente."
    )