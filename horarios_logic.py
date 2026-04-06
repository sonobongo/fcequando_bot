import os
import json
from datetime import datetime, time, timedelta, date
from typing import Tuple, Optional, List, Dict, Any
import pytz

# ============================================================================
# CARGAR CONFIGURACIÓN DESDE horarios.json
# ============================================================================
def load_config() -> Dict[str, Any]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'horarios.json')
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No se encontró {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
SCHEDULE_DATA = CONFIG["schedule"]
SANT_AGATA = CONFIG["sant_agata"]
CLOSED_ALL_DAY = CONFIG["closed_all_day"]
LAST_TRAIN_START_HOUR = CONFIG["last_train_message_start_hour"]
WARNING_HOUR = CONFIG["closing_warning_hour"]
SHORT_TIME_THRESHOLD = CONFIG["short_time_threshold"]
NEXT_TRAIN_THRESHOLD = CONFIG["next_train_threshold"]

# ============================================================================
# TIEMPOS DE TRAYECTO PARA CADA ESTACIÓN (desde Monte Po y desde Stesicoro)
# ============================================================================
TIEMPOS_ESTACION = {
    "montepo":    (0, 20),
    "fontana":    (1, 19),
    "nesima":     (3, 17),
    "sannullo":   (5, 15),
    "cibali":     (7, 13),
    "milo":       (9, 11),
    "borgo":      (11, 9),
    "giuffrida":  (13, 7),
    "italia":     (14, 6),
    "galatea":    (16, 4),
    "giovanni":   (17, 3),
    "stesicoro":  (20, 0)
}

# Nombres para mostrar
NOMBRE_MOSTRAR = {
    "montepo": "Monte Po",
    "fontana": "Fontana",
    "nesima": "Nesima",
    "sannullo": "San Nullo",
    "cibali": "Cibali",
    "milo": "Milo",
    "borgo": "Borgo",
    "giuffrida": "Giuffrida",
    "italia": "Italia",
    "galatea": "Galatea",
    "giovanni": "Giovanni XXIII",
    "stesicoro": "Stesicoro"
}

# ============================================================================
# IMÁGENES DE LAS ESTACIONES (cambia la URL si tu repositorio es diferente)
# ============================================================================
STATION_IMAGE = {
    "montepo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_montepo.jpg",
    "fontana": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_fontana.jpg",
    "nesima": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_nesima.jpg",
    "sannullo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_sannullo.jpg",
    "cibali": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_cibali.jpg",
    "milo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_milo.jpg",
    "borgo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_borgo.jpg",
    "giuffrida": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_giuffrida.jpg",
    "italia": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_italia.jpg",
    "galatea": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_galatea.jpg",
    "giovanni": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_giovanni.jpg",
    "stesicoro": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_stesicoro.jpg",
}

# ============================================================================
# CONVERSIÓN DE HORARIOS
# ============================================================================
def str_to_time(t_str: str) -> time:
    h, m = map(int, t_str.split(':'))
    return time(h, m)

def convert_schedule(sched_dict: Dict[str, List[str]]) -> Dict[str, Dict[str, List[time]]]:
    result = {}
    for station, days in sched_dict.items():
        result[station] = {}
        for day, str_list in days.items():
            result[station][day] = [str_to_time(t) for t in str_list]
    return result

SCHEDULES = convert_schedule(SCHEDULE_DATA)
CATANIA_TZ = pytz.timezone('Europe/Rome')

# ============================================================================
# FUNCIONES PARA SANT'AGATA
# ============================================================================
def is_sant_agata(now: datetime) -> bool:
    return (now.month == SANT_AGATA["month"] and 
            now.day in SANT_AGATA["days"] and 
            SANT_AGATA["active"])

def get_first_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["first"])

def get_last_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["last"])

def get_next_departure(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    # Excepciones especiales (Nochevieja, Sant'Agata)
    if is_new_years_eve(now):
        return get_next_departure_new_years_eve(station, now)
    if is_sant_agata(now):
        return get_next_departure_sant_agata(station, now)
    
    current_time = now.time()
    current_min = current_time.hour * 60 + current_time.minute
    
    # Obtener el horario del día actual
    schedule_list_today = get_schedule_list(station, now)
    
    # Buscar el primer tren del día actual que sea > ahora
    next_dep_time = None
    for dep_time in schedule_list_today:
        if dep_time > current_time:
            next_dep_time = dep_time
            break
    
    # Si encontramos un tren hoy, devolverlo
    if next_dep_time:
        next_dt = datetime.combine(now.date(), next_dep_time)
        next_dt = CATANIA_TZ.localize(next_dt)
        delta = int((next_dt - now).total_seconds())
        return (next_dt, delta // 60, delta % 60, True)
    
    # Si no hay trenes hoy (porque la hora actual es después del último o antes del primero),
    # comprobar si estamos en la madrugada (antes del primer tren del día) y el día anterior tenía trenes después de medianoche.
    # Para ello, obtenemos el primer tren del día actual.
    first_train_today = schedule_list_today[0] if schedule_list_today else None
    if first_train_today and current_time < first_train_today:
        # Estamos antes del primer tren de hoy (madrugada). Usar el horario del día anterior.
        yesterday = now - timedelta(days=1)
        schedule_list_yesterday = get_schedule_list(station, yesterday)
        # Buscar el último tren de ayer (el que pasa después de medianoche)
        # Necesitamos el primer tren de ayer que sea mayor que la hora actual (pero teniendo en cuenta que ayer sus horas son anteriores a hoy)
        # Lo más simple: recalcular la hora actual como si fuera ayer (sumando 24h)
        current_min_yesterday = current_min + 24 * 60
        for dep_time in schedule_list_yesterday:
            dep_min = dep_time.hour * 60 + dep_time.minute
            # Si el tren de ayer es después de medianoche (dep_min < 6*60? No, algunos pueden ser > 24*60? No, las horas son 00-23)
            # Para comparar, convertimos dep_min a minutos desde el inicio del día de ayer, pero si es después de medianoche, dep_min es pequeño (ej. 00:38)
            # Queremos que se consideren solo los que son después de medianoche (dep_min < 6*60) y que sean mayores que current_min
            if dep_min > current_min:
                # Es un tren de ayer que sale después de la hora actual (ej. 00:38 > 00:47? No, sería menor)
                pass
            # En realidad, necesitamos encontrar el primer tren de ayer cuya hora (en el mismo día ayer) sea mayor que current_min, pero como current_min es pequeño (0-60), los trenes de ayer con dep_min pequeños (ej. 00:38) son menores que 00:47, por lo que no los tomaría. Debemos tratar la hora actual como si fuera del día ayer sumando 24h.
        # Mejor: convertir la hora actual a minutos del día de ayer (sumando 24h) y luego buscar en la lista de ayer (sin modificar).
        current_min_adjusted = current_min + 24 * 60
        for dep_time in schedule_list_yesterday:
            dep_min = dep_time.hour * 60 + dep_time.minute
            if dep_min > current_min_adjusted - 24*60:
                # Este tren es después de medianoche (dep_min pequeño) y después de la hora actual?
                # Si dep_min es, por ejemplo, 38 (00:38) y current_min es 47, entonces dep_min (38) no es mayor que 47. Por tanto, no lo considera.
                # Necesitamos buscar el primer tren de ayer que sea mayor que la hora actual en la misma escala (con dep_min + 24*60)
                pass
        # Es más sencillo: si estamos en madrugada, simplemente tomar el primer tren de ayer que sea después de medianoche (cualquiera) y que sea el primero de ese día después de medianoche.
        # Pero para no complicar, la solución más robusta es generar todos los horarios de ayer y filtrar los que están después de medianoche (dep_min < 6*60) y luego elegir el primero mayor que current_min.
    else:
        # No hay trenes hoy (ya pasó el último) -> mañana
        tomorrow = now + timedelta(days=1)
        first_train_tomorrow = get_schedule_list(station, tomorrow)[0]
        next_dt = datetime.combine(tomorrow.date(), first_train_tomorrow)
        next_dt = CATANIA_TZ.localize(next_dt)
        delta = int((next_dt - now).total_seconds())
        return (next_dt, delta // 60, delta % 60, True)
# ============================================================================
# DÍAS FESTIVOS NACIONALES (horario de domingo) y Nochevieja
# ============================================================================
FESTIVI_NAZIONALI = [
    (1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 26)
]

def is_new_years_eve(now: datetime) -> bool:
    # 31 de diciembre o 1 de enero antes de las 3:00
    if now.month == 12 and now.day == 31:
        return True
    if now.month == 1 and now.day == 1 and now.hour < 3:
        return True
    return False

def get_next_departure(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    # Excepciones especiales
    if is_new_years_eve(now):
        return get_next_departure_new_years_eve(station, now)
    if is_sant_agata(now):
        return get_next_departure_sant_agata(station, now)
    
    current_time = now.time()
    # Primero, intentamos con el día actual
    schedule_today = get_schedule_list(station, now)
    next_dep_time = None
    for dep_time in schedule_today:
        if dep_time > current_time:
            next_dep_time = dep_time
            break
    
    if next_dep_time:
        next_dt = datetime.combine(now.date(), next_dep_time)
        next_dt = CATANIA_TZ.localize(next_dt)
        delta = int((next_dt - now).total_seconds())
        return (next_dt, delta // 60, delta % 60, True)
    
    # No hay trenes hoy. ¿Estamos en la madrugada (antes del primer tren del día)?
    first_train_today = schedule_today[0] if schedule_today else None
    if first_train_today and current_time < first_train_today:
        # Madrugada: usar el horario del día anterior (que pudo tener trenes después de medianoche)
        yesterday = now - timedelta(days=1)
        schedule_yesterday = get_schedule_list(station, yesterday)
        # Buscar el primer tren de ayer que sea después de la hora actual (teniendo en cuenta que los trenes de ayer después de medianoche tienen hora pequeña)
        # Convertimos la hora actual a minutos desde la medianoche de ayer (sumando 24h)
        current_min = current_time.hour * 60 + current_time.minute
        current_min_yesterday = current_min + 24 * 60
        for dep_time in schedule_yesterday:
            dep_min = dep_time.hour * 60 + dep_time.minute
            # Si el tren de ayer es después de medianoche (dep_min < 6*60) o es un tren normal, lo comparamos con current_min_yesterday
            # Para que sea válido, debe ser mayor que la hora actual en la escala de ayer.
            # Si dep_min es, por ejemplo, 38 (00:38) y current_min es 47, entonces dep_min (38) no es mayor que 47. Pero al sumar 24h a current_min, tenemos 24*60+47 = 1487. dep_min 38 no es mayor. Entonces no lo tomaría. Eso es correcto porque 00:38 ya pasó.
            # Necesitamos buscar el primer tren de ayer que sea mayor que la hora actual, pero considerando que esos trenes están en el mismo día ayer.
            # En realidad, la comparación debe ser: dep_min > current_min (sin sumar 24h) porque tanto current_min como dep_min están en el rango 0-1440.
            # Pero si current_min = 47, dep_min = 38, entonces 38 no es mayor. Así que no se toma. Eso está bien porque el tren de las 00:38 ya pasó.
            # El siguiente podría ser 01:00 (60) que sí es mayor que 47. Ese es el que debe devolver.
            if dep_min > current_min:
                # Encontramos un tren de ayer que sale después de la hora actual (dentro del mismo día ayer)
                # Pero cuidado: ese tren ya debería haber salido ayer? No, porque ayer a las 00:47 todavía no había llegado la 01:00.
                # La fecha de ese tren es ayer, pero la hora es posterior a la actual. Sin embargo, la hora actual es del día de hoy, pero en la madrugada.
                # En realidad, el tren de las 01:00 de ayer (viernes noche) corresponde a las 01:00 del sábado (hoy). Por tanto, debemos tratarlo como un tren de hoy.
                # Para evitar confusiones, la forma correcta es: si estamos en madrugada (current_time < first_train_today), entonces el próximo tren es el primer tren del día anterior que sea después de medianoche (es decir, dep_min < 6*60? No, puede ser 01:00 que es 60).
                # Lo más seguro es: generar todos los horarios del día anterior y luego ajustar la fecha sumando un día si el horario es después de medianoche? Mejor: si dep_min < 6*60 (es decir, antes de las 6), entonces ese tren pertenece al día siguiente (hoy). Pero 01:00 es < 6, así que ese tren debería considerarse como de hoy a las 01:00.
                # Por tanto, podemos calcular: if dep_min < first_train_today_min: entonces la fecha real es hoy.
                # En lugar de complicar, usa el mismo enfoque que para Sant'Agata: generas todos los horarios del día anterior y los ajustas.
                # Te propongo una solución más directa: 
                pass
# ============================================================================
# FUNCIONES PARA CIERRE TOTAL (Navidad, Pascua desde 2027)
# ============================================================================
def is_christmas(now: datetime) -> bool:
    return (now.month == CLOSED_ALL_DAY["christmas"]["month"] and 
            now.day == CLOSED_ALL_DAY["christmas"]["day"] and
            CLOSED_ALL_DAY["christmas"]["active"])

def is_easter_sunday(now: datetime) -> bool:
    if not CLOSED_ALL_DAY["easter_sunday"]["active"]:
        return False
    year = now.year
    if year < CLOSED_ALL_DAY["easter_sunday"]["start_year"]:
        return False
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    return now.date() == easter and now.weekday() == 6

def is_easter_monday(now: datetime) -> bool:
    """Retorna True se la data è il Lunedì dell'Angelo (lunes de Pascua)."""
    year = now.year
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter_sunday = date(year, month, day)
    easter_monday = easter_sunday + timedelta(days=1)
    return now.date() == easter_monday

def is_closed_all_day(now: datetime) -> bool:
    return is_christmas(now) or is_easter_sunday(now)

def get_closing_warning(now: datetime) -> str:
    tomorrow = now + timedelta(days=1)
    if is_closed_all_day(tomorrow):
        if now.hour >= WARNING_HOUR:
            if is_christmas(tomorrow):
                fest_name = "Natale (25 dicembre)"
            else:
                fest_name = CLOSED_ALL_DAY["easter_sunday"].get("message", "Pasqua")
            return f"⚠️ Attenzione: domani, {fest_name}, la metropolitana sarà CHIUSA tutto il giorno. ⚠️"
    return ""

def is_festivo_nazionale(now: datetime) -> bool:
    if is_christmas(now) or is_new_years_eve(now) or is_sant_agata(now):
        return False
    if is_easter_sunday(now):
        return False
    if is_easter_monday(now):
        return True
    return (now.month, now.day) in FESTIVI_NAZIONALI

# ============================================================================
# FUNCIONES DE HORARIOS (comunes para Monte Po y Stesicoro)
# ============================================================================
def get_opening_time(now: datetime, station: str = None) -> Tuple[int, int]:
    if is_new_years_eve(now):
        return (6, 0) if station == "Montepo" else (6, 25)
    if is_sant_agata(now):
        first = get_first_train_sant_agata(station if station else "Montepo")
        return (first.hour, first.minute)
    if is_festivo_nazionale(now) or now.weekday() == 6:
        return (7, 0)
    else:
        return (6, 0)

def get_closing_time(now: datetime, station: str) -> Tuple[int, int]:
    if is_new_years_eve(now):
        return (3, 0)
    if is_sant_agata(now):
        last = get_last_train_sant_agata(station)
        return (last.hour, last.minute)
    if is_festivo_nazionale(now) or now.weekday() == 6:
        return (22, 30)
    else:
        weekday = now.weekday()
        if weekday in [4, 5]:
            return (1, 0)
        else:
            return (22, 30)

def is_metro_closed(now: datetime, station: str) -> Tuple[bool, Optional[datetime]]:
    if is_closed_all_day(now):
        tomorrow = now + timedelta(days=1)
        open_h, open_m = get_opening_time(tomorrow, station)
        next_open = datetime.combine(tomorrow.date(), time(open_h, open_m))
        next_open = CATANIA_TZ.localize(next_open)
        return (True, next_open)
    
    current_time = now.time()
    open_h, open_m = get_opening_time(now, station)
    close_h, close_m = get_closing_time(now, station)
    opening_time = time(open_h, open_m)
    closing_time = time(close_h, close_m)
    
    if close_h < open_h or (close_h == open_h and close_m < open_m):
        if current_time >= opening_time or current_time < closing_time:
            return (False, None)
        else:
            next_open = datetime.combine(now.date(), opening_time)
            if next_open <= now:
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open)
    else:
        if current_time >= closing_time or current_time < opening_time:
            if current_time < opening_time:
                next_open = datetime.combine(now.date(), opening_time)
            else:
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open)
        return (False, None)

def get_schedule_list(station: str, now: datetime) -> List[time]:
    # Si es festivo nacional, usar domingo
    if is_festivo_nazionale(now):
        return SCHEDULES[station]["sunday"]
    
    current_time = now.time()
    # Obtener la lista normal del día actual
    weekday_num = now.weekday()
    if weekday_num == 4:
        normal_list = SCHEDULES[station]["friday"]
    elif weekday_num == 5:
        normal_list = SCHEDULES[station]["saturday"]
    elif weekday_num == 6:
        normal_list = SCHEDULES[station]["sunday"]
    else:
        normal_list = SCHEDULES[station]["weekday"]
    
    # Si la hora actual es antes del primer tren del día (madrugada)
    first_train = normal_list[0] if normal_list else None
    if first_train and current_time < first_train:
        # Mirar el día anterior (puede tener trenes nocturnos)
        yesterday = now - timedelta(days=1)
        y_weekday = yesterday.weekday()
        if y_weekday == 4:
            yesterday_list = SCHEDULES[station]["friday"]
        elif y_weekday == 5:
            yesterday_list = SCHEDULES[station]["saturday"]
        elif y_weekday == 6:
            yesterday_list = SCHEDULES[station]["sunday"]
        else:
            yesterday_list = SCHEDULES[station]["weekday"]
        # Si el día anterior tiene algún tren después de medianoche (hora < 6:00), usar esa lista
        if any(t.hour < 6 for t in yesterday_list):
            return yesterday_list
    return normal_list

def get_next_departure(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    if is_new_years_eve(now):
        return get_next_departure_new_years_eve(station, now)
    if is_sant_agata(now):
        return get_next_departure_sant_agata(station, now)
    
    current_time = now.time()
    schedule_list = get_schedule_list(station, now)
    for dep_time in schedule_list:
        if dep_time > current_time:
            next_dt = datetime.combine(now.date(), dep_time)
            next_dt = CATANIA_TZ.localize(next_dt)
            delta = int((next_dt - now).total_seconds())
            return (next_dt, delta // 60, delta % 60, True)
    return (None, 0, 0, False)

def get_next_departure_after(station: str, now: datetime, after_time: time) -> Tuple[Optional[datetime], int, int, bool]:
    if is_sant_agata(now):
        fake_now = datetime.combine(now.date(), after_time) + timedelta(minutes=1)
        fake_now = CATANIA_TZ.localize(fake_now)
        return get_next_departure(station, fake_now)
    if is_new_years_eve(now):
        fake_now = datetime.combine(now.date(), after_time) + timedelta(minutes=1)
        fake_now = CATANIA_TZ.localize(fake_now)
        return get_next_departure(station, fake_now)
    
    schedule_list = get_schedule_list(station, now)
    for dep_time in schedule_list:
        if dep_time > after_time:
            next_dt = datetime.combine(now.date(), dep_time)
            next_dt = CATANIA_TZ.localize(next_dt)
            delta = int((next_dt - now).total_seconds())
            return (next_dt, delta // 60, delta % 60, True)
    return (None, 0, 0, False)

def format_time(minutes: int, seconds: int) -> str:
    if minutes >= SHORT_TIME_THRESHOLD:
        return f"{minutes} minuti"
    if minutes == 0:
        if seconds < 30:
            return "meno di un minuto"
        else:
            return "30 secondi"
    elif minutes == 1:
        if seconds < 30:
            return "1 minuto"
        else:
            return "1 minuto e 30 secondi"
    else:
        if seconds < 30:
            return f"{minutes} minuti"
        else:
            return f"{minutes} minuti e 30 secondi"

def get_last_train_message(now: datetime) -> str:
    if now.hour < LAST_TRAIN_START_HOUR or is_sant_agata(now) or is_closed_all_day(now):
        return ""
    weekday = now.weekday()
    if weekday in [0, 1, 2, 3]:
        last_time = "22:30"
    elif weekday in [4, 5]:
        last_time = "01:00"
    else:
        last_time = "22:30"
    return f"📌 Ricorda che oggi l'ultima metropolitana da Stesicoro parte alle {last_time}."

# ============================================================================
# FUNCIONES PARA CUALQUIER ESTACIÓN (incluye trenes ya salidos)
# ============================================================================
def get_next_train_at_station(now: datetime, estacion_key: str) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    if estacion_key not in TIEMPOS_ESTACION:
        return (None, None)
    t_mp, t_st = TIEMPOS_ESTACION[estacion_key]
    
    # Dirección Monte Po -> Stesicoro
    info_mp = None
    closed_mp, _ = is_metro_closed(now, "Montepo")
    if not closed_mp:
        schedule_list = get_schedule_list("Montepo", now)
        pasos = []
        for salida in schedule_list:
            paso_dt = datetime.combine(now.date(), salida) + timedelta(minutes=t_mp)
            paso_dt = CATANIA_TZ.localize(paso_dt)
            pasos.append(paso_dt)
        next_paso = None
        next_index = -1
        for i, paso in enumerate(pasos):
            if paso > now:
                next_paso = paso
                next_index = i
                break
        if next_paso:
            delta = next_paso - now
            mins_rest = int(delta.total_seconds() // 60)
            secs_rest = int(delta.total_seconds() % 60)
            next_info = None
            if next_index + 1 < len(pasos):
                next_paso2 = pasos[next_index + 1]
                delta2 = next_paso2 - now
                mins2 = int(delta2.total_seconds() // 60)
                secs2 = int(delta2.total_seconds() % 60)
                next_info = (next_paso2, mins2, secs2)
            info_mp = (next_paso, mins_rest, secs_rest, next_info)
    
    # Dirección Stesicoro -> Monte Po
    info_st = None
    closed_st, _ = is_metro_closed(now, "Stesicoro")
    if not closed_st:
        schedule_list = get_schedule_list("Stesicoro", now)
        pasos = []
        for salida in schedule_list:
            paso_dt = datetime.combine(now.date(), salida) + timedelta(minutes=t_st)
            paso_dt = CATANIA_TZ.localize(paso_dt)
            pasos.append(paso_dt)
        next_paso = None
        next_index = -1
        for i, paso in enumerate(pasos):
            if paso > now:
                next_paso = paso
                next_index = i
                break
        if next_paso:
            delta = next_paso - now
            mins_rest = int(delta.total_seconds() // 60)
            secs_rest = int(delta.total_seconds() % 60)
            next_info = None
            if next_index + 1 < len(pasos):
                next_paso2 = pasos[next_index + 1]
                delta2 = next_paso2 - now
                mins2 = int(delta2.total_seconds() // 60)
                secs2 = int(delta2.total_seconds() % 60)
                next_info = (next_paso2, mins2, secs2)
            info_st = (next_paso, mins_rest, secs_rest, next_info)
    
    return (info_mp, info_st)
