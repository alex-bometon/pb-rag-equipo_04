from pathlib import Path
import sys


# =========================================================
# IMPORTS DEL PROYECTO
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.generate import generar_respuesta


# =========================================================
# PRUEBA DE GENERACIÓN
# =========================================================

contexto = """
En Madrid, los residuos de envases de vidrio deben depositarse
en el contenedor verde.
"""

pregunta = "¿Dónde deben depositarse los envases de vidrio?"
respuesta = generar_respuesta(pregunta, contexto)


print()
print("=" * 60)
print("TEST REAL DE GENERACIÓN")
print("=" * 60)

print()
print("CONTEXTO:")
print(contexto.strip())

print()
print("PREGUNTA:")
print(pregunta)

print()
print("RESPUESTA DEL RAG:")
print(respuesta)