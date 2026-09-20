# comprobaciones previas a registro
# comprobaciones de cadenas de texto válidas y normalizadas
# campos obligatorios con información
# contraseña cumpliendo requisitos y coincide con contraseña repetida
# dirección válida

import re
import unicodedata

#===================================================================
# NORMALIZACION DEL TEXTO
#===================================================================

def normalize_text(value: str) -> str:
    """
    Normaliza los campos de texto introducidos durante el registro.

    Reglas:
    - Elimina espacios al principio y al final.
    - Compacta espacios consecutivos.
    - Convierte el texto a minúsculas.
    - Elimina tildes y otros signos diacríticos.
    - Conserva la letra ñ.
    """

    # Eliminamos espacios sobrantes y compactamos espacios consecutivos.
    value = " ".join(value.strip().split())

    # Convertimos todo a minúsculas.
    value = value.lower()

    # Protegemos temporalmente la ñ para que Unicode no la convierta en n.
    value = value.replace("ñ", "__ENYE__")

    # Separamos las letras de sus signos diacríticos.
    value = unicodedata.normalize("NFD", value)

    # Eliminamos los signos diacríticos.
    value = "".join(
        char
        for char in value
        if unicodedata.category(char) != "Mn"
    )

    # Restauramos la ñ.
    value = value.replace("__ENYE__", "ñ")

    return value

#===================================================================
# PATRON Y NORMALIZACION DEL EMAIL
#===================================================================

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

# función de normalización concreta por si el email tuviera alguna tilde
def normalize_email(email: str) -> str:
    """
    Normaliza el email para su almacenamiento y comparación.

    - Elimina espacios al principio y al final.
    - Convierte a minúsculas.
    """
    return email.strip().lower()

def validate_email(email: str) -> bool:
    """
    Comprueba que el email tenga un formato válido.
    """
    email = normalize_email(email)

    return bool(EMAIL_PATTERN.fullmatch(email))


#===================================================================
# CODIGO POSTAL
#===================================================================

def validate_postal_code(postal_code: str) -> bool:
    """
    Comprueba que el código postal tenga exactamente
    cinco dígitos.
    """
    postal_code = postal_code.strip()

    return postal_code.isdigit() and len(postal_code) == 5


#===================================================================
# CONTRASEÑA
#===================================================================

# 8 caracteres mínimo
# minúscula
# mayúscula
# número

def validate_password(password: str) -> list[str]:
    """
    Valida los requisitos de seguridad de una contraseña.

    Devuelve una lista con los errores encontrados.
    Si la lista está vacía, la contraseña es válida.
    """

    errors = []

    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres.")

    if not any(char.isupper() for char in password):
        errors.append("La contraseña debe contener al menos una mayúscula.")

    if not any(char.islower() for char in password):
        errors.append("La contraseña debe contener al menos una minúscula.")

    if not any(char.isdigit() for char in password):
        errors.append("La contraseña debe contener al menos un número.")

    return errors

# contraseña y repetir contraseña coinciden o no...
def passwords_match(
    password: str,
    repeat_password: str,
) -> bool:
    """
    Comprueba que ambas contraseñas coincidan.
    """
    return password == repeat_password


#===================================================================
# CAMPO OBLIGATORIO
#===================================================================

# aplicar a:
# nombre, apellido1, dirección, provincia, ciudad, cp, email, contraseña, repetir contraseña

def validate_required_text(value: str) -> bool:
    """
    Comprueba que un campo obligatorio contenga texto.
    """
    if not isinstance(value, str):
        return False

    return bool(value.strip())