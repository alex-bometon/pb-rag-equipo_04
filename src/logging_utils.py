import json
from datetime import datetime, timezone

from config import OUTPUT_DIR


LOG_FILE = OUTPUT_DIR / "logs" / "rag.jsonl"


def registrar_consulta(
    pregunta: str,
    k: int,
    num_chunks: int,
    tiempo_segundos: float,
    modelo: str,
) -> None:
    """
    Registra una ejecución del RAG en formato JSONL.
    """

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    registro = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "question": pregunta,
        "k": k,
        "num_chunks": num_chunks,
        "time_seconds": round(
            tiempo_segundos,
            3,
        ),
        "model": modelo,
    }

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
    ) as archivo:
        archivo.write(
            json.dumps(
                registro,
                ensure_ascii=False,
            )
            + "\n"
        )