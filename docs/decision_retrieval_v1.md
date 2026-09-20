# Decisión sobre el retrieval de la V1

## 1. Contexto

Se ha implementado `retrieve.py` sobre el índice ChromaDB ya construido
en el bloque de corpus/embeddings (712 chunks, modelo
`gemini-embedding-2`, 768 dimensiones, métrica coseno).

Para validar el retrieval se ha creado un conjunto de 12 preguntas de
evaluación (`queries/eval_queries.json`), cubriendo los 5 tipos de
consulta descritos en `docs/dominio.md` (destino de un residuo,
separación de residuos, puntos de recogida, servicios de recogida,
residuos domésticos especiales), más 2 preguntas fuera de dominio para
comprobar el comportamiento cuando no hay información relevante.

## 2. Experimento K

Se ha comparado la tasa de acierto (si al menos una de las fuentes
esperadas aparece entre los chunks recuperados) para distintos valores
de `TOP_K`, sobre las 10 preguntas respondibles:

| K  | Aciertos | Tasa |
|----|----------|------|
| 3  | 7/10     | 70%  |
| 5  | 8/10     | 80%  |
| 8  | 8/10     | 80%  |
| 10 | 8/10     | 80%  |

## 3. Decisión

Se fija `TOP_K = 5` como valor por defecto en `config.py`.

Justificación: aumentar K por encima de 5 no mejora la tasa de acierto
(se mantiene en 80% hasta K=10), por lo que los fallos no se deben a
recuperar pocos resultados, sino a que esos chunks concretos no están
entre los más cercanos en el espacio vectorial. Subir K solo añadiría
coste y ruido innecesario al contexto que recibirá el LLM en la fase
de generación.

## 4. Casos que no recuperan la fuente esperada

- **"¿Dónde hay un punto limpio fijo en el distrito de Arganzuela?"**
  (esperado: `puntos_limpios_fijos.csv` / `residuos_punto_limpio_fijo.html`)
- **"¿Qué tipos de residuos reconoce el Ayuntamiento de Madrid?"**
  (esperado: `tipos_residuos.csv`)

Ambas son preguntas relativamente genéricas frente a chunks muy
específicos (filas individuales de CSV). No se considera bloqueante
para la V1: queda documentado como posible mejora futura (revisar
chunking/embeddings de esas fuentes, o reformular las preguntas de
evaluación para que sean más específicas).

## 5. Preguntas fuera de dominio

Las 2 preguntas fuera de dominio ("piscinas municipales", "reciclar en
Barcelona") sí devuelven resultados de ChromaDB, con distancias más
altas que las preguntas respondibles (0.28–0.34 frente a 0.20–0.28).
El retrieval, por diseño, siempre devuelve los `top_k` más cercanos,
aunque no sean relevantes: la decisión de abstenerse ("no lo sé") no
corresponde a esta fase, sino a `generate.py`, que deberá aplicar un
criterio sobre la distancia/relevancia antes de responder.
