# Reglas de reconocimiento textual de estaciones (modo normal)

## Objetivo
El bot debe reconocer la intención del usuario de consultar una estación cuando el texto contiene el nombre de la estación o una variante muy cercana, en cualquier parte del mensaje, sin importar mayúsculas/minúsculas.

## Comportamiento general

| Tipo de entrada | Ejemplo | ¿Reconoce? |
|----------------|---------|-------------|
| Nombre exacto | `galatea` | ✅ Sí |
| Mayúsculas/minúsculas | `GALATEA`, `Galatea` | ✅ Sí |
| Error tipográfico cercano | `galaxia` (para Galatea) | ✅ Sí (si está en la lista de variantes) |
| Dentro de una frase | `hola para ir a galatea?` | ✅ Sí |
| Palabra no reconocida | `galatino` | ❌ No |
| Múltiples estaciones | `galatea y stesicoro` | ✅ Solo la primera encontrada |
| Estación al inicio | `como era galatea o montepo` | ✅ Reconoce Galatea primero |

## Variantes predefinidas (por estación)

Cada estación puede tener una lista de sinónimos o errores comunes que se consideran válidos. Ejemplo para Galatea:
- galatea, galaxia, galate, galat

## Lógica de implementación
- Se normaliza el texto eliminando tildes y convirtiendo a minúsculas.
- Se busca la primera coincidencia con el nombre completo o variante.
- El orden de búsqueda es por longitud descendente (ej. "Giovanni XXIII" antes que "Giovanni").
- No se revelan los trucos de prefijos de tres letras en modo normal.
- Si no se reconoce ninguna estación, se responde con un mensaje de error estándar.

## Archivo de configuración
Las listas de variantes se mantendrán en un archivo `variantes_estaciones.json` en el futuro. Por ahora, están codificadas en `handlers_dev.py`.
