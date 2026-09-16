# comprueba que embeddings coincida con chroma_db

import json
import math
from pathlib import Path
import sys

import chromadb

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    EMBEDDING_DIMENSIONS,
    EMBEDDINGS_JSON,
)


# =========================================================
# UTILIDADES
# =========================================================

def cargar_embeddings_json() -> dict:
    """
    Carga directamente embeddings.json para utilizarlo
    como referencia durante las comprobaciones.
    """

    if not EMBEDDINGS_JSON.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {EMBEDDINGS_JSON}"
        )

    with EMBEDDINGS_JSON.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        return json.load(archivo)


def mostrar_resultado(
    nombre: str,
    correcto: bool,
    detalle: str = "",
) -> bool:
    """
    Muestra el resultado de una comprobación.
    """

    estado = "OK" if correcto else "ERROR"

    print(f"[{estado}] {nombre}")

    if detalle:
        print(f"       {detalle}")

    return correcto

def metadata_equivalente(
    metadata_origen: dict,
    metadata_chroma: dict,
) -> bool:
    """
    Compara dos diccionarios de metadata.

    Los valores de tipo float se comparan con una pequeña
    tolerancia porque ChromaDB puede representar los números
    decimales con una precisión ligeramente distinta.

    El resto de valores deben coincidir exactamente.
    """

    if not isinstance(metadata_chroma, dict):
        return False

    if set(metadata_origen.keys()) != set(metadata_chroma.keys()):
        return False

    for clave in metadata_origen:

        valor_origen = metadata_origen[clave]
        valor_chroma = metadata_chroma[clave]


        # Los bool también son int en Python,
        # por eso se excluyen explícitamente.
        ambos_numericos = (
            isinstance(valor_origen, (int, float))
            and not isinstance(valor_origen, bool)
            and isinstance(valor_chroma, (int, float))
            and not isinstance(valor_chroma, bool)
        )


        if ambos_numericos:

            if not math.isclose(
                float(valor_origen),
                float(valor_chroma),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                return False

        else:

            if valor_origen != valor_chroma:
                return False


    return True


# =========================================================
# TEST PRINCIPAL
# =========================================================

def main() -> None:

    print("=" * 70)
    print("COMPROBACIÓN DE INDEXACIÓN EN CHROMADB")
    print("=" * 70)
    print()

    errores = 0


    # =====================================================
    # 1. CARGAR EMBEDDINGS DE REFERENCIA
    # =====================================================

    print("1. ARTEFACTO DE REFERENCIA")
    print("-" * 70)

    payload = cargar_embeddings_json()

    items = payload.get(
        "items",
        [],
    )

    total_embeddings = len(items)

    dimensiones_esperadas = payload.get(
        "embedding_dimensions"
    )

    print(
        f"Embeddings en embeddings.json: {total_embeddings}"
    )

    print(
        f"Dimensiones esperadas:         {dimensiones_esperadas}"
    )

    print()


    # =====================================================
    # 2. ABRIR CHROMADB
    # =====================================================

    print("2. CONEXIÓN CON CHROMADB")
    print("-" * 70)

    if not CHROMA_DIR.exists():

        mostrar_resultado(
            "Existe la base de datos persistente",
            False,
            f"No existe: {CHROMA_DIR}",
        )

        return

    if not mostrar_resultado(
        "Existe la base de datos persistente",
        True,
        str(CHROMA_DIR),
    ):
        errores += 1


    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    print()


    # =====================================================
    # 3. COMPROBAR COLECCIÓN
    # =====================================================

    print("3. COLECCIÓN")
    print("-" * 70)

    colecciones = client.list_collections()

    nombres = [
        coleccion.name
        for coleccion in colecciones
    ]

    existe_coleccion = (
        CHROMA_COLLECTION_NAME in nombres
    )

    if not mostrar_resultado(
        "Existe la colección esperada",
        existe_coleccion,
        f"Colección: {CHROMA_COLLECTION_NAME}",
    ):
        errores += 1

        print()
        print("=" * 70)
        print("RESULTADO: INDEXACIÓN NO VÁLIDA")
        print("=" * 70)

        return


    collection = client.get_collection(
        name=CHROMA_COLLECTION_NAME
    )

    print()


    # =====================================================
    # 4. NÚMERO DE REGISTROS
    # =====================================================

    print("4. CANTIDAD DE REGISTROS")
    print("-" * 70)

    total_chroma = collection.count()

    correcto = (
        total_chroma == total_embeddings
    )

    if not mostrar_resultado(
        "Chroma contiene un registro por embedding",
        correcto,
        (
            f"embeddings.json: {total_embeddings} | "
            f"ChromaDB: {total_chroma}"
        ),
    ):
        errores += 1

    print()


    # =====================================================
    # 5. RECUPERAR TODOS LOS REGISTROS
    # =====================================================

    print("5. ESTRUCTURA DE LOS REGISTROS")
    print("-" * 70)

    resultado = collection.get(
        include=[
            "documents",
            "metadatas",
            "embeddings",
        ]
    )

    ids = resultado.get(
        "ids",
        [],
    )

    documents = resultado.get(
        "documents",
        [],
    )

    metadatas = resultado.get(
        "metadatas",
        [],
    )

    embeddings = resultado.get(
        "embeddings",
        [],
    )


    comprobaciones_estructura = [
        (
            "Número de IDs",
            len(ids) == total_embeddings,
            len(ids),
        ),
        (
            "Número de documentos",
            len(documents) == total_embeddings,
            len(documents),
        ),
        (
            "Número de metadatos",
            len(metadatas) == total_embeddings,
            len(metadatas),
        ),
        (
            "Número de vectores",
            len(embeddings) == total_embeddings,
            len(embeddings),
        ),
    ]


    for nombre, correcto, cantidad in comprobaciones_estructura:

        if not mostrar_resultado(
            nombre,
            correcto,
            f"Encontrados: {cantidad}",
        ):
            errores += 1

    print()


    # =====================================================
    # 6. IDS
    # =====================================================

    print("6. IDENTIFICADORES")
    print("-" * 70)

    ids_unicos = (
        len(ids) == len(set(ids))
    )

    if not mostrar_resultado(
        "Todos los IDs son únicos",
        ids_unicos,
        (
            f"IDs totales: {len(ids)} | "
            f"IDs únicos: {len(set(ids))}"
        ),
    ):
        errores += 1


    ids_vacios = sum(
        1
        for identificador in ids
        if not isinstance(identificador, str)
        or not identificador.strip()
    )

    if not mostrar_resultado(
        "Todos los IDs son cadenas no vacías",
        ids_vacios == 0,
        f"IDs inválidos: {ids_vacios}",
    ):
        errores += 1

    print()


    # =====================================================
    # 7. DOCUMENTOS
    # =====================================================

    print("7. DOCUMENTOS")
    print("-" * 70)

    documentos_vacios = sum(
        1
        for documento in documents
        if not isinstance(documento, str)
        or not documento.strip()
    )

    if not mostrar_resultado(
        "Todos los documentos contienen texto",
        documentos_vacios == 0,
        f"Documentos vacíos: {documentos_vacios}",
    ):
        errores += 1

    print()


    # =====================================================
    # 8. METADATA
    # =====================================================

    print("8. METADATA")
    print("-" * 70)

    metadata_invalidos = sum(
        1
        for metadata in metadatas
        if not isinstance(metadata, dict)
    )

    if not mostrar_resultado(
        "Todos los registros contienen metadata",
        metadata_invalidos == 0,
        f"Metadata inválidos: {metadata_invalidos}",
    ):
        errores += 1


    fuentes_vacias = sum(
        1
        for metadata in metadatas
        if not metadata.get("source")
    )

    if not mostrar_resultado(
        "Todos los registros conservan la fuente",
        fuentes_vacias == 0,
        f"Registros sin source: {fuentes_vacias}",
    ):
        errores += 1


    tipos_vacios = sum(
        1
        for metadata in metadatas
        if not metadata.get("document_type")
    )

    if not mostrar_resultado(
        "Todos los registros conservan document_type",
        tipos_vacios == 0,
        f"Registros sin document_type: {tipos_vacios}",
    ):
        errores += 1

    print()


    # =====================================================
    # 9. EMBEDDINGS ALMACENADOS
    # =====================================================

    print("9. VECTORES INDEXADOS")
    print("-" * 70)

    dimensiones_incorrectas = 0
    valores_invalidos = 0
    vectores_cero = 0

    for vector in embeddings:

        if len(vector) != EMBEDDING_DIMENSIONS:
            dimensiones_incorrectas += 1
            continue

        vector_correcto = True

        for valor in vector:

            if not isinstance(
                valor,
                (int, float),
            ):
                valores_invalidos += 1
                vector_correcto = False
                break

            if not math.isfinite(
                float(valor)
            ):
                valores_invalidos += 1
                vector_correcto = False
                break

        if not vector_correcto:
            continue

        norma = math.sqrt(
            sum(
                float(valor) ** 2
                for valor in vector
            )
        )

        if norma == 0:
            vectores_cero += 1


    comprobaciones_vectores = [
        (
            "Todos los vectores tienen 768 dimensiones",
            dimensiones_incorrectas == 0,
            f"Vectores incorrectos: {dimensiones_incorrectas}",
        ),
        (
            "Todos los valores son numéricos y finitos",
            valores_invalidos == 0,
            f"Vectores con valores inválidos: {valores_invalidos}",
        ),
        (
            "No existen vectores nulos",
            vectores_cero == 0,
            f"Vectores de norma 0: {vectores_cero}",
        ),
    ]


    for nombre, correcto, detalle in comprobaciones_vectores:

        if not mostrar_resultado(
            nombre,
            correcto,
            detalle,
        ):
            errores += 1

    print()

    # =====================================================
    # 10. CORRESPONDENCIA CON EMBEDDINGS.JSON
    # =====================================================

    print("10. CORRESPONDENCIA CON EMBEDDINGS.JSON")
    print("-" * 70)


    # -----------------------------------------------------
    # DOCUMENTOS
    # -----------------------------------------------------

    documentos_origen = {
        item["text"]
        for item in items
    }

    documentos_chroma = set(
        documents
    )


    if not mostrar_resultado(
        "Los documentos de Chroma corresponden al corpus",
        documentos_origen == documentos_chroma,
        (
            f"Origen: {len(documentos_origen)} documentos únicos | "
            f"Chroma: {len(documentos_chroma)} documentos únicos"
        ),
    ):
        errores += 1


    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    # Como cada texto del corpus es único, podemos utilizar
    # el propio documento como clave para comparar directamente
    # la metadata original con la recuperada desde Chroma.

    metadata_origen_por_texto = {
        item["text"]: item["metadata"]
        for item in items
    }

    metadata_chroma_por_texto = {
        documento: metadata
        for documento, metadata in zip(
            documents,
            metadatas,
        )
    }


    diferencias_metadata = []


    for texto, metadata_origen in metadata_origen_por_texto.items():

        metadata_chroma = metadata_chroma_por_texto.get(
            texto
        )

        if not metadata_equivalente(
            metadata_origen,
            metadata_chroma,
        ):

            diferencias_metadata.append(
                (
                    texto,
                    metadata_origen,
                    metadata_chroma,
                )
            )


    metadata_correcta = (
        len(diferencias_metadata) == 0
    )


    if not mostrar_resultado(
        "Cada documento conserva su metadata correcta",
        metadata_correcta,
        (
            f"Documentos con diferencias: "
            f"{len(diferencias_metadata)}"
        ),
    ):
        errores += 1


    # -----------------------------------------------------
    # DIAGNÓSTICO DE DIFERENCIAS
    # -----------------------------------------------------

    if diferencias_metadata:

        print()
        print("DIAGNÓSTICO DE METADATA")
        print("-" * 70)

        # Mostramos como máximo los primeros 5 casos.
        # No necesitamos imprimir los 712 documentos completos.
        for indice, (
            texto,
            metadata_origen,
            metadata_chroma,
        ) in enumerate(
            diferencias_metadata[:5],
            start=1,
        ):

            print()
            print(f"Diferencia {indice}")
            print()

            print(
                "Documento:"
            )

            print(
                texto[:200].replace(
                    "\n",
                    " ",
                )
            )

            print()


            # Reunimos todas las claves que aparecen
            # en cualquiera de las dos versiones.

            claves = sorted(
                set(metadata_origen)
                |
                set(metadata_chroma or {})
            )


            for clave in claves:

                valor_origen = metadata_origen.get(
                    clave,
                    "<NO EXISTE>",
                )

                valor_chroma = (
                    metadata_chroma.get(
                        clave,
                        "<NO EXISTE>",
                    )
                    if metadata_chroma is not None
                    else "<NO EXISTE>"
                )


                ambos_numericos = (
                    isinstance(valor_origen, (int, float))
                    and not isinstance(valor_origen, bool)
                    and isinstance(valor_chroma, (int, float))
                    and not isinstance(valor_chroma, bool)
                )

                if ambos_numericos:

                    valores_iguales = math.isclose(
                        float(valor_origen),
                        float(valor_chroma),
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )

                else:

                    valores_iguales = (
                        valor_origen == valor_chroma
                    )


                if not valores_iguales:

                    print(
                        f"Clave: {clave}"
                    )

                    print(
                        f"  origen: "
                        f"{repr(valor_origen)} "
                        f"({type(valor_origen).__name__})"
                    )

                    print(
                        f"  chroma: "
                        f"{repr(valor_chroma)} "
                        f"({type(valor_chroma).__name__})"
                    )

                    print()


    # =====================================================
    # 11. RESUMEN
    # =====================================================

    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Colección:               {CHROMA_COLLECTION_NAME}"
    )

    print(
        f"Embeddings de origen:    {total_embeddings}"
    )

    print(
        f"Registros en ChromaDB:   {total_chroma}"
    )

    print(
        f"Dimensiones por vector:  {EMBEDDING_DIMENSIONS}"
    )

    print()


    # =====================================================
    # 12. RESULTADO FINAL
    # =====================================================

    if errores == 0:

        print(
            "RESULTADO: INDEXACIÓN VÁLIDA"
        )

    else:

        print(
            f"RESULTADO: INDEXACIÓN NO VÁLIDA "
            f"({errores} errores)"
        )


if __name__ == "__main__":
    main()