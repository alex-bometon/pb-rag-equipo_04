# Informe de decisiones — Proyecto Break 1: RAG Engineering

## 1. Objetivo y alcance

El proyecto desarrolla **ReciclaTIA**, un sistema RAG orientado a responder consultas sobre reciclaje, residuos domésticos y municipales, contenedores y puntos de recogida de la ciudad de Madrid.

El objetivo técnico es construir un flujo completo y reproducible:

```text
fuentes externas
    ↓
carga y limpieza
    ↓
chunking
    ↓
embeddings
    ↓
ChromaDB
    ↓
retrieval
    ↓
construcción de contexto
    ↓
generación fundamentada
    ↓
respuesta + fuentes + chunks
```

El sistema debe responder utilizando únicamente información procedente del corpus. Cuando la información recuperada no permite contestar, debe abstenerse explícitamente en lugar de completar la respuesta utilizando conocimiento externo.

El desarrollo se repartió entre varios miembros del equipo y posteriormente se realizó una revisión e integración conjunta de las distintas partes para garantizar que corpus, retrieval, generación y evaluación funcionasen como un único sistema.

---

## 2. Delimitación del dominio

Se decidió limitar la primera versión a información correspondiente a la **ciudad de Madrid** y relacionada con:

* clasificación de residuos;
* contenedores y fracciones de recogida;
* residuos domésticos;
* puntos limpios fijos;
* puntos limpios móviles;
* puntos limpios de proximidad;
* recogida de muebles y enseres;
* recogida de aceite vegetal usado.

Quedaron fuera del alcance de esta versión:

* búsquedas generales fuera de Madrid;
* geolocalización automática;
* cálculo de rutas;
* recomendación automática del punto más cercano;
* servicios municipales no relacionados con residuos;
* información sobre otras ciudades.

Esta delimitación permite evaluar de forma clara cuándo una pregunta pertenece o no al corpus y hace posible aplicar un criterio explícito de abstención.

---

## 3. Corpus final

Durante el desarrollo se trabajó inicialmente con un corpus considerablemente mayor.

Una primera versión llegó a contener aproximadamente:

```text
18 archivos
2.914 documentos limpios
2.935 chunks
```

Gran parte del volumen procedía de datasets de localización de contenedores ordinarios.

Durante la revisión se concluyó que esos datos no eran necesarios para la V1, ya que todavía no se implementa búsqueda geoespacial ni cálculo del contenedor más cercano.

Se decidió reducir el corpus a la información realmente necesaria para las funcionalidades del proyecto.

### Corpus final

El corpus definitivo contiene **15 archivos fuente** en dos formatos diferentes.

#### CSV

* `puntos_limpios_fijos.csv`
* `puntos_limpios_moviles.csv`
* `puntos_limpios_moviles_24h.csv`
* `puntos_limpios_proximidad.csv`
* `tipos_residuos.csv`

#### HTML

* `fraccion_organica.html`
* `fraccion_papel.html`
* `fraccion_plasticos_metales_briks.html`
* `fraccion_resto.html`
* `fraccion_vidrio.html`
* `recogida_aceite_vegetal.html`
* `recogida_muebles_enseres.html`
* `residuos_punto_limpio_fijo.html`
* `residuos_punto_limpio_movil.html`
* `residuos_punto_limpio_proximidad.html`

Tras la limpieza se obtuvieron:

```text
691 documentos limpios
```

La decisión de reducir el corpus tuvo dos efectos positivos:

1. eliminó información innecesaria para el dominio funcional de la V1;
2. redujo considerablemente el número de embeddings necesarios.

---

## 4. Separación del pipeline

Se mantuvo una arquitectura modular para evitar concentrar todo el proceso en un único script o notebook.

Las principales responsabilidades se distribuyen entre:

```text
src/load.py
    carga de fuentes

src/clean.py
    limpieza y normalización

src/chunk.py
    fragmentación

src/embed.py
    generación de embeddings

src/artifacts.py
    persistencia de artefactos

src/index.py
    construcción de ChromaDB

src/retrieve.py
    recuperación de chunks

src/generate.py
    generación fundamentada

src/rag.py
    orquestación del flujo completo

src/gemini_client.py
    creación del cliente Gemini

src/logging_utils.py
    registro de métricas de ejecución
```

Esta separación permite ejecutar de forma independiente las etapas costosas y reutilizar los resultados ya calculados.

---

# 5. Decisión de chunking

Se compararon tres configuraciones sobre el corpus actual.

| Configuración | Chunk size | Overlap | Total chunks |
| ------------- | ---------: | ------: | -----------: |
| A             |        800 |     100 |          722 |
| B             |       1000 |     100 |          712 |
| C             |       1500 |     150 |          704 |

En las tres configuraciones se partió de los mismos:

```text
691 documentos limpios
```

### Configuración A — 800 / 100

Produce el mayor número de fragmentos:

```text
722 chunks
```

Ofrece mayor granularidad, pero incrementa el número de elementos indexados y puede separar información que resulta útil conservar junta.

### Configuración B — 1000 / 100

Produce:

```text
712 chunks
```

Mantiene suficiente contexto por fragmento sin aumentar innecesariamente el volumen del índice.

### Configuración C — 1500 / 150

Produce:

```text
704 chunks
```

Reduce ligeramente el número de fragmentos, pero cada resultado recuperado puede incluir más información no relacionada directamente con la consulta.

### Decisión final

Se mantiene:

```python
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
```

El corpus final genera:

```text
712 chunks
```

distribuidos aproximadamente entre:

```text
681 chunks procedentes de información estructurada
31 chunks procedentes de documentación HTML
```

La configuración `1000/100` representa un equilibrio adecuado entre granularidad y conservación de contexto.

---

# 6. Embeddings

## 6.1. Modelo

Se eligió:

```text
gemini-embedding-2
```

con:

```text
768 dimensiones
```

y similitud:

```text
cosine
```

La dimensionalidad de 768 se consideró suficiente para un corpus pequeño y especializado y evita utilizar vectores de mayor tamaño sin una mejora demostrada para este caso.

---

## 6.2. Problemas encontrados con la primera versión del corpus

Con el corpus inicial de aproximadamente 2.935 chunks se detectaron límites operativos del Free Tier de Gemini.

Durante la generación aparecieron errores:

```text
429 RESOURCE_EXHAUSTED
```

Se comprobó que existían límites tanto por minuto como por día.

El corpus inicial requería casi tres veces el número de embeddings permitido diariamente en las condiciones observadas.

Se estudiaron varias posibilidades:

* pausas entre lotes;
* reintentos;
* backoff;
* checkpoints;
* persistencia incremental;
* modelos locales alternativos.

También se estudió `multilingual-e5-base` como alternativa local.

Sin embargo, tras redefinir correctamente el alcance de la V1, el corpus quedó reducido a 712 chunks. Con ese tamaño volvió a ser viable utilizar Gemini sin introducir otra tecnología únicamente para resolver una limitación producida por datos que finalmente no eran necesarios.

### Decisión final

Se mantuvo:

```text
gemini-embedding-2
768 dimensiones
```

---

# 7. Persistencia de artefactos

Una decisión importante durante la revisión fue **no repetir procesos costosos cuando sus resultados ya existen**.

Se persisten:

```text
output/chunks.json
output/embeddings.json
```

El artefacto de embeddings contiene la correspondencia:

```text
texto
↔ metadata
↔ embedding
```

Las pruebas finales comprobaron:

```text
Chunks:              712
Embeddings:          712
Dimensiones:         768
Correspondencia:     correcta
Valores numéricos:   correctos
```

El resultado de la validación fue:

```text
EMBEDDINGS VÁLIDOS
```

De esta forma, reconstruir posteriormente ChromaDB no requiere volver a llamar a la API de embeddings.

---

# 8. ChromaDB

Los embeddings se almacenan en una colección persistente:

```text
residuos_madrid
```

La indexación final fue validada comprobando:

* 712 registros;
* IDs únicos;
* documentos no vacíos;
* metadatos presentes;
* fuente presente en metadata;
* tipo documental presente;
* embeddings de 768 dimensiones;
* valores numéricos finitos;
* correspondencia exacta entre `embeddings.json` y ChromaDB.

El resultado fue:

```text
INDEXACIÓN VÁLIDA
```

La separación entre embeddings e índice permite reconstruir ChromaDB sin volver a generar los vectores.

---

# 9. Integración del retrieval desarrollado por Pol

Pol desarrolló la primera implementación y evaluación del retrieval.

La versión inicial permitió probar distintos valores de K y detectar los principales casos problemáticos.

Sobre el conjunto inicial de evaluación se obtuvieron aproximadamente:

| K  | Aciertos |
| -- | -------: |
| 3  |     7/10 |
| 5  |     8/10 |
| 8  |     8/10 |
| 10 |     8/10 |

Ya en esa fase se observó que aumentar K por encima de 5 no producía una mejora.

También se identificaron dos preguntas especialmente difíciles:

* punto limpio fijo en Arganzuela;
* tipos de residuos reconocidos por el Ayuntamiento.

---

# 10. Experimentos adicionales de retrieval

Durante la integración se compararon varias estrategias.

## 10.1. Embedding directo de la pregunta

La pregunta se envía directamente al modelo de embeddings.

Ejemplo:

```text
¿Dónde hay un punto limpio fijo en el distrito de Arganzuela?
```

Esta variante terminó ofreciendo el mejor comportamiento global.

---

## 10.2. Formato específico de question answering

También se probó preparar la consulta como:

```text
task: question answering | query: {pregunta}
```

El objetivo era orientar explícitamente el embedding hacia tareas de recuperación para pregunta-respuesta.

Sin embargo, las pruebas no demostraron una mejora global frente al embedding directo.

---

## 10.3. Reranking híbrido

Se desarrolló también un retrieval híbrido combinando:

```text
similitud semántica
+
coincidencia léxica
```

con una ponderación experimental:

```text
0.70 × semantic_score
+
0.30 × lexical_score
```

El reranking logró mejorar algunos casos concretos, especialmente la consulta sobre Arganzuela.

Sin embargo, al evaluar el conjunto completo se observó que mejoraba casos individuales a costa de empeorar otros.

Resultados comparativos observados durante la experimentación:

```text
semantic original       → 8/10
semantic QA             → 7/10
hybrid QA               → 7/10
hybrid original         → 7/10
```

### Decisión final

Se conservó el código experimental para trazabilidad, pero el flujo RAG final utiliza:

```text
embedding directo de la pregunta
+
retrieval semántico de ChromaDB
```

No se utiliza el reranking híbrido como retrieval de producción.

Esta decisión se basa en rendimiento global observado, no en el rendimiento de una única consulta.

---

# 11. Evaluación definitiva de K

Durante la revisión final se unificó el conjunto de evaluación en:

```text
queries/eval_queries.json
```

El dataset definitivo contiene:

```text
14 preguntas
```

de las cuales:

```text
11 son respondibles con el corpus
3 están fuera de dominio
```

Se regeneraron los embeddings de esas preguntas y se persistieron para poder repetir experimentos sin nuevas llamadas a Gemini.

La evaluación final del retrieval produjo:

| K  | Aciertos |   Tasa |
| -- | -------: | -----: |
| 3  |     8/11 | 72,7 % |
| 5  |     9/11 | 81,8 % |
| 8  |     9/11 | 81,8 % |
| 10 |     9/11 | 81,8 % |

### Decisión final

Se mantiene:

```python
TOP_K = 5
```

K=8 y K=10 no recuperan más fuentes correctas que K=5.

Aumentar K solo implica:

* mayor contexto enviado al modelo;
* más ruido potencial;
* mayor número de tokens;
* mayor coste de generación.

Por tanto, K=5 proporciona el mismo rendimiento observado con menor cantidad de contexto.

---

# 12. Caché de embeddings de evaluación

Durante la revisión se detectó que repetir evaluaciones podía provocar llamadas de embeddings innecesarias.

Se añadió:

```text
output/cache/eval_query_embeddings.json
```

Las 14 preguntas se embeben una vez y esos vectores se reutilizan posteriormente para:

* evaluación con K=3;
* K=5;
* K=8;
* K=10;
* evaluación end-to-end del RAG.

De esta forma:

```text
14 preguntas
→ 14 embeddings
```

en lugar de regenerarlos en cada ejecución.

El helper utilizado para esta función se mantiene separado de los tests específicos para evitar duplicar lógica.

---

# 13. Integración de generación desarrollada por Mihaela

Mihaela desarrolló la parte de generación y una primera estructura de evaluación.

Durante la integración se revisó `generate.py` para asegurar que la generación cumplía el requisito principal del proyecto: **responder exclusivamente con el contexto recuperado**.

El prompt contiene instrucciones explícitas:

* utilizar únicamente el contexto;
* no utilizar conocimiento externo;
* no inventar información;
* no completar datos ausentes;
* responder de forma clara;
* abstenerse cuando el contexto sea insuficiente.

La pregunta y el contexto se delimitan de forma explícita.

---

# 14. Abstención

Se definió un mensaje único:

```text
No puedo responder con la información disponible en los documentos.
```

El sistema debe devolver exactamente ese mensaje cuando el contexto no permita responder.

Además, si retrieval no devuelve ningún contexto, `generate.py` devuelve directamente la abstención sin consumir una llamada al modelo generativo.

Esta decisión reduce coste y evita llamadas innecesarias.

---

# 15. Gestión de errores del modelo generativo

Durante pruebas previas aparecieron errores temporales:

```text
429 TooManyRequests
503 ServiceUnavailable
```

Para mejorar la robustez se incorporaron reintentos para:

```text
429
500
502
503
504
```

utilizando backoff exponencial.

La configuración final utiliza:

```text
GENERATION_MODEL = "gemini-3.1-flash-lite"
```

Se mantuvo este modelo por su equilibrio entre velocidad, disponibilidad y coste para una aplicación RAG pequeña.

---

# 16. API interna del RAG

Durante la integración se centralizó el flujo completo en:

```python
responder(pregunta, k=TOP_K, ...)
```

La función realiza:

```text
pregunta
    ↓
embedding
    ↓
retrieval
    ↓
chunks
    ↓
contexto
    ↓
generación
    ↓
fuentes
```

y devuelve un diccionario estructurado.

Después de la revisión, el resultado incluye:

```python
{
    "answer": ...,
    "sources": ...,
    "chunks": ...,
    "metrics": ...
}
```

Esta API permite utilizar exactamente la misma lógica desde:

* CLI;
* tests;
* Streamlit.

---

# 17. CLI

Se consolidó `main.py` como interfaz por terminal.

Las principales operaciones son:

```bash
python main.py --index
```

Reconstruye ChromaDB utilizando los embeddings persistidos.

```bash
python main.py --query "pregunta" --k 5
```

Ejecuta únicamente retrieval.

```bash
python main.py --ask "pregunta"
```

Ejecuta el flujo RAG completo.

Esto mantiene separadas:

```text
indexación
consulta
generación
```

tal como se exige en la arquitectura del proyecto.

---

# 18. Revisión y consolidación de la evaluación

Tras integrar el trabajo de retrieval y generación se detectó que existían varios archivos de evaluación con funciones parcialmente solapadas.

Se decidió consolidarlos en un único dataset:

```text
queries/eval_queries.json
```

La versión definitiva contiene:

```text
14 consultas
11 respondibles
3 OOD
```

Cada consulta especifica:

```text
id
categoría
pregunta
es_respondible
fuentes_esperadas
```

Esto permite utilizar el mismo conjunto tanto para retrieval como para generación.

Los resultados de las pruebas se mantienen fuera de `queries/`, ya que `queries/` debe contener únicamente las entradas de evaluación.

---

# 19. Evaluación end-to-end definitiva

Se ejecutó el RAG completo con:

```text
K = 5
14 preguntas
```

Resultado:

```text
Preguntas totales:             14
Errores de ejecución:           0
Preguntas respondibles:         11
Fuente esperada recuperada:     9/11
Respondidas sin abstención:     9/11
Preguntas fuera de dominio:      3
Abstenciones correctas OOD:      3/3
```

Por tanto:

```text
retrieval esperado:       81,8 %
respuestas in-domain:     81,8 %
abstención OOD:          100 %
errores de ejecución:       0
```

La abstención ante preguntas fuera del corpus funcionó correctamente en todos los casos evaluados.

---

# 20. Ejemplos de funcionamiento correcto

## 20.1. Vidrio

Pregunta:

```text
¿En qué contenedor tiro una botella de vidrio?
```

Respuesta:

```text
Debes depositarla en el contenedor verde.
```

Fuentes recuperadas:

```text
fraccion_vidrio.html
tipos_residuos.csv
```

La respuesta está directamente respaldada por el contexto.

---

## 20.2. Aceite vegetal usado

Pregunta:

```text
¿Dónde puedo tirar el aceite vegetal usado de la cocina?
```

El sistema recuperó:

```text
recogida_aceite_vegetal.html
tipos_residuos.csv
```

y respondió utilizando únicamente esos documentos.

---

## 20.3. Punto limpio fijo de Hortaleza

Pregunta:

```text
¿Cuál es la dirección del punto limpio fijo de Hortaleza?
```

Respuesta:

```text
Calle Tomas Redondo 8.
```

Entre las fuentes recuperadas se encontraba:

```text
puntos_limpios_fijos.csv
```

---

# 21. Evaluación de abstención

Las tres preguntas OOD definitivas fueron:

```text
¿Cuál es el horario de las piscinas municipales de Madrid?
```

```text
¿Dónde reciclo el vidrio en Barcelona?
```

```text
¿Qué servicios de reparación de móviles hay cerca de Gran Vía?
```

En los tres casos el retrieval recuperó algún documento por similitud vectorial, ya que ChromaDB siempre devuelve los elementos más cercanos.

Sin embargo, el generador detectó que el contexto no contenía información suficiente y respondió:

```text
No puedo responder con la información disponible en los documentos.
```

Resultado:

```text
3/3 abstenciones correctas
```

Este comportamiento es especialmente importante porque evita una de las principales fuentes de error de un sistema RAG: generar una respuesta plausible utilizando información que no existe en el corpus.

---

# 22. Fallos observados en la evaluación final

La evaluación definitiva permitió identificar tres limitaciones relevantes.

## Fallo 1 — Contenedor gris de restos

Pregunta:

```text
¿Qué va en el contenedor gris de restos?
```

Retrieval recuperó correctamente:

```text
fraccion_resto.html
```

junto con otras fuentes relacionadas.

Por tanto:

```text
retrieval → correcto
generación → abstención
```

El modelo respondió:

```text
No puedo responder con la información disponible en los documentos.
```

aunque existía una fuente relevante.

### Interpretación

El fallo no está en la indexación ni en retrieval, sino en la interpretación que realiza el modelo generativo del contexto recuperado.

### Mejora futura

* revisar el contenido limpio de `fraccion_resto.html`;
* comprobar cómo aparece expresada la información relevante;
* estudiar pequeñas mejoras en el prompt antes de aumentar K.

---

## Fallo 2 — Punto limpio fijo de Arganzuela

Pregunta:

```text
¿Dónde hay un punto limpio fijo en el distrito de Arganzuela?
```

El retrieval final recuperó:

```text
puntos_limpios_proximidad.csv
puntos_limpios_moviles.csv
```

pero no las fuentes esperadas:

```text
puntos_limpios_fijos.csv
residuos_punto_limpio_fijo.html
```

El modelo respondió utilizando puntos limpios de proximidad y los describió como puntos fijos.

### Interpretación

Aquí el problema principal se encuentra en retrieval.

Existe una fuerte similitud entre:

```text
punto limpio fijo
punto limpio móvil
punto limpio de proximidad
```

y la recuperación semántica no distingue siempre correctamente esas categorías.

Los experimentos híbridos desarrollados durante el trabajo de Pol lograron mejorar específicamente este caso, pero empeoraban el rendimiento global del conjunto de evaluación.

### Mejora futura

* introducir filtros de metadata por tipo de punto;
* reforzar entidades como distrito y tipo de instalación;
* estudiar reranking solo cuando la consulta incluya categorías muy concretas.

---

## Fallo 3 — Tipos de residuos del Ayuntamiento

Pregunta:

```text
¿Qué tipos de residuos reconoce el Ayuntamiento de Madrid?
```

La fuente esperada era:

```text
tipos_residuos.csv
```

pero no apareció entre los cinco primeros resultados.

El sistema terminó absteniéndose.

### Interpretación

La consulta es muy general y compite con numerosos documentos que contienen terminología relacionada con residuos.

### Mejora futura

* mejorar la representación de documentos estructurados;
* crear chunks de resumen para datasets tabulares;
* incorporar metadata o filtros;
* estudiar consultas de recuperación específicas para preguntas agregadas.

---

# 23. Decisión de no optimizar los fallos únicamente para la evaluación

Durante la revisión se decidió no modificar artificialmente el sistema para conseguir un resultado perfecto sobre las 14 preguntas.

Las tres limitaciones observadas son información útil sobre el comportamiento real del RAG.

Modificar el retrieval específicamente para resolver esas preguntas podría producir sobreajuste al conjunto de evaluación y empeorar otras consultas.

Se prefirió conservar:

```text
K = 5
retrieval semántico directo
```

y documentar de forma transparente las limitaciones.

---

# 24. Logging y métricas

El enunciado requiere registrar:

* pregunta;
* K;
* número de chunks;
* tiempo;
* modelo.

Se implementó un registro JSONL en:

```text
output/logs/rag.jsonl
```

Cada ejecución almacena aproximadamente:

```json
{
  "timestamp": "...",
  "question": "...",
  "k": 5,
  "num_chunks": 5,
  "time_seconds": 1.234,
  "model": "gemini-3.1-flash-lite"
}
```

Estas mismas métricas se incorporan al resultado de `responder()`:

```python
"metrics": {
    "k": 5,
    "num_chunks": 5,
    "time_seconds": ...,
    "model": "gemini-3.1-flash-lite"
}
```

Esto permite reutilizarlas posteriormente en Streamlit sin duplicar cálculos.

---

# 25. Streamlit y aplicación web

Antes de la integración definitiva del RAG ya se había desarrollado una interfaz Streamlit con:

* pantalla inicial;
* registro;
* login;
* autenticación;
* sesiones;
* logout;
* historial visual de mensajes;
* `st.chat_input`;
* vista privada del asistente.

También se desarrolló una pequeña base SQLite para usuarios.

La autenticación incluye:

* normalización de email;
* validación de campos;
* código postal;
* validación de contraseña;
* hash mediante `bcrypt`;
* email único;
* estado activo de usuario.

Estas funcionalidades exceden los requisitos mínimos del ejercicio, pero se mantienen porque ya están desarrolladas y separadas correctamente del RAG.

Durante la revisión se detectó además una funcionalidad experimental de **modos de consulta**:

```text
Automático
Clasificar residuo
Cómo reciclarlo
Información sobre contenedores
Información sobre puntos limpios
```

Estos modos no modificaban realmente retrieval ni generación y únicamente añadían complejidad a la interfaz.

La decisión para la versión final es simplificar esta parte y utilizar una única entrada de consulta que delegue directamente en el RAG.

---

# 26. Decisiones de simplificación tomadas durante la revisión

La revisión general tuvo como objetivo no solo corregir errores, sino eliminar complejidad innecesaria.

Entre las principales decisiones:

### 26.1. Un único dataset de evaluación

Antes existían varios archivos con funciones solapadas.

Se consolidaron en:

```text
queries/eval_queries.json
```

---

### 26.2. Un único retrieval de producción

Se conservaron experimentos QA e híbridos únicamente como trazabilidad.

Producción utiliza:

```text
embedding directo
+
retrieval semántico
+
K=5
```

---

### 26.3. Persistencia de embeddings

No se regeneran embeddings del corpus para reconstruir el índice.

```text
embeddings.json
→ ChromaDB
```

---

### 26.4. Persistencia de embeddings de evaluación

Las consultas de evaluación también se embeben una única vez.

---

### 26.5. API única

CLI, tests y Streamlit deben utilizar:

```python
responder()
```

en vez de replicar el pipeline.

---

### 26.6. No añadir funcionalidades fuera de alcance

Para la entrega no se desarrollarán:

* geolocalización;
* rutas;
* modos especializados;
* recomendación del punto más cercano;
* persistencia completa de conversaciones;
* selección dinámica de modelos.

El objetivo es cerrar correctamente el RAG solicitado antes de ampliar producto.

---

# 27. Configuración final

| Componente               | Configuración final            |
| ------------------------ | ------------------------------ |
| Dominio                  | Residuos y reciclaje de Madrid |
| Fuentes                  | 15                             |
| Formatos                 | CSV + HTML                     |
| Documentos limpios       | 691                            |
| Chunk size               | 1000                           |
| Chunk overlap            | 100                            |
| Chunks                   | 712                            |
| Modelo embeddings        | `gemini-embedding-2`           |
| Dimensionalidad          | 768                            |
| Vector store             | ChromaDB                       |
| Colección                | `residuos_madrid`              |
| Métrica                  | Cosine                         |
| Retrieval                | Semántico                      |
| Embedding de consulta    | Pregunta directa               |
| K por defecto            | 5                              |
| Generación               | `gemini-3.1-flash-lite`        |
| Abstención               | Mensaje explícito              |
| Dataset evaluación       | 14 preguntas                   |
| Preguntas in-domain      | 11                             |
| Preguntas OOD            | 3                              |
| Retrieval final          | 9/11 — 81,8 %                  |
| Respuestas in-domain     | 9/11 — 81,8 %                  |
| Abstención OOD           | 3/3 — 100 %                    |
| Errores evaluación final | 0                              |
| Logging                  | JSONL                          |
| Interfaz                 | Streamlit                      |

---

# 28. Conclusiones

La revisión final permitió transformar varias partes desarrolladas de forma relativamente independiente en un único flujo RAG coherente.

La integración del retrieval desarrollado por Pol permitió disponer de una primera evaluación sistemática de K y experimentar con diferentes estrategias de recuperación.

Los experimentos posteriores mostraron que técnicas más complejas, como el reranking híbrido o el formato QA para embeddings de consulta, podían mejorar casos concretos pero no el rendimiento global. Por ello se mantuvo como solución final el retrieval semántico directo con K=5.

La generación desarrollada por Mihaela proporcionó la base para la respuesta fundamentada y la abstención. Durante la integración se reforzó el contrato del prompt, la gestión de errores, la reutilización del cliente y la evaluación end-to-end.

La revisión conjunta permitió además:

* consolidar el conjunto de evaluación;
* eliminar archivos redundantes;
* reutilizar embeddings;
* separar entradas de evaluación de resultados;
* validar embeddings e índice;
* incorporar logging;
* establecer una API interna única;
* documentar de forma reproducible los experimentos.

Los resultados finales muestran:

```text
retrieval correcto en 9/11 consultas respondibles
respuesta sin abstención en 9/11 consultas respondibles
abstención correcta en 3/3 consultas fuera de dominio
0 errores de ejecución en la evaluación final
```

Los fallos restantes están identificados y documentados, principalmente relacionados con:

* distinción entre tipos similares de puntos limpios;
* recuperación de preguntas agregadas;
* interpretación del contexto por parte del modelo generativo.

Estos fallos no impiden demostrar el funcionamiento completo del sistema y proporcionan una base clara para futuras mejoras sin introducir optimizaciones específicas orientadas únicamente a superar el conjunto de evaluación.
