# Reglas de reconocimiento textual de estaciones (modo normal)

## Objetivo
El bot debe reconocer la intención del usuario de consultar una estación cuando el texto contiene el nombre de la estación, una variante cercana, o **las tres primeras letras** (prefijo secreto) **al inicio del mensaje**.

## Comportamiento general

| Tipo de entrada | Ejemplo | ¿Reconoce? |
|----------------|---------|-------------|
| Nombre exacto | `galatea` | ✅ Sí |
| Mayúsculas/minúsculas | `GALATEA`, `Galatea` | ✅ Sí |
| Error tipográfico cercano | `galaxia` (para Galatea) | ✅ Sí |
| **Prefijo de 3 letras al inicio** | `gal` (como palabra completa) | ✅ Sí |
| **Prefijo de 3 letras al inicio seguido de más texto** | `galabunu` | ✅ Sí (porque empieza con "gal") |
| Prefijo dentro de una frase (no al inicio) | `sabes donde esta galabunu?` | ❌ No (el texto no empieza con "gal") |
| Dentro de una frase (nombre completo) | `hola para ir a galatea?` | ✅ Sí (porque contiene "galatea") |
| Palabra no reconocida | `galatino` | ❌ No (a menos que empiece con "gal" y el texto completo sea "galatino"? En realidad "galatino" empieza con "gal", por lo que si es el inicio del mensaje, SÍ se reconocería) |
| Múltiples estaciones | `galatea y stesicoro` | ✅ Solo la primera encontrada |
| Estación al inicio | `como era galatea o montepo` | ✅ Reconoce Galatea primero |

## Variantes y prefijos predefinidos (ejemplo para Galatea)

- Nombres completos: `galatea`
- Errores comunes: `galaxia`
- Prefijos secretos (tres primeras letras) **solo si aparecen al inicio del mensaje**: `gal` (cualquier mensaje que empiece con "gal" se interpreta como Galatea, independientemente de lo que venga después)

**Nota:** Los prefijos de tres letras son un truco de accesibilidad y **no deben mostrarse nunca al usuario** en el modo normal. Solo se mencionan aquí para documentación interna.

## Lógica de implementación
- Se normaliza el texto eliminando tildes y convirtiendo a minúsculas.
- Se busca **primero** coincidencia exacta con el nombre completo o variantes en cualquier parte del texto.
- Si no hay coincidencia exacta, se comprueba si el texto **empieza** por el prefijo de tres letras de alguna estación.
- El orden de búsqueda es por longitud descendente (ej. "Giovanni XXIII" antes que "Giovanni").
- Los prefijos de tres letras son secretos: no se mencionan en los mensajes de error ni en la ayuda.
- Si no se reconoce ninguna estación, se responde con un mensaje de error estándar.

## Archivo de configuración
Las listas de variantes y prefijos se mantendrán en un archivo `variantes_estaciones.json` en el futuro. Por ahora, están codificadas en `handlers_dev.py`.
