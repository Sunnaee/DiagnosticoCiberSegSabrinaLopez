# Diagnóstico - Ciberseguridad
#### Estudiante: Sabrina López

---

## Miner de palabras utilizadas en funciones en repositorios de Github

Para efectos prácticos, se buscó la url usada por la api de Github para obtener los [50 repositorios ordenados por el mayor número de estrellas](https://api.github.com/search/repositories?q=stars:>1&sort=stars&order=desc&per_page=50). En el top 50 hay muchos repositorios con lenguaje python y se encontró al menos 1 de java, por eso se escogió ese número.

Las palabras se almacenan en un archivo counts.json para asegurar que no se pierdan datos. Se tuvo precaución con la frecuencia de las solicitudes a la api para evitar que se excediera el límite permitido sin token. Sólo se cuentan las palabras de las funciones de archivos _.py_ (parseo con _ast_) o _.java_ (mediante _regex_). Para la lectura de los contenidos, utiliza la api _git/trees_, descarga los archivos desde _raw.githubusercontent.com_, y hace las llamadas HTTP con _requests_.
Se apoyó con IA para entender herramientas que se podían usar y manejo de errores.

## Visualizer

Para visualizar la información, se utilizó websocket para comunicarla. Los repositorios procesados se guardan en processed.json para no generar duplicados en el conteo, evitando leer repositorios más de una vez.
Se utilizó mayor contribución de IA para esta funcionalidad.

## Uso con Docker
1. docker-compose up --build
2. Abrir: http://localhost:4000