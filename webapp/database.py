# Únicamente responde a la base de datos de la aplicación web
# usuarios, conversaciones, preferencias...
# webapp/database.py

# webapp/database.py

# webapp/database.py

import sqlite3

from webapp.config_app import DB_PATH, STORAGE_DIR


def get_connection():
    """
    Crea y devuelve una conexión a la base de datos SQLite
    utilizada por la aplicación.
    """

    # Nos aseguramos de que exista la carpeta donde se guardará
    # la base de datos.
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    return sqlite3.connect(DB_PATH)


def init_database():
    """
    Inicializa la base de datos de la aplicación.

    Crea las tablas necesarias si todavía no existen.
    """

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nombre TEXT NOT NULL,
                apellido1 TEXT NOT NULL,
                apellido2 TEXT,

                direccion TEXT NOT NULL,
                direccion2 TEXT,

                provincia TEXT NOT NULL,
                ciudad TEXT NOT NULL,
                cp TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,

                is_active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

def get_user_by_email(email: str):
    """
    Busca un usuario por su email.

    Devuelve el usuario encontrado como una fila de SQLite
    o None si no existe.
    """

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        )

        return cursor.fetchone()


def create_user(
    nombre: str,
    apellido1: str,
    apellido2: str | None,
    direccion: str,
    direccion2: str | None,
    provincia: str,
    ciudad: str,
    cp: str,
    email: str,
    password_hash: str,
):
    """
    Guarda un nuevo usuario en la base de datos.

    Devuelve el ID generado para el nuevo usuario.
    """

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                nombre,
                apellido1,
                apellido2,
                direccion,
                direccion2,
                provincia,
                ciudad,
                cp,
                email,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre,
                apellido1,
                apellido2,
                direccion,
                direccion2,
                provincia,
                ciudad,
                cp,
                email,
                password_hash,
            ),
        )

        return cursor.lastrowid