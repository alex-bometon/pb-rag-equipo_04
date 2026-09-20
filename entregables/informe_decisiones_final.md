# Informe de decisiones — Proyecto Break 1: RAG Engineering

## 1. Objetivo

El objetivo de esta fase es evaluar el sistema RAG desarrollado sobre el corpus de puntos limpios de Madrid y documentar las principales decisiones técnicas, observaciones de recuperación, generación, abstención y evaluación.

El sistema incluye:

- ingesta y corpus de documentos municipales;
- chunking;
- embeddings con Gemini Embedding 2;
- almacenamiento y recuperación mediante ChromaDB;
- reranking híbrido;
- generación de respuestas mediante Gemini;
- flujo RAG integrado;
- CLI;
- evaluación.

---

## 2. Experimento de chunking

La configuración inicial del proyecto era:

- `CHUNK_SIZE = 1000`
- `CHUNK_OVERLAP = 100`

Para evaluar el efecto del tamaño de los fragmentos se compararon tres configuraciones sobre el mismo corpus:

| Configuración | Chunk size | Overlap | Nº total de chunks | Tamaño medio | Mínimo | Máximo |
|---|---:|---:|---:|---:|---:|---:|
| A | 500 | 50 | 749 | 177,6 | 32 | 813 |
| B | 1000 | 100 | 712 | 186,9 | 41 | 997 |
| C | 1500 | 150 | 704 | 189,1 | 41 | 1497 |

El corpus tenía 691 documentos después de la limpieza.

### Observaciones

La configuración A, con chunks más pequeños, generó el mayor número de fragmentos: 749. Esto proporciona una mayor granularidad, pero también aumenta el número de elementos que deben almacenarse y recuperarse.

La configuración C, con chunks más grandes, produjo 704 chunks. Reduce ligeramente el número total de fragmentos y permite conservar más contexto en cada chunk, aunque puede introducir más información no relevante cuando se recupera un fragmento.

La configuración B, `1000/100`, produjo 712 chunks y representa una solución intermedia entre granularidad y cantidad de contexto.

### Decisión

Se mantiene:

```text
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
```

como configuración de trabajo.

La decisión se basa en que ofrece un equilibrio entre número de chunks y tamaño de los fragmentos, y además es la configuración con la que se realizaron las pruebas principales de retrieval y generación.

Como limitación, este experimento compara principalmente la estructura resultante del chunking. No se realizó una comparación completa de calidad de retrieval para cada configuración. Como siguiente paso se podría repetir la evaluación con las tres configuraciones y comparar métricas de retrieval y calidad de respuesta.

---

## 3. Embeddings

Se utilizó:

- modelo: `gemini-embedding-2`;
- dimensionalidad: `768`;
- distancia en ChromaDB: coseno.

Para las consultas se utilizó el formato:

```text
task: question answering | query: {pregunta}
```

Para los documentos se utilizó el formato:

```text
title: {title} | text: {text}
```

---

## 4. Retrieval y reranking

Durante las primeras pruebas se detectó un problema de recuperación.

Para la pregunta:

> ¿Dónde hay un punto limpio fijo en el distrito de Arganzuela?

la búsqueda semántica inicial no colocaba correctamente el documento del punto limpio fijo de Arganzuela entre los primeros resultados, aunque dicho documento sí estaba presente en ChromaDB.

El problema estaba, por tanto, en el ranking de recuperación y no en la ingesta.

Para solucionarlo se implementó un reranking híbrido que combina:

- similitud semántica;
- coincidencia léxica con términos relevantes de la consulta.

La puntuación final utilizada es:

```text
score = 0.70 × semantic_similarity + 0.30 × lexical_score
```

Además, se amplió el conjunto inicial de candidatos antes de realizar el reranking.

Después de este cambio, el documento del punto limpio fijo de Arganzuela pasó a aparecer como primer resultado y la respuesta generada fue correcta.

---

## 5. Observaciones de K

Se realizaron evaluaciones con:

- `K = 5`;
- `K = 10`.

### K = 5

Se evaluaron 12 preguntas.

En 11 preguntas la generación pudo ejecutarse correctamente y se produjo una incidencia `503 ServiceUnavailable` de la API.

Las preguntas 1-8 pertenecían al corpus. Las respuestas obtenidas fueron correctas en las preguntas que pudieron ejecutarse.

Las preguntas 9-12 estaban fuera del corpus y el sistema se abstuvo correctamente.

### K = 10

También se evaluaron 12 preguntas.

Se produjeron tres errores `429 TooManyRequests` relacionados con los límites de uso de la API. Las preguntas que sí pudieron ejecutarse mantuvieron respuestas correctas o abstenciones adecuadas.

### Decisión sobre K

Se mantiene:

```text
K = 5
```

como valor por defecto.

En las pruebas realizadas, K=5 fue suficiente para recuperar el contexto necesario. Aumentar a K=10 no produjo una mejora clara en las respuestas evaluadas y puede introducir información menos relevante en el contexto.

Como mejora futura se podría realizar una evaluación más sistemática con varios valores de K y métricas como precision@K y recall@K.

---

## 6. Acierto

Se utilizó como caso de éxito la consulta:

> ¿Cuál es la dirección del punto limpio fijo de Hortaleza?

El sistema respondió:

> La dirección del punto limpio fijo del distrito de Hortaleza es Calle Tomás Redondo 8.

El primer chunk recuperado correspondía al punto limpio fijo de Hortaleza y contenía la dirección indicada.

También se comprobó el grounding con la consulta sobre el horario del punto limpio fijo de Arganzuela, cuya respuesta reprodujo la información presente en el contexto recuperado.

---

## 7. Abstención

Se utilizaron preguntas fuera del dominio del corpus, entre ellas:

- ¿Cuál es la capital de Francia?
- ¿Quién ganó el Mundial de fútbol de 2022?
- ¿Cuál es la población actual de Madrid?
- ¿Qué restaurantes hay cerca de la Puerta del Sol?

En las ejecuciones correctas, el sistema se abstuvo en lugar de inventar una respuesta.

Además, se realizó una prueba específica:

> ¿Qué servicios de reparación de móviles hay cerca de Gran Vía?

El retrieval recuperó documentos parcialmente relacionados con términos de la consulta, como documentos que contienen «Gran Vía», pero el modelo detectó que el corpus solo contiene información sobre puntos limpios y se abstuvo.

Esto demuestra que la capa de generación puede evitar una respuesta inventada aunque el retrieval introduzca cierto ruido.

---

## 8. Tres fallos observados

### Fallo 1 — Retrieval semántico inicial

La búsqueda semántica inicial no priorizaba correctamente el punto limpio fijo de Arganzuela.

**Causa:** la similitud semántica por sí sola no daba suficiente peso a la coincidencia de términos como el distrito y el tipo de punto limpio.

**Solución aplicada:** reranking híbrido semántico + léxico.

**Resultado:** el documento correcto pasó a la primera posición y la respuesta fue correcta.

### Fallo 2 — Error 503 de disponibilidad de la API

Durante la evaluación con K=5 se produjo un error:

```text
503 ServiceUnavailable
```

Esto impidió generar una de las respuestas.

Se considera una incidencia operacional del servicio externo y no un fallo de calidad del retrieval o del grounding.

**Siguiente paso:** mantener reintentos con backoff exponencial y registrar los errores durante la evaluación.

### Fallo 3 — Errores 429 por límites de API

Durante la evaluación se produjeron errores:

```text
429 TooManyRequests
```

El proyecto alcanzó los límites observados de solicitudes por minuto y solicitudes por día del modelo utilizado inicialmente.

Se trata de una incidencia operacional de la API y no de un fallo de calidad del RAG.

**Solución aplicada:** cambiar el modelo de generación a `gemini-3.1-flash-lite` y reducir llamadas innecesarias durante las pruebas.

---

## 9. Siguientes pasos

1. Repetir, si el tiempo disponible lo permite, la evaluación de retrieval con las tres configuraciones de chunking para comparar no solo el número de chunks sino también la calidad de recuperación.
2. Ampliar el conjunto de evaluación manteniendo entre 8 y 15 preguntas en la evaluación mínima y añadiendo casos más difíciles.
3. Medir métricas específicas de retrieval, como precision@K y recall@K.
4. Estudiar filtros por tipo de documento y un mayor peso de entidades y metadatos.
5. Añadir un umbral mínimo de similitud para reducir ruido en consultas fuera del corpus.
6. Mantener el manejo de errores y backoff para la API.
7. Integrar el flujo RAG con Streamlit sin duplicar la lógica existente.

---

## 10. Configuración final de trabajo

| Componente | Configuración |
|---|---|
| Chunk size | 1000 |
| Chunk overlap | 100 |
| Embeddings | `gemini-embedding-2` |
| Dimensiones | 768 |
| Vector store | ChromaDB |
| Métrica | Cosine |
| Retrieval | ChromaDB + reranking híbrido |
| K por defecto | 5 |
| Generación | `gemini-3.1-flash-lite` |

## Conclusión

La evaluación muestra que el sistema es capaz de recuperar información del corpus, generar respuestas fundamentadas y abstenerse ante consultas fuera del dominio. El experimento de chunking permitió comparar tres configuraciones y mantener 1000/100 como configuración de trabajo. Durante el desarrollo también se identificaron y documentaron problemas de retrieval y de disponibilidad/cuota de la API, junto con las medidas aplicadas y las mejoras previstas.
