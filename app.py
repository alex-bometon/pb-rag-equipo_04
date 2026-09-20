# ¿Qué pantalla enseño? ¿Qué botón se ha pulsado?
# ¿Se ha autenticado el usuario? ¿Qué formulario se tiene que mostrar?
# ¿Qué consulta se ha escrito? ¿Qué hago cuando se pulsa determinado botón?

import streamlit as st

from webapp.assistant_service import ask_assistant
from webapp.auth import authenticate_user, register_user
from webapp.database import init_database
from webapp.config_app import APP_DESCRIPTION, APP_NAME


# -------------------------
# Configuración de página
# -------------------------

st.set_page_config(page_title=APP_NAME, layout="centered")


# -------------------------
# Inicialización
# -------------------------

init_database()


# -------------------------
# Estado de sesión
# -------------------------

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "vista" not in st.session_state:
    st.session_state.vista = "inicio"

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []


# -------------------------
# Funciones de navegación
# -------------------------

def cambiar_vista(vista: str):
    """
    Cambia la vista actual de la aplicación.
    """
    st.session_state.vista = vista
    st.rerun()

def cerrar_sesion():
    """
    Cierra la sesión del usuario y vuelve a la vista inicial.
    """
    st.session_state.usuario = None
    st.session_state.vista = "inicio"
    st.session_state.mensajes = []

    st.rerun()

def mostrar_detalles_asistente(
    mensaje: dict,
):
    """
    Muestra fuentes, chunks recuperados y métricas
    asociadas a una respuesta del asistente.
    """

    fuentes = mensaje.get("sources", [])
    chunks = mensaje.get("chunks", [])
    metricas = mensaje.get("metrics", {})

    # -------------------------
    # Métricas
    # -------------------------

    if metricas:

        k = metricas.get("k", "-")
        num_chunks = metricas.get("num_chunks", "-")
        tiempo = metricas.get("time_seconds")
        modelo = metricas.get("model", "-")

        tiempo_texto = (
            f"{tiempo:.2f} s"
            if isinstance(tiempo, (int, float))
            else "-"
        )

        st.caption("Métricas de la consulta")

        st.markdown(
            f"**K:** {k} · "
            f"**Chunks:** {num_chunks} · "
            f"**Tiempo:** {tiempo_texto} · "
            f"**Modelo:** `{modelo}`"
        )

    # -------------------------
    # Fuentes
    # -------------------------

    if fuentes:
        with st.expander("Fuentes utilizadas"):
            for fuente in fuentes:
                nombre = fuente.get("source")

                if nombre:
                    st.write(f"- `{nombre}`")

    # -------------------------
    # Contexto / chunks
    # -------------------------

    if chunks:
        with st.expander("Contexto recuperado"):
            for indice, chunk in enumerate(chunks, start=1):
                metadata = chunk.get("metadata", {}) or {}
                source = metadata.get("source", "Fuente desconocida")
                distancia = chunk.get("distance")
                texto = chunk.get("text", "") or ""

                st.markdown(f"**Chunk {indice} — {source}**")

                if isinstance(distancia, (int, float)):
                    st.caption("Distancia vectorial: {distancia:.4f}")

                st.write(texto)

                if indice < len(chunks):
                    st.divider()

# -------------------------
# Cabecera
# -------------------------

st.title(APP_NAME)


# -------------------------
# Usuario no autenticado
# -------------------------

if st.session_state.usuario is None:

    # -------------------------
    # Vista: inicio
    # -------------------------

    if st.session_state.vista == "inicio":

        st.write(APP_DESCRIPTION)

        st.subheader("Bienvenido")

        columna_login, columna_registro = st.columns(2)

        with columna_login:
            if st.button("Iniciar sesión",  use_container_width=True):
                cambiar_vista("login")

        with columna_registro:
            if st.button("Crear cuenta", use_container_width=True):
                cambiar_vista("registro")

    # -------------------------
    # Vista: login
    # -------------------------

    elif st.session_state.vista == "login":

        st.subheader("Iniciar sesión")

        st.write("¿No tienes cuenta?")

        if st.button(
            "Crear cuenta",
            use_container_width=True,
            key="ir_registro_desde_login",
        ):
            cambiar_vista("registro")

        st.divider()

        with st.form("form_login"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            enviar_login = st.form_submit_button("Iniciar sesión", use_container_width=True)

        if enviar_login:
            resultado = authenticate_user(email=email, password=password)

            if resultado["success"]:
                st.session_state.usuario = resultado["user"]
                st.session_state.vista = "asistente"

                st.rerun()

            else:
                st.error(resultado["error"])

        if st.button("← Volver al inicio", key="volver_inicio_desde_login"):
            cambiar_vista("inicio")

    # -------------------------
    # Vista: registro
    # -------------------------

    elif st.session_state.vista == "registro":
        st.subheader("Crear cuenta")
        st.write("¿Ya tienes cuenta?")

        if st.button(
            "Iniciar sesión",
            use_container_width=True,
            key="ir_login_desde_registro",
        ):
            cambiar_vista("login")

        st.divider()

        st.write("Los campos marcados con * son obligatorios.")

        with st.form("form_registro"):

            nombre = st.text_input("Nombre *")
            apellido1 = st.text_input("Primer apellido *")
            apellido2 = st.text_input("Segundo apellido")
            direccion = st.text_input("Dirección *", placeholder="Calle y número")
            direccion2 = st.text_input("Dirección adicional", placeholder="Piso, puerta, escalera...")
            provincia = st.text_input("Provincia *")
            ciudad = st.text_input("Ciudad *")
            cp = st.text_input("Código postal *", max_chars=5)
            email = st.text_input("Email *")

            password = st.text_input(
                "Contraseña *",
                type="password",
                help=(
                    "Debe tener al menos 8 caracteres, "
                    "una mayúscula, una minúscula y un número."
                ),
            )

            repetir_password = st.text_input("Repetir contraseña *", type="password")
            enviar_registro = st.form_submit_button("Crear cuenta", use_container_width=True)

        if enviar_registro:
            resultado = register_user(
                nombre=nombre,
                apellido1=apellido1,
                apellido2=apellido2,
                direccion=direccion,
                direccion2=direccion2,
                provincia=provincia,
                ciudad=ciudad,
                cp=cp,
                email=email,
                password=password,
                repetir_password=repetir_password
            )

            if resultado["success"]:
                st.success(
                    "Cuenta creada correctamente. Ya puedes iniciar sesión."
                )

                if st.button(
                    "Ir a iniciar sesión",
                    use_container_width=True,
                    key="login_despues_registro",
                ):
                    cambiar_vista("login")

            else:
                for error in resultado["errors"]:
                    st.error(error)

        if st.button("← Volver al inicio", key="volver_inicio_desde_registro"):
            cambiar_vista("inicio")


else:

    # -------------------------
    # Usuario autenticado
    # -------------------------

    usuario = st.session_state.usuario

    # -------------------------
    # Cabecera privada
    # -------------------------

    columna_usuario, columna_logout = st.columns([3, 1])

    with columna_usuario:
        st.write(f"Hola, **{usuario['nombre']}**")

    with columna_logout:
        if st.button("Cerrar sesión", use_container_width=True):
            cerrar_sesion()

    st.divider()

    # -------------------------
    # Asistente
    # -------------------------

    st.subheader("Asistente de residuos")

    st.write(
        "Pregunta sobre reciclaje, residuos, "
        "contenedores o puntos de recogida "
        "de la ciudad de Madrid."
    )

    # -------------------------
    # Historial del chat
    # -------------------------

    for mensaje in st.session_state.mensajes:
        with st.chat_message(mensaje["role"]):
            st.write(mensaje["content"])

            if mensaje["role"] == "assistant":
                mostrar_detalles_asistente(mensaje)

    # -------------------------
    # Entrada del usuario
    # -------------------------

    consulta = st.chat_input("Escribe tu consulta...")

    if consulta:

        # Guardamos la pregunta.
        st.session_state.mensajes.append(
            {
                "role": "user",
                "content": consulta,
            }
        )

        # Ejecutamos el RAG.
        with st.spinner("Buscando información..."):
            resultado = ask_assistant(consulta=consulta)

        # -------------------------
        # Respuesta correcta
        # -------------------------

        if resultado["success"]:
            st.session_state.mensajes.append(
                {
                    "role": "assistant",
                    "content": resultado["answer"],
                    "sources": resultado["sources"],
                    "chunks": resultado["chunks"],
                    "metrics": resultado["metrics"]
                }
            )

        # -------------------------
        # Error
        # -------------------------

        else:
            st.session_state.mensajes.append(
                {
                    "role": "assistant",
                    "content": "No se ha podido procesar la consulta.",
                    "sources": [],
                    "chunks": [],
                    "metrics": {}
                }
            )

        st.rerun()