# Dominio del asistente RAG

## 1. Objetivo

El proyecto consiste en desarrollar un asistente conversacional basado en RAG capaz de responder preguntas sobre reciclaje y puntos de recogida de residuos en la ciudad de Madrid.

El asistente ayudará al usuario a determinar cómo y dónde depositar correctamente residuos domésticos o municipales utilizando exclusivamente la información disponible en el corpus documental incorporado al sistema.

## 2. Ámbito geográfico

La primera versión del sistema está limitada a **Madrid ciudad**.

No se proporcionará información específica sobre otros municipios de la Comunidad de Madrid ni sobre otras ciudades.

La V1 tampoco intentará detectar automáticamente la ubicación del usuario.

## 3. Ámbito temático

El asistente podrá responder preguntas relacionadas con:

- separación doméstica de residuos;
- contenedores y tipos de residuos admitidos;
- puntos limpios;
- puntos limpios móviles;
- puntos y servicios municipales de recogida;
- tratamiento adecuado de residuos domésticos especiales;
- ubicación y características de puntos de recogida incluidos en el corpus.

## 4. Fuera de alcance

Quedan fuera de la primera versión:

- residuos industriales;
- gestión de residuos específica de empresas;
- municipios distintos de Madrid;
- geolocalización automática;
- cálculo de rutas;
- consultas medioambientales generales que no estén relacionadas con la gestión de residuos;
- información no contenida en el corpus del sistema.

## 5. Política de respuesta

Las respuestas deberán estar respaldadas por información recuperada del corpus.

Cuando el sistema no encuentre información suficiente para responder con seguridad, deberá indicarlo expresamente en lugar de completar la respuesta utilizando únicamente el conocimiento previo del modelo.

Las respuestas deberán mostrar o identificar las fuentes utilizadas.

## 6. Tipos principales de consulta

La V1 estará diseñada principalmente para resolver:

1. **Destino de un residuo**
   - Ejemplo: «¿Dónde tiro una sartén?»

2. **Separación de residuos**
   - Ejemplo: «¿Qué va en el contenedor amarillo?»

3. **Puntos de recogida**
   - Ejemplo: «¿Dónde hay un punto limpio en Ventas?»

4. **Servicios de recogida**
   - Ejemplo: «¿Qué hago con un colchón viejo?»

5. **Residuos domésticos especiales**
   - Ejemplo: «¿Dónde puedo llevar una bombilla usada?»

```text
DOMINIO
│
├── Geografía
│   └── Madrid ciudad
│
├── Tema
│   └── Gestión de residuos domésticos/municipales
│
├── Funciones
│   ├── dónde tirar un residuo
│   ├── cómo separarlo
│   ├── puntos de recogida
│   ├── puntos limpios
│   └── servicios de recogida
│
├── Fuente de conocimiento
│   └── exclusivamente corpus oficial incorporado
│
└── Fuera de dominio
    ├── otras ciudades
    ├── residuos industriales
    ├── consultas ambientales generales
    ├── geolocalización
    └── información que no esté respaldada por el corpus
```
