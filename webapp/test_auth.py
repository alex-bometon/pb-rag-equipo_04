from webapp.auth import (
    authenticate_user,
    register_user,
)
from webapp.database import init_database


# Inicializa la base de datos y crea las tablas si no existen.
init_database()


# 1. Registro correcto
resultado_registro = register_user(
    nombre="José",
    apellido1="Muñoz",
    apellido2="García",
    direccion="Calle Alcalá, 25",
    direccion2="3º B",
    provincia="Madrid",
    ciudad="Madrid",
    cp="28001",
    email="JOSE@EMAIL.COM",
    password="Residuo2026",
    repetir_password="Residuo2026",
)

print("\n1. REGISTRO CORRECTO")
print(resultado_registro)


# 2. Intento de registro con el mismo email
resultado_duplicado = register_user(
    nombre="José",
    apellido1="Muñoz",
    apellido2="García",
    direccion="Calle Alcalá, 25",
    direccion2="3º B",
    provincia="Madrid",
    ciudad="Madrid",
    cp="28001",
    email="jose@email.com",
    password="Residuo2026",
    repetir_password="Residuo2026",
)

print("\n2. EMAIL DUPLICADO")
print(resultado_duplicado)


# 3. Login correcto
resultado_login = authenticate_user(
    email="JOSE@EMAIL.COM",
    password="Residuo2026",
)

print("\n3. LOGIN CORRECTO")
print(resultado_login)


# 4. Login con contraseña incorrecta
resultado_password_incorrecta = authenticate_user(
    email="jose@email.com",
    password="PasswordIncorrecta2026",
)

print("\n4. CONTRASEÑA INCORRECTA")
print(resultado_password_incorrecta)


# 5. Login con usuario inexistente
resultado_usuario_inexistente = authenticate_user(
    email="noexiste@email.com",
    password="Residuo2026",
)

print("\n5. USUARIO INEXISTENTE")
print(resultado_usuario_inexistente)