# Decisión sobre el corpus de la V1

## 1. Contexto

Durante la fase de ingesta, limpieza y chunking del proyecto se incorporaron inicialmente 19 fuentes de datos relacionadas con la gestión de residuos de la ciudad de Madrid.

Entre ellas se encontraba el archivo:

`contenedores_papel_carton_todos.csv`

A pesar de su nombre, este dataset contiene un inventario masivo de contenedores ordinarios de diferentes fracciones de residuos distribuidos por Madrid.

La incorporación de este archivo producía un número muy elevado de documentos y chunks, debido a que cada ubicación se transforma en una unidad semántica independiente.

Con las 19 fuentes iniciales, el pipeline generaba aproximadamente:

- 47.194 chunks
- Más de 47.000 de ellos procedentes de fuentes CSV

## 2. Decisión

Se decide excluir `contenedores_papel_carton_todos.csv` del corpus utilizado en la V1 del sistema.

La V1 seguirá utilizando 18 fuentes:

- 8 archivos CSV
- 10 documentos HTML municipales

Esta decisión no elimina el conocimiento necesario para determinar dónde debe depositarse cada tipo de residuo.

La información conceptual sobre las diferentes fracciones de residuos continúa estando presente en:

- `tipos_residuos.csv`
- La documentación HTML oficial del Ayuntamiento de Madrid
- Los datasets específicos de aceite, pilas, ropa y puntos limpios

Lo que se excluye es principalmente el inventario completo de ubicaciones individuales de los contenedores ordinarios.

## 3. Justificación funcional

El objetivo de la V1 es responder preguntas relacionadas con:

- clasificación de residuos
- contenedor o sistema de recogida adecuado
- puntos limpios
- recogida de aceite vegetal usado
- recogida de pilas
- recogida de ropa y residuos textiles
- puntos limpios fijos
- puntos limpios móviles
- puntos limpios móviles 24 horas
- puntos limpios de proximidad
- documentación municipal sobre gestión de residuos

No forma parte del alcance inicial resolver consultas de geolocalización como:

> ¿Cuál es el contenedor amarillo más cercano a mi ubicación?

Por tanto, almacenar decenas de miles de ubicaciones de contenedores ordinarios no resulta necesario para cumplir los objetivos de esta primera versión.

Esta funcionalidad podrá incorporarse en una versión posterior si se amplía el alcance del asistente.

## 4. Impacto sobre el corpus

Tras eliminar el dataset y volver a ejecutar el pipeline se obtuvieron:

- 18 archivos originales
- 2.914 documentos limpios
- 2.935 chunks

La distribución resultante es:

| Tipo de documento | Chunks |
|---|---:|
| Contenedores de aceite | 123 |
| Contenedores de pilas | 1.492 |
| Contenedores de ropa | 608 |
| Puntos limpios fijos | 16 |
| Puntos limpios móviles | 351 |
| Puntos limpios móviles 24 h | 42 |
| Puntos limpios de proximidad | 95 |
| Relaciones residuo-destino | 177 |
| Documentación municipal | 31 |
| **Total** | **2.935** |

La reducción respecto al corpus inicial es de aproximadamente un 93,8 % en número de chunks.

## 5. Características del corpus resultante

El análisis estadístico de los 2.935 chunks produjo:

- 436.329 caracteres totales
- 64.499 palabras
- 148,66 caracteres de media por chunk
- 135 caracteres de mediana
- 41 caracteres en el chunk más pequeño
- 997 caracteres en el chunk más grande

La estimación orientativa del volumen para embeddings se encuentra entre 109.000 y 145.000 tokens aproximadamente.

La mayor parte de los chunks son registros CSV pequeños que representan entidades completas, mientras que los documentos HTML se dividen mediante chunking en fragmentos de hasta 1.000 caracteres.

## 6. Comprobación de casos atípicos

Durante el análisis se detectó que los chunks de tipo `residuo_destino` tenían una longitud máxima de 679 caracteres, considerablemente superior a su mediana de 92 caracteres.

Se revisó el registro correspondiente y se comprobó que no se trataba de un error del pipeline.

El registro contiene una enumeración extensa de residuos de aparatos eléctricos y electrónicos (RAEE) que comparten un mismo destino: el punto limpio fijo.

Se decide conservar este contenido como una única unidad semántica, ya que dividirlo podría separar los residuos del destino al que pertenecen.

## 7. Consecuencias de la decisión

### Ventajas

- Reducción muy significativa del número de embeddings a generar
- Menor tiempo de procesamiento
- Menor tamaño del índice vectorial
- Menor almacenamiento necesario
- Menor riesgo de que miles de ubicaciones similares introduzcan ruido en el retrieval
- Corpus más alineado con el alcance funcional real de la V1
- Mayor facilidad para realizar experimentos de chunking, embeddings y retrieval

### Limitaciones

La V1 no podrá proporcionar directamente la ubicación exacta del contenedor ordinario más cercano para fracciones como:

- papel y cartón
- vidrio
- orgánica
- resto
- plásticos, metales y briks

El asistente sí podrá explicar qué contenedor corresponde a cada residuo y proporcionar información sobre los sistemas de recogida incluidos en el corpus.

## 8. Decisión final

Se mantiene excluido `contenedores_papel_carton_todos.csv` durante el desarrollo y evaluación de la V1.

El corpus actual de 2.935 chunks se considera suficientemente representativo para continuar con la fase de generación de embeddings.

Si en versiones posteriores se incorpora geolocalización de contenedores ordinarios, el dataset podrá volver a añadirse y se regenerarán los documentos, chunks, embeddings e índice vectorial correspondientes.