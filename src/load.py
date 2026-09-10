from pathlib import Path
import re

import pandas as pd
from bs4 import BeautifulSoup

from config import BASE_DIR, CSV_DIR, HTML_DIR


# =========================================================
# UTILIDADES
# =========================================================

def _leer_texto_con_fallback(path: Path) -> tuple[str, str]:
    """
    Lee un archivo de texto probando varias codificaciones.

    Devuelve:
        - contenido del archivo
        - codificación utilizada
    """

    codificaciones = (
        "utf-8-sig",
        "utf-8",
        "latin-1",
    )

    ultimo_error = None

    for encoding in codificaciones:
        try:
            contenido = path.read_text(encoding=encoding)
            return contenido, encoding

        except UnicodeDecodeError as error:
            ultimo_error = error

    raise ValueError(
        f"No se pudo leer el archivo '{path.name}'. "
        f"Último error: {ultimo_error}"
    )


def _extraer_texto_html(contenedor) -> str:
    """
    Extrae el contenido textual útil de un bloque HTML.

    Conserva títulos, subtítulos, párrafos y elementos
    de listas, eliminando etiquetas HTML.
    """

    etiquetas = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
    ]

    lineas = []

    for elemento in contenedor.find_all(etiquetas):

        # Evita duplicar contenido cuando un <li>
        # contiene otra lista interna.
        if elemento.name == "li" and elemento.find("li"):
            continue

        texto = " ".join(elemento.stripped_strings)

        # Normalizamos espacios repetidos.
        texto = re.sub(r"\s+", " ", texto).strip()

        # Elementos de interfaz que no aportan
        # información al corpus.
        if texto in {"", "Volver", "Escuchar"}:
            continue

        # Evita duplicados consecutivos.
        if lineas and texto == lineas[-1]:
            continue

        lineas.append(texto)

    return "\n".join(lineas)


# =========================================================
# CARGA DE CSV
# =========================================================

def cargar_csv(path: Path) -> dict:
    """
    Carga un CSV del corpus manteniendo su estructura tabular.

    Los CSV del corpus utilizan ';' como separador.

    Se cargan todas las columnas como texto para conservar
    los valores originales, incluidos códigos con ceros
    iniciales.
    """

    codificaciones = (
        "utf-8-sig",
        "latin-1",
    )

    ultimo_error = None

    for encoding in codificaciones:
        try:
            df = pd.read_csv(
                path,
                sep=";",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
            )

            return {
                "source": path.name,
                "title": path.stem.replace("_", " "),
                "path": str(path.relative_to(BASE_DIR)),
                "format": "csv",
                "encoding": encoding,
                "content": df,
            }

        except UnicodeDecodeError as error:
            ultimo_error = error

        except pd.errors.ParserError as error:
            ultimo_error = error

    raise ValueError(
        f"No se pudo cargar el CSV '{path.name}'. "
        f"Último error: {ultimo_error}"
    )


# =========================================================
# CARGA DE HTML
# =========================================================

def cargar_html(path: Path) -> dict:
    """
    Carga una página HTML del corpus y extrae
    su contenido textual principal.
    """

    html, encoding = _leer_texto_con_fallback(path)

    soup = BeautifulSoup(html, "html.parser")

    # El contenido útil de las páginas del Ayuntamiento
    # está dentro de <main id="readspeaker">.
    main = soup.find("main", id="readspeaker")

    if main is None:
        raise ValueError(
            f"No se ha encontrado el contenido principal "
            f"en '{path.name}'."
        )

    # En la mayoría de páginas el contenido principal
    # está todavía más acotado dentro de .detalle.
    detalle = main.find("div", class_="detalle")

    if detalle is not None:
        contenedor = detalle
    else:
        contenedor = main

    # Intentamos obtener un título útil.
    titulo_elemento = contenedor.find(
        ["h1", "h2", "h3"]
    )

    if titulo_elemento is not None:
        titulo = " ".join(
            titulo_elemento.stripped_strings
        )

    elif soup.title is not None:
        titulo = " ".join(
            soup.title.stripped_strings
        )

    else:
        titulo = path.stem.replace("_", " ")

    contenido = _extraer_texto_html(contenedor)

    if not contenido:
        raise ValueError(
            f"No se ha podido extraer texto útil "
            f"de '{path.name}'."
        )

    return {
        "source": path.name,
        "title": titulo,
        "path": str(path.relative_to(BASE_DIR)),
        "format": "html",
        "encoding": encoding,
        "content": contenido,
    }


# =========================================================
# CARGA DEL CORPUS COMPLETO
# =========================================================

def cargar_corpus() -> list[dict]:
    """
    Carga todos los documentos disponibles
    en las carpetas configuradas en config.py.

    Actualmente soporta:
        - CSV
        - HTML
    """

    documentos = []

    for path in sorted(CSV_DIR.glob("*.csv")):
        documentos.append(
            cargar_csv(path)
        )

    for path in sorted(HTML_DIR.glob("*.html")):
        documentos.append(
            cargar_html(path)
        )

    return documentos