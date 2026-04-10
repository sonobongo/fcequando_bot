import pytz
from datetime import datetime

# Zona horaria de Roma (Europa/Rome)
ROME_TZ = pytz.timezone('Europe/Rome')

def now_rome() -> datetime:
    """Devuelve la hora actual en Roma con zona horaria (aware)."""
    return datetime.now(ROME_TZ)

def localize_rome(dt: datetime) -> datetime:
    """Convierte un datetime naive a aware con zona Roma."""
    if dt.tzinfo is None:
        return ROME_TZ.localize(dt)
    return dt

def ensure_rome(dt: datetime) -> datetime:
    """Asegura que un datetime tenga zona horaria Roma (si es naive, lo localiza)."""
    if dt.tzinfo is None:
        return ROME_TZ.localize(dt)
    return dt
