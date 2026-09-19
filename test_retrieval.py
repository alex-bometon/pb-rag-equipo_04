from src.retrieve import recuperar_chunks


preguntas = [
    "Punto Limpio Fijo Arganzuela",
    "Dirección del Punto Limpio Fijo de Arganzuela",
    "Puntos limpios fijos del distrito de Arganzuela",
]


for pregunta in preguntas:
    print()
    print("=" * 70)
    print(f"PREGUNTA: {pregunta}")
    print("=" * 70)

    resultados = recuperar_chunks(pregunta, k=20)

    for i, chunk in enumerate(resultados, start=1):
        metadata = chunk["metadata"]

        print(
            f"{i:2}. "
            f"distancia={chunk['distance']:.4f} | "
            f"source={metadata.get('source')} | "
            f"district={metadata.get('district')} | "
            f"address={metadata.get('address')}"
        )