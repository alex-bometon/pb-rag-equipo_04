# Decisión técnica: generación de embeddings para la V1 del RAG

## 1. Objetivo de este documento

Este documento registra las decisiones técnicas tomadas durante la fase de embeddings del proyecto `pb-rag-equipo_04`, desde la preparación del corpus y la primera implementación con Google Gemini hasta la decisión de descartar Gemini Embedding 2 para esta fase y estudiar una alternativa local basada en Hugging Face, con `intfloat/multilingual-e5-base` como candidato principal.

El objetivo es dejar trazabilidad académica y técnica antes de modificar de nuevo `config.py`, `src/embed.py`, `src/artifacts.py` o cualquier otro archivo del pipeline.

**Estado actual:** no se han aplicado todavía cambios para migrar a Hugging Face. La migración queda pendiente de validación final del modelo elegido y de la implementación.

---

## 2. Punto de partida: corpus V1 ya validado

La V1 del sistema se ha limitado deliberadamente a consultas sobre:

- reciclaje
- residuos domésticos y municipales
- dónde depositar residuos
- puntos de recogida específicos
- documentación municipal
- ciudad de Madrid

Se partió de 19 fuentes, pero se excluyó de la V1 el dataset masivo de contenedores ordinarios de papel/cartón, porque el producto no necesita resolver todavía búsquedas geoespaciales del tipo «contenedor ordinario más cercano». La información conceptual sobre tipos de residuos se conserva a través de `tipos_residuos.csv` y la documentación municipal.

El corpus final de V1 quedó compuesto por:

- **18 archivos de origen**
- **2.914 documentos limpios**
- **2.935 chunks**

Distribución de chunks validada:

| Tipo documental | Chunks |
|---|---:|
| contenedor_aceite | 123 |
| contenedor_pilas | 1.492 |
| contenedor_ropa | 608 |
| punto_limpio_fijo | 16 |
| punto_limpio_movil | 351 |
| punto_limpio_movil_24h | 42 |
| punto_limpio_proximidad | 95 |
| residuo_destino | 177 |
| documentacion_municipal | 31 |
| **Total** | **2.935** |

Estadísticas del corpus chunked:

- 436.329 caracteres totales
- media de 148,66 caracteres por chunk
- mediana de 135 caracteres
- chunk mínimo: 41 caracteres
- chunk máximo: 997 caracteres
- 64.499 palabras
- estimación aproximada: 109.000–145.000 tokens

El artefacto `output/chunks.json` fue generado y validado con:

- `schema_version = 1`
- `source_count = 18`
- `total_chunks = 2935`
- `chunk_size = 1000`
- `chunk_overlap = 100`

Este artefacto se fijó como entrada estable de la fase de embeddings.

---

## 3. Arquitectura acordada para la fase de embeddings

Se decidió mantener una separación clara de responsabilidades:

- `config.py`: rutas y configuración
- `src/artifacts.py`: lectura/escritura de artefactos intermedios
- `src/embed.py`: preparación de textos y generación de embeddings
- `src/gemini_client.py`: creación del cliente Gemini mientras Google fuese el proveedor de embeddings

Se descartó crear un `embed_pipeline.py` independiente porque, para la complejidad real de esta fase, suponía una capa adicional sin suficiente beneficio. La orquestación sencilla de la fase podía permanecer en `embed.py`, delegando la persistencia en `artifacts.py`.

---

## 4. Primera decisión de modelo: Google Gemini Embedding 2

### 4.1. Modelo seleccionado inicialmente

Se eligió inicialmente:

```text
Gemini Embedding 2
```

con una dimensionalidad de:

```text
768 dimensiones
```

### 4.2. Motivos de la elección

La decisión inicial se basó en:

- modelo actual de embeddings de Google apto para retrieval/RAG
- buen soporte multilingüe, relevante porque el corpus y las consultas son principalmente en español
- posibilidad de elegir dimensionalidad reducida
- Free Tier disponible
- integración sencilla con `google-genai`
- 768 dimensiones consideradas suficientes para un corpus pequeño y especializado como este

La dimensionalidad de 768 se eligió como compromiso entre:

- calidad semántica
- tamaño de almacenamiento
- coste computacional posterior en ChromaDB

Para 2.935 chunks:

```text
2.935 × 768 = 2.254.080 valores float
```

Se consideró suficiente para la V1, dejando abierta la posibilidad de comparar dimensiones mayores únicamente si las pruebas de retrieval lo justificaban.

---

## 5. Implementación inicial con Gemini

### 5.1. Formato de entrada

Se preparó inicialmente cada documento para embeddings con el formato:

```text
title: {title_or_none} | text: {text}
```

El texto original del chunk se conservaba por separado en el artefacto final para poder recuperarlo posteriormente desde ChromaDB.

### 5.2. Generación individual y por lotes

Se implementaron funciones para:

- preparar el documento
- generar un embedding individual
- generar múltiples embeddings por lotes

El tamaño inicial de lote se fijó en:

```text
EMBED_BATCH_SIZE = 50
```

### 5.3. Problema detectado con el batching

En una primera implementación se envió una lista de strings directamente a `embed_content()`.

Resultado observado:

```text
Se enviaron 50 chunks y se recibió 1 embedding.
```

Se diagnosticó que los textos se estaban interpretando como un único contenido compuesto.

La solución consistió en envolver cada texto en un `types.Content` independiente, con su propio `types.Part`, de forma que:

```text
50 chunks → 50 objetos Content → 50 embeddings
```

Tras esa corrección se validó correctamente una ejecución de prueba de 100 chunks:

- 100 chunks de entrada
- 100 embeddings de salida
- 768 dimensiones por vector
- orden conservado

---

## 6. Artefacto `embeddings.json`

Se decidió guardar el resultado como artefacto intermedio reproducible:

```text
output/embeddings.json
```

Cada item mantiene la asociación:

```text
text ↔ metadata ↔ vector
```

La estructura planteada incluye información como:

- versión del esquema
- modelo de embeddings
- dimensionalidad
- número total de chunks del corpus
- número de embeddings generados
- items con texto, metadata y vector

La persistencia se dejó en `src/artifacts.py` para no mezclar generación de embeddings con escritura de archivos.

---

## 7. Validación de los primeros 100 embeddings

Antes de intentar procesar el corpus completo, se creó una prueba específica bajo:

```text
tests/embeddings/
```

La prueba comprueba sin volver a llamar a la API:

- modelo declarado
- dimensionalidad declarada
- número esperado de embeddings
- presencia de `text`, `metadata` y `vector`
- que todos los vectores tengan 768 valores
- que todos los valores sean numéricos
- correspondencia exacta entre `embeddings.json` y `chunks.json` para texto y metadata

La salida de la prueba se guardó en:

```text
tests/embeddings/results.txt
```

Los 100 embeddings de prueba superaron correctamente todas las comprobaciones.

Conclusión en ese punto:

```text
chunks.json → Gemini → embeddings.json
```

funcionaba correctamente a nivel de integridad y dimensionalidad.

---

## 8. Intento de generación de los 2.935 embeddings

Tras validar los primeros 100 elementos, se eliminó el límite de prueba para intentar procesar todo el corpus.

Durante esta ejecución apareció:

```text
429 RESOURCE_EXHAUSTED
```

El primer error detallado de Google informó explícitamente:

```text
Quota exceeded for metric:
generativelanguage.googleapis.com/embed_content_free_tier_requests

quotaId:
EmbedContentRequestsPerMinutePerUserPerProjectPerModel-FreeTier

quotaValue: 100
model: gemini-embedding-2
```

Además, Google proporcionó un `retryDelay` de aproximadamente 55 segundos.

---

## 9. Investigación del 429

### 9.1. Primer diagnóstico

Inicialmente se estudió la posibilidad de:

- espaciar los lotes
- aplicar reintentos
- usar backoff ante 429
- mantener `EMBED_BATCH_SIZE = 50`

Se llegó a plantear una pausa aproximada de 32 segundos entre lotes para mantener una tasa media inferior a 100 embeddings/minuto.

### 9.2. Reintentos

Se añadió conceptualmente una función auxiliar para:

1. ejecutar un lote
2. capturar `ClientError` con código 429
3. esperar
4. reintentar el mismo lote

Durante esta fase se detectó además una diferencia de versión del SDK: en la instalación local de `google-genai`, el atributo correcto del error era `error.code`, no `error.status_code`.

### 9.3. Confirmación mediante el panel de cuota

El panel de Google mostró:

```text
Gemini Embedding 2
RPM: 100 / 100
TPM: 5,06K / 30K
RPD: 752 / 1K
```

Esto confirmó que el problema no era el volumen de tokens, sino los límites operativos del Free Tier.

Interpretación:

- **RPM = 100/100**: límite por minuto agotado
- **TPM = 5,06K/30K**: amplio margen, por tanto no era el cuello de botella
- **RPD = 752/1K**: límite diario muy avanzado

---

## 10. Hallazgo decisivo: límite diario insuficiente

El límite diario observado fue:

```text
1.000 embeddings/día
```

El corpus necesita:

```text
2.935 embeddings
```

Por tanto, incluso gestionando perfectamente el RPM:

```text
2.935 / 1.000 ≈ 2,94 días
```

La generación completa requeriría como mínimo tres ventanas diarias de cuota.

Además, la implementación existente guardaba el artefacto definitivo al finalizar la generación completa. Esto implicaba que, si la API fallaba después de varios cientos de embeddings, la cuota consumida podía perderse desde el punto de vista del artefacto persistido.

Se consideró implementar:

- checkpoints
- guardado por lotes
- reanudación desde el último chunk generado
- gestión de límites diarios y por minuto

Sin embargo, esta solución añadía complejidad al proyecto únicamente para adaptarse a las restricciones del proveedor, no por una necesidad funcional del RAG.

---

## 11. Decisión: descartar Gemini Embedding 2 para la fase de embeddings

Se decide **descartar Gemini Embedding 2 como modelo de embeddings para la V1**.

Esta decisión **no se debe a problemas de calidad semántica del modelo**. La implementación quedó técnicamente validada con 100 chunks.

El motivo es operativo:

1. límite de 100 embeddings por minuto
2. límite de 1.000 embeddings diarios en el Free Tier observado
3. corpus de 2.935 chunks
4. necesidad de varios días para una única generación completa
5. necesidad adicional de implementar checkpoints y reanudación para evitar perder trabajo
6. posible repetición futura de embeddings al modificar corpus, chunking o modelo
7. dependencia innecesaria de una API externa para una tarea que puede ejecutarse localmente

Para un proyecto académico de este tamaño, la complejidad añadida no se considera justificada.

---

## 12. Nuevo criterio de selección

Se redefine el requisito para la fase de embeddings:

El modelo debe ser:

- apto para semantic search / retrieval
- multilingüe y competente en español
- capaz de procesar los 2.935 chunks sin cuotas por minuto o por día
- gratuito para este proyecto
- reproducible localmente
- compatible con Sentence Transformers o una librería equivalente
- adecuado para ChromaDB
- suficientemente ligero para volver a generar todos los embeddings cuando sea necesario

Esto desplaza la arquitectura desde una API remota hacia inferencia local.

---

## 13. Hugging Face: API alojada frente a ejecución local

Se estudió Hugging Face como alternativa.

### 13.1. Inference Providers

No se considera la opción principal porque las cuentas gratuitas disponen actualmente de una cantidad pequeña de crédito mensual para Inference Providers. Esto volvería a introducir dependencia de cuota y facturación.

Por tanto, no se pretende sustituir simplemente:

```text
Gemini API → Hugging Face API
```

### 13.2. Ejecución local

La alternativa preferida es:

```text
Hugging Face Hub
        ↓
descarga del modelo una vez
        ↓
Sentence Transformers
        ↓
inferencia local en el Mac
        ↓
2.935 embeddings
```

Ventajas:

- sin RPM
- sin RPD
- sin coste por embedding
- sin necesidad de API key para la inferencia local
- posibilidad de regenerar el corpus completo tantas veces como sea necesario
- reproducibilidad más alta para el proyecto académico

---

## 14. Modelos considerados

### 14.1. `intfloat/multilingual-e5-small`

Características relevantes:

- multilingüe
- licencia MIT
- compatible con Sentence Transformers
- embeddings de 384 dimensiones
- pesos de aproximadamente 471 MB
- orientado a recuperación semántica

Ventaja principal: consumo reducido de memoria y mayor velocidad.

Inconveniente: menor dimensionalidad y capacidad que la variante `base`.

### 14.2. `intfloat/multilingual-e5-base`

Características relevantes:

- multilingüe
- licencia MIT
- compatible con Sentence Transformers
- hidden size / embedding size de 768
- pesos de aproximadamente 1,11 GB
- longitud máxima de 512 tokens
- específicamente diseñado para embeddings y recuperación semántica.

Para este corpus, el límite de 512 tokens no supone un problema relevante porque los chunks actuales tienen como máximo 997 caracteres, muy por debajo de ese límite en la práctica.

Una ventaja adicional es que mantiene las **768 dimensiones** que ya se habían adoptado para Gemini, por lo que el diseño conceptual del artefacto y del futuro índice puede mantenerse sin aumentar dimensionalidad.

### 14.3. `BAAI/bge-m3`

Características relevantes:

- multilingüe
- 1.024 dimensiones
- hasta 8.192 tokens
- soporte para retrieval dense, sparse y multi-vector
- modelo considerablemente más pesado

Se considera técnicamente potente, pero sobredimensionado para la V1 actual:

- el corpus es pequeño
- los chunks son cortos
- no se necesita contexto de miles de tokens por chunk
- no se ha planteado todavía retrieval híbrido dense+sparse+ColBERT
- supone más consumo de memoria y almacenamiento

---

## 15. Candidato principal: `intfloat/multilingual-e5-base`

Antes de modificar el código, el candidato principal queda fijado como:

```text
intfloat/multilingual-e5-base
```

Motivos:

1. está diseñado específicamente para embeddings y retrieval
2. es multilingüe y adecuado para español
3. licencia MIT
4. ejecución local, sin cuotas de API
5. 768 dimensiones, coherentes con el diseño anterior
6. tamaño asumible para el equipo local disponible
7. suficiente para 2.935 chunks relativamente pequeños
8. integración directa con `sentence-transformers`
9. permite regenerar el corpus completo cuando cambie el chunking o el contenido

Esta selección es **provisional hasta completar una prueba local de carga, generación de embeddings e inspección de retrieval**.

---

## 16. Diferencia semántica importante respecto a Gemini

E5 tiene una convención de entrada propia para tareas de retrieval.

Para documentos:

```text
passage: <contenido>
```

Para consultas:

```text
query: <consulta del usuario>
```

Por tanto, la futura implementación deberá diferenciar explícitamente:

```text
chunk/documento → passage:
consulta         → query:
```

Esto reemplazaría el formato provisional utilizado con Gemini:

```text
title: {title_or_none} | text: {text}
```

El cambio deberá quedar reflejado también en los metadatos del artefacto de embeddings para garantizar reproducibilidad.

---

## 17. Decisión al cierre de esta fase

La implementación con Gemini ha cumplido su función de validar el diseño de la fase de embeddings, el batching, la estructura del artefacto y las pruebas de integridad. Sin embargo, los límites reales observados del Free Tier convierten a Gemini Embedding 2 en una opción poco práctica para generar y regenerar el corpus completo de esta V1.

La siguiente fase no debe comenzar modificando código directamente. Primero se validará la alternativa local, con `intfloat/multilingual-e5-base` como candidato principal. Una vez confirmada, se documentará la configuración definitiva y sólo entonces se adaptarán `config.py`, `src/embed.py`, `src/artifacts.py`, dependencias y tests.
