from src.generate import generar_respuesta


contexto = """
En Madrid, los residuos de envases de vidrio deben depositarse
en el contenedor verde.
"""

pregunta = "¿En qué contenedor se deben depositar los envases de vidrio?"

respuesta = generar_respuesta(pregunta, contexto)

print("\nRESPUESTA DEL RAG:")
print(respuesta)