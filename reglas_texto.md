# Reglas de reconocimiento textual de estaciones (modo normal)

## Configuración
Las reglas se definen en `variantes_estaciones.json`. Cada estación tiene:
- `nombre`: nombre completo (para mostrar).
- `variantes`: lista de palabras que también activan la estación (incluyendo errores comunes).
- `prefijo`: tres primeras letras secretas (solo se activa si el texto **empieza** con ese prefijo).

## Comportamiento
1. Se busca cualquier variante (nombre completo o sinónimo) en **cualquier parte** del mensaje.
2. Si no se encuentra, se comprueba si el mensaje **empieza** con el prefijo de 3 letras.
3. Se reconoce la primera estación que cumpla cualquiera de las condiciones.

## Ejemplos (para Galatea)
- `galatea`, `GALATEA`, `Galatea` → Sí (nombre exacto)
- `galaxia` → Sí (variante)
- `gal` → Sí (prefijo al inicio)
- `galabunu` → Sí (empieza con "gal")
- `mi galaxia` → No (no empieza con "gal" y la variante no está al inicio)
- `hola galatea` → Sí (contiene "galatea" en cualquier parte)

## Nota
Los prefijos de 3 letras son secretos (no se muestran en los mensajes de error ni en la ayuda).
