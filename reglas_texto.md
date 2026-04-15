# Reglas de reconocimiento textual de estaciones (modo normal)

## Objetivo
El bot debe reconocer la intención del usuario de consultar una estación cuando:
- El texto contiene el nombre completo de la estación (en cualquier posición).
- El texto contiene una variante cercana (error tipográfico) en cualquier posición.
- El texto **empieza** con las tres primeras letras (prefijo secreto) de la estación.

## Comportamiento general

| Tipo de entrada | Ejemplo | ¿Reconoce? |
|----------------|---------|-------------|
| Nombre exacto (cualquier posición) | `galatea`, `quiero ir a galatea` | ✅ Sí |
| Variante cercana (cualquier posición) | `galaxia` (para Galatea) | ✅ Sí |
| **Prefijo de 3 letras al inicio del texto** | `gal`, `galaxia` (como palabra inicial) | ✅ Sí |
| **Prefijo de 3 letras al inicio, seguido de más texto** | `galabunu`, `galatea es bonita` | ✅ Sí |
| Prefijo dentro de una frase (no al inicio) | `mi galaxia`, `sabes donde esta galabunu?` | ❌ No |
| Palabra que empieza con el prefijo pero no es el inicio | `hola galatea` | ❌ No (porque el texto no empieza con "gal") |
| Sin coincidencia | `galatino` (si no empieza el texto) | ❌ No |

## Variantes y prefijos predefinidos (ejemplo para Galatea)

- Nombres completos: `galatea`
- Errores comunes: `galaxia`
- Prefijo secreto (tres primeras letras) **solo válido al inicio del mensaje**: `gal`

## Lógica de implementación (pseudocódigo)
