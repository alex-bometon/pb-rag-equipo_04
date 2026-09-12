# Autenticación y gestión de acceso
# registro de usuario / login
# comprobación de contraseña
# comprobación de user activo

import bcrypt

from webapp.database import create_user, get_user_by_email
from webapp.validators import (
    normalize_email,
    normalize_text,
    validate_email,
    validate_password,
    validate_postal_code,
    validate_required_text,
    passwords_match,
)

#===================================================================
# HASH CONTRASEÑA
#===================================================================

def hash_password(password: str) -> str:
    """
    Genera un hash seguro de la contraseña.

    La contraseña original nunca se almacena.
    """

    password_bytes = password.encode("utf-8")

    password_hash = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return password_hash.decode("utf-8")

# A usar durante login
def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Comprueba si una contraseña coincide con el hash almacenado.
    """

    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


#===================================================================
# REGISTRO DE USUARIO
#===================================================================

def register_user(
    nombre: str,
    apellido1: str,
    apellido2: str,
    direccion: str,
    direccion2: str,
    provincia: str,
    ciudad: str,
    cp: str,
    email: str,
    password: str,
    repetir_password: str,
) -> dict:
    """
    Valida y registra un nuevo usuario.

    Devuelve un diccionario con:
    - success: indica si el registro se ha realizado correctamente.
    - errors: lista de errores encontrados.
    - user_id: ID del usuario creado o None si el registro falla.
    """

    errors = []

    # -------------------------
    # Campos obligatorios
    # -------------------------

    campos_obligatorios = {
        "Nombre": nombre,
        "Primer apellido": apellido1,
        "Dirección": direccion,
        "Provincia": provincia,
        "Ciudad": ciudad,
        "Código postal": cp,
        "Email": email,
    }

    for nombre_campo, valor in campos_obligatorios.items():
        if not validate_required_text(valor):
            errors.append(
                f"El campo '{nombre_campo}' es obligatorio."
            )

    # -------------------------
    # Email
    # -------------------------

    email = normalize_email(email)

    if email and not validate_email(email):
        errors.append(
            "El email introducido no tiene un formato válido."
        )

    # -------------------------
    # Código postal
    # -------------------------

    if cp and not validate_postal_code(cp):
        errors.append(
            "El código postal debe contener exactamente 5 dígitos."
        )

    # -------------------------
    # Contraseña
    # -------------------------

    errors.extend(validate_password(password))

    if not passwords_match(password, repetir_password):
        errors.append(
            "Las contraseñas no coinciden."
        )

    # -------------------------
    # Email duplicado
    # -------------------------

    if not errors:
        usuario_existente = get_user_by_email(email)

        if usuario_existente is not None:
            errors.append(
                "Ya existe una cuenta registrada con este email."
            )

    # -------------------------
    # Si hay errores, detenemos
    # -------------------------

    if errors:
        return {
            "success": False,
            "errors": errors,
            "user_id": None,
        }

    # -------------------------
    # Normalización de texto
    # -------------------------

    nombre = normalize_text(nombre)
    apellido1 = normalize_text(apellido1)

    apellido2 = (
        normalize_text(apellido2)
        if apellido2.strip()
        else None
    )

    direccion = normalize_text(direccion)

    direccion2 = (
        normalize_text(direccion2)
        if direccion2.strip()
        else None
    )

    provincia = normalize_text(provincia)
    ciudad = normalize_text(ciudad)

    cp = cp.strip()

    # -------------------------
    # Hash de contraseña
    # -------------------------

    password_hash = hash_password(password)

    # -------------------------
    # Crear usuario
    # -------------------------

    user_id = create_user(
        nombre=nombre,
        apellido1=apellido1,
        apellido2=apellido2,
        direccion=direccion,
        direccion2=direccion2,
        provincia=provincia,
        ciudad=ciudad,
        cp=cp,
        email=email,
        password_hash=password_hash,
    )

    # -------------------------
    # Registro correcto
    # -------------------------

    return {
        "success": True,
        "errors": [],
        "user_id": user_id,
    }


#===================================================================
# LOGIN, AUTENTICACION
#===================================================================

def authenticate_user(
    email: str,
    password: str,
) -> dict:
    """
    Comprueba las credenciales de un usuario.

    Devuelve:
    - success: indica si la autenticación ha sido correcta.
    - error: mensaje de error si el login falla.
    - user: datos básicos del usuario si el login es correcto.
    """

    # -------------------------
    # Normalización del email
    # -------------------------

    email = normalize_email(email)

    # -------------------------
    # Comprobaciones básicas
    # -------------------------

    if not email or not password:
        return {
            "success": False,
            "error": "Email y contraseña son obligatorios.",
            "user": None,
        }

    if not validate_email(email):
        return {
            "success": False,
            "error": "Email o contraseña incorrectos.",
            "user": None,
        }

    # -------------------------
    # Buscar usuario
    # -------------------------

    user = get_user_by_email(email)

    if user is None:
        return {
            "success": False,
            "error": "Email o contraseña incorrectos.",
            "user": None,
        }

    # -------------------------
    # Comprobar cuenta activa
    # -------------------------

    if not user["is_active"]:
        return {
            "success": False,
            "error": "La cuenta está desactivada.",
            "user": None,
        }

    # -------------------------
    # Verificar contraseña
    # -------------------------

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return {
            "success": False,
            "error": "Email o contraseña incorrectos.",
            "user": None,
        }

    # -------------------------
    # Login correcto
    # -------------------------

    return {
        "success": True,
        "error": None,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nombre": user["nombre"],
            "apellido1": user["apellido1"],
            "apellido2": user["apellido2"],
        },
    }