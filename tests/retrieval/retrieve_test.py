# Compara dos versiones del retrieval:
#
#   V1 -> retrieval semántico original
#   V2 -> retrieval semántico + reranking híbrido
#
# Las dos versiones utilizan exactamente:
#
#   - el mismo dataset;
#   - los mismos embeddings de consulta;
#   - la misma colección ChromaDB.
#
# Los embeddings de las preguntas de evaluación se generan
# una sola vez y se guardan en un archivo JSON persistente.
# Las siguientes ejecuciones reutilizan esos vectores y no
# necesitan volver a llamar a la API de embeddings.

import json
import sys
from pathlib import Path


# =========================================================
# CONFIGURACIÓN DEL PATH DEL PROYECTO
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    EVAL_QUERIES_JSON,
    EVAL_QUERY_EMBEDDINGS_JSON,
    TOP_K,
)

from src.gemini_client import crear_cliente_gemini
from src.index import crear_cliente_chroma
from src.retrieve import (
    embeddear_pregunta,
    embeddear_pregunta_original,
    buscar_chunks_relevantes,
    recuperar_chunks,
)


# =========================================================
# UTILIDADES DE SALIDA
# =========================================================

def mostrar_resultado(
    nombre: str,
    correcto: bool,
    detalle: str = "",
) -> bool:
    """
    Muestra el resultado de una comprobación.
    """

    estado = (
        "OK"
        if correcto
        else "ERROR"
    )

    print(
        f"[{estado}] {nombre}"
    )

    if detalle:
        print(
            f"       {detalle}"
        )

    return correcto


# =========================================================
# CARGA DEL DATASET DE EVALUACIÓN
# =========================================================

def cargar_eval_queries() -> list[dict]:
    """
    Carga las preguntas utilizadas para evaluar el retrieval.
    """

    if not EVAL_QUERIES_JSON.exists():
        raise FileNotFoundError(
            "No existe el archivo de preguntas: "
            f"{EVAL_QUERIES_JSON}"
        )

    with EVAL_QUERIES_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        payload = json.load(
            archivo
        )

    queries = payload.get(
        "queries",
        [],
    )

    total_declarado = payload.get(
        "total_queries"
    )

    if (
        total_declarado is not None
        and total_declarado != len(queries)
    ):
        raise ValueError(
            "El número de preguntas declarado en "
            "eval_queries.json no coincide con el "
            "número real de preguntas."
        )

    return queries


# =========================================================
# CACHÉ DE EMBEDDINGS DE CONSULTAS
# =========================================================

def cargar_cache_embeddings() -> dict:
    """
    Carga la caché persistente de embeddings de consultas.

    Si el archivo no existe, devuelve una estructura vacía.

    La versión actual de la caché almacena dos embeddings
    diferentes para cada pregunta:

        vector_original
            Embedding utilizado por el retrieval original.

        vector_qa
            Embedding con formato específico de
            question answering.
    """

    if not EVAL_QUERY_EMBEDDINGS_JSON.exists():
        return {
            "schema_version": 2,
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
            "queries": [],
        }

    with EVAL_QUERY_EMBEDDINGS_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        payload = json.load(
            archivo
        )

    return payload


def cache_compatible(
    cache: dict,
) -> bool:
    """
    Comprueba que la caché utiliza el mismo modelo y
    dimensionalidad que la configuración actual.
    """

    return (
        cache.get("model")
        == EMBEDDING_MODEL
        and cache.get("dimensions")
        == EMBEDDING_DIMENSIONS
    )


def indexar_cache_embeddings(
    cache: dict,
) -> dict[int, dict]:
    """
    Convierte las entradas de la caché en un diccionario
    indexado por id de pregunta.
    """

    return {
        item["id"]: item
        for item in cache.get(
            "queries",
            [],
        )
        if "id" in item
    }


def vector_cache_valido(
    vector,
) -> bool:
    """
    Comprueba que un vector almacenado en caché tiene
    el formato y dimensionalidad esperados.
    """

    return (
        isinstance(
            vector,
            list,
        )
        and len(vector)
        == EMBEDDING_DIMENSIONS
    )


def entrada_cache_corresponde(
    entrada: dict | None,
    query: dict,
) -> bool:
    """
    Comprueba que una entrada de caché corresponde
    realmente a la pregunta actual.

    Esto evita reutilizar un embedding antiguo si una
    pregunta mantiene el mismo id pero cambia su texto.
    """

    if entrada is None:
        return False

    return (
        entrada.get(
            "pregunta"
        )
        == query.get(
            "pregunta"
        )
    )


def migrar_entrada_cache(
    entrada: dict,
) -> dict:
    """
    Migra una entrada de la versión anterior de la caché.

    La primera versión almacenaba:

        "vector": [...]

    Ese vector fue generado utilizando embeddear_pregunta(),
    es decir, con el formato de question answering.

    Por tanto puede conservarse correctamente como:

        "vector_qa": [...]

    y no es necesario volver a generarlo.
    """

    entrada = dict(
        entrada
    )

    vector_antiguo = entrada.get(
        "vector"
    )

    if (
        "vector_qa" not in entrada
        and vector_cache_valido(
            vector_antiguo
        )
    ):
        entrada[
            "vector_qa"
        ] = vector_antiguo

    # Eliminamos el nombre antiguo una vez realizada
    # correctamente la migración.
    entrada.pop(
        "vector",
        None,
    )

    return entrada


def guardar_cache_embeddings(
    entradas: list[dict],
) -> None:
    """
    Guarda los embeddings de evaluación en disco.

    Cada pregunta puede contener:

        vector_original
        vector_qa
    """

    payload = {
        "schema_version": 2,
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        "queries": entradas,
    }

    EVAL_QUERY_EMBEDDINGS_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with EVAL_QUERY_EMBEDDINGS_JSON.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            payload,
            archivo,
            ensure_ascii=False,
            indent=2,
        )


def obtener_embeddings_evaluacion(
    queries: list[dict],
) -> dict[int, list[float]]:
    """
    Prepara los dos tipos de embeddings necesarios para
    comparar las distintas versiones del retrieval.

    Para cada pregunta se mantienen:

        vector_original
            Pregunta enviada directamente a Gemini.

        vector_qa
            Pregunta preparada como:
            task: question answering | query: ...

    En esta fase se sigue devolviendo vector_qa para mantener
    compatible el resto del test actual. En el siguiente paso
    utilizaremos ambos vectores para comparar tres versiones
    distintas del retrieval.

    Solo se generan los vectores que realmente falten.
    """

    cache = cargar_cache_embeddings()

    if not cache_compatible(
        cache
    ):
        print(
            "La caché existente usa otro modelo o "
            "dimensionalidad."
        )

        print(
            "Se regenerarán los embeddings de evaluación."
        )

        cache = {
            "schema_version": 2,
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
            "queries": [],
        }

    cache_por_id = indexar_cache_embeddings(
        cache
    )

    entradas_actualizadas = []

    pendientes_original = []
    pendientes_qa = []

    # Este diccionario mantiene, de momento, el contrato
    # anterior de la función:
    #
    #     id -> vector_qa
    #
    # Así no rompemos todavía el resto del test.
    embeddings_qa = {}

    for query in queries:

        query_id = query[
            "id"
        ]

        entrada = cache_por_id.get(
            query_id
        )

        if (
            entrada is not None
            and entrada_cache_corresponde(
                entrada,
                query,
            )
        ):
            entrada = migrar_entrada_cache(
                entrada
            )

        else:
            entrada = {
                "id": query_id,
                "pregunta": query[
                    "pregunta"
                ],
            }

        vector_original = entrada.get(
            "vector_original"
        )

        vector_qa = entrada.get(
            "vector_qa"
        )

        if not vector_cache_valido(
            vector_original
        ):
            pendientes_original.append(
                query
            )

        if not vector_cache_valido(
            vector_qa
        ):
            pendientes_qa.append(
                query
            )

        if vector_cache_valido(
            vector_qa
        ):
            embeddings_qa[
                query_id
            ] = vector_qa

        entradas_actualizadas.append(
            entrada
        )

    entradas_por_id = {
        entrada["id"]: entrada
        for entrada in entradas_actualizadas
    }

    print()
    print(
        "EMBEDDINGS DE EVALUACIÓN"
    )
    print(
        "-" * 70
    )

    print(
        f"Preguntas totales:            "
        f"{len(queries)}"
    )

    print(
        f"Embeddings QA a generar:      "
        f"{len(pendientes_qa)}"
    )

    print(
        f"Embeddings originales a generar: "
        f"{len(pendientes_original)}"
    )

    total_pendientes = (
        len(pendientes_qa)
        + len(pendientes_original)
    )

    # Solo abrimos Gemini si realmente falta algún vector.
    if total_pendientes > 0:

        client = crear_cliente_gemini()

        try:

            # ---------------------------------------------
            # EMBEDDINGS QA
            # ---------------------------------------------

            for posicion, query in enumerate(
                pendientes_qa,
                start=1,
            ):

                print(
                    f"Generando embedding QA "
                    f"{posicion}/{len(pendientes_qa)}: "
                    f"[{query['id']}] "
                    f"{query['pregunta']}"
                )

                vector = embeddear_pregunta(
                    client,
                    query[
                        "pregunta"
                    ],
                )

                entradas_por_id[
                    query["id"]
                ][
                    "vector_qa"
                ] = vector

                embeddings_qa[
                    query["id"]
                ] = vector

            # ---------------------------------------------
            # EMBEDDINGS ORIGINALES
            # ---------------------------------------------

            for posicion, query in enumerate(
                pendientes_original,
                start=1,
            ):

                print(
                    f"Generando embedding original "
                    f"{posicion}/"
                    f"{len(pendientes_original)}: "
                    f"[{query['id']}] "
                    f"{query['pregunta']}"
                )

                vector = embeddear_pregunta_original(
                    client,
                    query[
                        "pregunta"
                    ],
                )

                entradas_por_id[
                    query["id"]
                ][
                    "vector_original"
                ] = vector

        finally:
            client.close()

    # Nos aseguramos de que todos los embeddings QA estén
    # disponibles para el test actual.
    for query in queries:

        query_id = query[
            "id"
        ]

        entrada = entradas_por_id[
            query_id
        ]

        vector_qa = entrada.get(
            "vector_qa"
        )

        if not vector_cache_valido(
            vector_qa
        ):
            raise ValueError(
                "No se ha podido obtener un embedding QA "
                f"válido para la pregunta {query_id}."
            )

        embeddings_qa[
            query_id
        ] = vector_qa

    entradas_finales = [
        entradas_por_id[
            query["id"]
        ]
        for query in queries
    ]

    guardar_cache_embeddings(
        entradas_finales
    )

    print()

    print(
        f"Caché guardada en: "
        f"{EVAL_QUERY_EMBEDDINGS_JSON}"
    )

    embeddings = {}

    for query in queries:

        query_id = query["id"]

        entrada = entradas_por_id[
            query_id
        ]

        vector_original = entrada.get(
            "vector_original"
        )

        vector_qa = entrada.get(
            "vector_qa"
        )

        if not vector_cache_valido(
            vector_original
        ):
            raise ValueError(
                "No se ha podido obtener un embedding original "
                f"válido para la pregunta {query_id}."
            )

        if not vector_cache_valido(
            vector_qa
        ):
            raise ValueError(
                "No se ha podido obtener un embedding QA "
                f"válido para la pregunta {query_id}."
            )

        embeddings[
            query_id
        ] = {
            "original": vector_original,
            "qa": vector_qa,
        }

    return embeddings


# =========================================================
# VALIDACIÓN DE FUENTES
# =========================================================

def obtener_fuentes(
    chunks: list[dict],
) -> set[str]:
    """
    Devuelve las fuentes únicas presentes en los chunks.
    """

    return {
        chunk.get(
            "metadata",
            {},
        ).get(
            "source"
        )
        for chunk in chunks
        if chunk.get(
            "metadata",
            {},
        ).get(
            "source"
        )
    }


def alguna_fuente_esperada(
    chunks: list[dict],
    fuentes_esperadas: list[str],
) -> bool:
    """
    Comprueba si alguna fuente esperada aparece entre los
    resultados recuperados.
    """

    if not fuentes_esperadas:
        return True

    fuentes_recuperadas = obtener_fuentes(
        chunks
    )

    return any(
        fuente in fuentes_recuperadas
        for fuente in fuentes_esperadas
    )


# =========================================================
# VALIDACIÓN DEL ORDEN
# =========================================================

def resultados_semanticos_ordenados(
    chunks: list[dict],
) -> bool:
    """
    V1 debe estar ordenado por distancia ascendente.
    """

    distancias = [
        chunk["distance"]
        for chunk in chunks
    ]

    return (
        distancias
        == sorted(distancias)
    )


def resultados_hibridos_ordenados(
    chunks: list[dict],
) -> bool:
    """
    V2 debe estar ordenado por score descendente.
    """

    scores = [
        chunk["score"]
        for chunk in chunks
    ]

    return (
        scores
        == sorted(
            scores,
            reverse=True,
        )
    )


# =========================================================
# ADAPTADORES DE RETRIEVAL
# =========================================================

def retrieval_v1_original(
    pregunta: str,
    k: int,
    collection,
    query_embedding: list[float],
) -> list[dict]:
    """
    V1 — Retrieval original.

    Reproduce el retrieval semántico inicial utilizando
    el embedding de la pregunta sin prefijo de tarea.
    """

    return buscar_chunks_relevantes(
        pregunta=pregunta,
        top_k=k,
        collection=collection,
        query_embedding=query_embedding,
    )


def retrieval_v15_semantico_qa(
    pregunta: str,
    k: int,
    collection,
    query_embedding: list[float],
) -> list[dict]:
    """
    V1.5 — Retrieval semántico con query embedding preparado
    específicamente para question answering.

    Mantiene exactamente el mismo retrieval vectorial que V1;
    únicamente cambia la representación de la consulta.
    """

    return buscar_chunks_relevantes(
        pregunta=pregunta,
        top_k=k,
        collection=collection,
        query_embedding=query_embedding,
    )


def retrieval_v2_hibrido(
    pregunta: str,
    k: int,
    collection,
    query_embedding: list[float],
) -> list[dict]:
    """
    V2 — Retrieval semántico con query QA seguido de
    reranking híbrido semántico + léxico.
    """

    return recuperar_chunks(
        pregunta=pregunta,
        k=k,
        collection=collection,
        query_embedding=query_embedding,
    )

def retrieval_v2_hibrido_original(
    pregunta: str,
    k: int,
    collection,
    query_embedding: list[float],
) -> list[dict]:
    """
    V2B — Retrieval híbrido utilizando el embedding original
    de la consulta.

    Permite comprobar si el reranking híbrido mejora el
    retrieval original sin introducir el cambio posterior
    en la representación de la consulta.
    """

    return recuperar_chunks(
        pregunta=pregunta,
        k=k,
        collection=collection,
        query_embedding=query_embedding,
    )


# =========================================================
# EVALUACIÓN DE UNA VERSIÓN
# =========================================================

def evaluar_retrieval(
    nombre: str,
    queries: list[dict],
    embeddings: dict[int, dict[str, list[float]]],
    tipo_embedding: str,
    funcion_retrieval,
    collection,
    k: int = TOP_K,
) -> dict:
    """
    Evalúa una implementación del retrieval utilizando los
    embeddings precalculados.
    """

    print()
    print(
        "=" * 70
    )
    print(
        nombre
    )
    print(
        "=" * 70
    )
    print()

    errores = 0
    aciertos = 0
    total_respondibles = 0

    resultados_por_query = []

    for query in queries:

        query_id = query[
            "id"
        ]

        pregunta = query[
            "pregunta"
        ]

        fuentes_esperadas = query.get(
            "fuentes_esperadas",
            [],
        )

        es_respondible = query.get(
            "es_respondible",
            True,
        )

        query_embedding = embeddings[
            query_id
        ][
            tipo_embedding
        ]

        chunks = funcion_retrieval(
            pregunta=pregunta,
            k=k,
            collection=collection,
            query_embedding=query_embedding,
        )

        if tipo_embedding in {
            "original",
            "qa",
        } and all(
            "score" not in chunk
            for chunk in chunks
        ):
            orden_correcto = (
                resultados_semanticos_ordenados(
                    chunks
                )
            )

        else:
            orden_correcto = (
                resultados_hibridos_ordenados(
                    chunks
                )
            )

        if chunks:

            detalle = (
                f"chunks={len(chunks)} "
                f"top_distancia="
                f"{chunks[0]['distance']:.4f}"
            )

            if "score" in chunks[0]:
                detalle += (
                    f" "
                    f"top_score="
                    f"{chunks[0]['score']:.4f}"
                )

        else:
            detalle = (
                "sin resultados"
            )

        if not mostrar_resultado(
            (
                f"[{query_id}] "
                f"resultados ordenados: "
                f"{pregunta}"
            ),
            (
                bool(chunks)
                and orden_correcto
            ),
            detalle,
        ):
            errores += 1

        acierto = None

        if es_respondible:

            total_respondibles += 1

            acierto = alguna_fuente_esperada(
                chunks,
                fuentes_esperadas,
            )

            if acierto:
                aciertos += 1

            else:
                errores += 1

            fuentes_recuperadas = obtener_fuentes(
                chunks
            )

            mostrar_resultado(
                "       fuente esperada entre los recuperados",
                acierto,
                (
                    f"esperadas="
                    f"{fuentes_esperadas} | "
                    f"recuperadas="
                    f"{sorted(fuentes_recuperadas)}"
                ),
            )

        else:

            print(
                "       fuera de dominio"
            )

            print(
                "       La abstención se evalúa "
                "en la fase de generación."
            )

        resultados_por_query.append(
            {
                "id": query_id,
                "pregunta": pregunta,
                "es_respondible": es_respondible,
                "acierto": acierto,
            }
        )

        print()

    tasa = (
        aciertos
        / total_respondibles
        * 100
        if total_respondibles
        else 0
    )

    print(
        "-" * 70
    )

    print(
        f"Aciertos: "
        f"{aciertos}/{total_respondibles}"
    )

    print(
        f"Hit@{k}: "
        f"{tasa:.0f}%"
    )

    print(
        f"Incidencias: {errores}"
    )

    return {
        "nombre": nombre,
        "k": k,
        "aciertos": aciertos,
        "total": total_respondibles,
        "tasa": tasa,
        "errores": errores,
        "resultados": resultados_por_query,
    }


# =========================================================
# EXPERIMENTO K
# =========================================================

def experimentar_k(
    nombre: str,
    queries: list[dict],
    embeddings: dict[int, dict[str, list[float]]],
    tipo_embedding: str,
    funcion_retrieval,
    collection,
) -> dict[int, float]:
    """
    Compara distintos valores de K reutilizando siempre los
    mismos embeddings precalculados.
    """

    print()
    print(
        "=" * 70
    )

    print(
        f"EXPERIMENTO K — {nombre}"
    )

    print(
        "=" * 70
    )

    print()

    queries_respondibles = [
        query
        for query in queries
        if query.get(
            "es_respondible",
            True,
        )
    ]

    resultados = {}

    for k in (
        3,
        5,
        8,
        10,
    ):

        aciertos = 0

        for query in queries_respondibles:

            chunks = funcion_retrieval(
                pregunta=query[
                    "pregunta"
                ],
                k=k,
                collection=collection,
                query_embedding=embeddings[
                    query["id"]
                ][
                    tipo_embedding
                ],
            )

            if alguna_fuente_esperada(
                chunks,
                query.get(
                    "fuentes_esperadas",
                    [],
                ),
            ):
                aciertos += 1

        total = len(
            queries_respondibles
        )

        tasa = (
            aciertos
            / total
            * 100
            if total
            else 0
        )

        resultados[
            k
        ] = tasa

        print(
            f"K={k:<3} -> "
            f"aciertos "
            f"{aciertos}/{total} "
            f"({tasa:.0f}%)"
        )

    return resultados


# =========================================================
# COMPARACIÓN V1 / V2
# =========================================================

def mostrar_comparacion(
    resultado_v1: dict,
    resultado_v15: dict,
    resultado_v2: dict,
) -> None:
    """
    Compara las tres etapas del retrieval.

    V1:
        query original + retrieval semántico.

    V1.5:
        query QA + retrieval semántico.

    V2:
        query QA + retrieval híbrido.
    """

    print()
    print(
        "=" * 70
    )

    print(
        "COMPARACIÓN V1 vs V1.5 vs V2"
    )

    print(
        "=" * 70
    )

    print()

    print(
        f"V1 Pol original: "
        f"{resultado_v1['aciertos']}/"
        f"{resultado_v1['total']} "
        f"({resultado_v1['tasa']:.0f}%)"
    )

    print(
        f"V1.5 query QA:   "
        f"{resultado_v15['aciertos']}/"
        f"{resultado_v15['total']} "
        f"({resultado_v15['tasa']:.0f}%)"
    )

    print(
        f"V2 híbrido:      "
        f"{resultado_v2['aciertos']}/"
        f"{resultado_v2['total']} "
        f"({resultado_v2['tasa']:.0f}%)"
    )

    diferencia_query = (
        resultado_v15["tasa"]
        - resultado_v1["tasa"]
    )

    diferencia_reranking = (
        resultado_v2["tasa"]
        - resultado_v15["tasa"]
    )

    diferencia_total = (
        resultado_v2["tasa"]
        - resultado_v1["tasa"]
    )

    print()

    print(
        "Efecto del formato QA: "
        f"{diferencia_query:+.0f} "
        "puntos porcentuales"
    )

    print(
        "Efecto del reranking:  "
        f"{diferencia_reranking:+.0f} "
        "puntos porcentuales"
    )

    print(
        "Cambio total V2-V1:    "
        f"{diferencia_total:+.0f} "
        "puntos porcentuales"
    )

    print()
    print(
        "Cambios por pregunta:"
    )

    mapa_v1 = {
        item["id"]: item
        for item in resultado_v1[
            "resultados"
        ]
    }

    mapa_v15 = {
        item["id"]: item
        for item in resultado_v15[
            "resultados"
        ]
    }

    mapa_v2 = {
        item["id"]: item
        for item in resultado_v2[
            "resultados"
        ]
    }

    hubo_cambios = False

    for query_id in sorted(
        mapa_v1
    ):

        item_v1 = mapa_v1[
            query_id
        ]

        item_v15 = mapa_v15[
            query_id
        ]

        item_v2 = mapa_v2[
            query_id
        ]

        if not item_v1[
            "es_respondible"
        ]:
            continue

        estado_v1 = item_v1[
            "acierto"
        ]

        estado_v15 = item_v15[
            "acierto"
        ]

        estado_v2 = item_v2[
            "acierto"
        ]

        if (
            estado_v1
            == estado_v15
            == estado_v2
        ):
            continue

        hubo_cambios = True

        print(
            f"- [{query_id}] "
            f"{item_v1['pregunta']}"
        )

        print(
            f"    V1={estado_v1} | "
            f"V1.5={estado_v15} | "
            f"V2={estado_v2}"
        )

    if not hubo_cambios:
        print(
            "- No hay diferencias entre "
            "las tres versiones."
        )


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    print(
        "=" * 70
    )

    print(
        "EVALUACIÓN COMPARATIVA DEL RETRIEVAL"
    )

    print(
        "=" * 70
    )

    print()

    # -----------------------------------------------------
    # 1. CHROMADB
    # -----------------------------------------------------

    print(
        "1. CONEXIÓN CON CHROMADB"
    )

    print(
        "-" * 70
    )

    if not CHROMA_DIR.exists():

        mostrar_resultado(
            "Existe la base de datos persistente",
            False,
            (
                f"No existe: {CHROMA_DIR}. "
                "Ejecuta antes src/index.py."
            ),
        )

        return

    mostrar_resultado(
        "Existe la base de datos persistente",
        True,
        str(CHROMA_DIR),
    )

    print()

    # -----------------------------------------------------
    # 2. DATASET
    # -----------------------------------------------------

    print(
        "2. PREGUNTAS DE EVALUACIÓN"
    )

    print(
        "-" * 70
    )

    queries = cargar_eval_queries()

    if not queries:

        mostrar_resultado(
            "Existen preguntas de evaluación",
            False,
        )

        return

    mostrar_resultado(
        "Existen preguntas de evaluación",
        True,
        (
            f"Preguntas cargadas: "
            f"{len(queries)}"
        ),
    )

    # -----------------------------------------------------
    # 3. EMBEDDINGS DE CONSULTAS
    # -----------------------------------------------------

    embeddings = obtener_embeddings_evaluacion(
        queries
    )

    # -----------------------------------------------------
    # 4. CHROMADB
    # -----------------------------------------------------

    chroma_client = crear_cliente_chroma()

    collection = chroma_client.get_collection(
        name=CHROMA_COLLECTION_NAME
    )

    # -----------------------------------------------------
    # 5. V1 — POL ORIGINAL
    # -----------------------------------------------------

    resultado_v1 = evaluar_retrieval(
        nombre=(
            "V1 — POL ORIGINAL"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="original",
        funcion_retrieval=(
            retrieval_v1_original
        ),
        collection=collection,
        k=TOP_K,
    )


    # -----------------------------------------------------
    # 6. V1.5 — QUERY QA
    # -----------------------------------------------------

    resultado_v15 = evaluar_retrieval(
        nombre=(
            "V1.5 — RETRIEVAL SEMÁNTICO + QUERY QA"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="qa",
        funcion_retrieval=(
            retrieval_v15_semantico_qa
        ),
        collection=collection,
        k=TOP_K,
    )


    # -----------------------------------------------------
    # 7. V2 — RETRIEVAL HÍBRIDO
    # -----------------------------------------------------

    resultado_v2 = evaluar_retrieval(
        nombre=(
            "V2 — RETRIEVAL HÍBRIDO"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="qa",
        funcion_retrieval=(
            retrieval_v2_hibrido
        ),
        collection=collection,
        k=TOP_K,
    )

    # -----------------------------------------------------
    # 7.a. V2B — HÍBRIDO + EMBEDDING ORIGINAL
    # -----------------------------------------------------

    resultado_v2b = evaluar_retrieval(
        nombre=(
            "V2B — HÍBRIDO + EMBEDDING ORIGINAL"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="original",
        funcion_retrieval=(
            retrieval_v2_hibrido_original
        ),
        collection=collection,
        k=TOP_K,
    )


    # -----------------------------------------------------
    # 8. COMPARACIÓN
    # -----------------------------------------------------

    mostrar_comparacion(
        resultado_v1,
        resultado_v15,
        resultado_v2,
    )

    # -----------------------------------------------------
    # 9. EXPERIMENTO K — V1
    # -----------------------------------------------------

    experimentar_k(
        nombre=(
            "V1 — POL ORIGINAL"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="original",
        funcion_retrieval=(
            retrieval_v1_original
        ),
        collection=collection,
    )


    # -----------------------------------------------------
    # 10. EXPERIMENTO K — V1.5
    # -----------------------------------------------------

    experimentar_k(
        nombre=(
            "V1.5 — QUERY QA"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="qa",
        funcion_retrieval=(
            retrieval_v15_semantico_qa
        ),
        collection=collection,
    )


    # -----------------------------------------------------
    # 11. EXPERIMENTO K — V2
    # -----------------------------------------------------

    experimentar_k(
        nombre=(
            "V2 — HÍBRIDO"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="qa",
        funcion_retrieval=(
            retrieval_v2_hibrido
        ),
        collection=collection,
    )

    # -----------------------------------------------------
    # 12. EXPERIMENTO K — V2B
    # -----------------------------------------------------

    experimentar_k(
        nombre=(
            "V2B — HÍBRIDO + EMBEDDING ORIGINAL"
        ),
        queries=queries,
        embeddings=embeddings,
        tipo_embedding="original",
        funcion_retrieval=(
            retrieval_v2_hibrido_original
        ),
        collection=collection,
    )

    print()
    print("=" * 70)
    print("EVALUACIÓN FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    main()