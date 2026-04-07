import os
import json
import time as timer
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
# TIEMPOS BASE ENTRE ESTACIONES (en segundos)
# ============================================================================
TRAMOS = [
    ("montepo", "fontana", 87),    # 1:27
    ("fontana", "nesima", 87),     # 1:27
    ("nesima", "sannullo", 98),    # 1:38
    ("sannullo", "cibali", 93),    # 1:33
    ("cibali", "milo", 101),       # 1:41
    ("milo", "borgo", 100),        # 1:40
    ("borgo", "giuffrida", 118),   # 1:58 (normal)
    ("giuffrida", "italia", 60),   # 1:00
    ("italia", "galatea", 120),    # 2:00
    ("galatea", "giovanni", 60),   # 1:00
    ("giovanni", "stesicoro", 180) # 3:00
]

# ============================================================================
# CIERRE TEMPORAL DE ESTACIONES
# ============================================================================
CLOSED_STATIONS = [
    {
        "station": "giuffrida",
        "start": date(2026, 1, 1),
        "end": date(2026, 4, 19),
        "reduction_seconds": 40
    }
]

def is_station_closed(station: str, now: datetime) -> bool:
    for closed in CLOSED_STATIONS:
        if closed["station"] == station:
            if closed["start"] <= now.date() <= closed["end"]:
                return True
    return False

def get_closing_message(station: str, now: datetime) -> str:
    if is_station_closed(station, now):
        for closed in CLOSED_STATIONS:
            if closed["station"] == station:
                end_date = closed["end"].strftime('%d/%m/%Y')
                return f"⚠️ La stazione {NOMBRE_MOSTRAR.get(station, station).capitalize()} è chiusa per lavori fino al {end_date}. I treni non fermano.\n"
    return ""

def get_travel_time_from_montepo(station: str, now: datetime) -> int:
    total_seconds = 0
    for (start, end, base_sec) in TRAMOS:
        total_seconds += base_sec
        if end == station:
            break
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for closed in CLOSED_STATIONS:
        if closed["station"] == station:
            continue
        if closed["station"] in stations_order and station in stations_order:
            if stations_order.index(closed["station"]) < stations_order.index(station):
                if is_station_closed(closed["station"], now):
                    total_seconds -= closed["reduction_seconds"]
    minutes = (total_seconds + 59) // 60
    return minutes

def get_travel_time_from_stesicoro(station: str, now: datetime) -> int:
    total_montepo_to_stesicoro = 20 * 60
    montepo_to_station = get_travel_time_from_montepo(station, now) * 60
    stesicoro_to_station = total_montepo_to_stesicoro - montepo_to_station
    minutes = (stesicoro_to_station + 59) // 60
    return max(0, minutes)

def build_tiempos_estacion(now: datetime) -> Dict[str, Tuple[int, int]]:
    result = {}
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for station in stations_order:
        t_mp = get_travel_time_from_montepo(station, now)
        t_st = get_travel_time_from_stesicoro(station, now)
        result[station] = (t_mp, t_st)
    return result

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
# IMÁGENES DE LAS ESTACIONES
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

STATION_IMAGE_BW = {
    "montepo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_montepo_bw.jpg",
    "fontana": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_fontana_bw.jpg",
    "nesima": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_nesima_bw.jpg",
    "sannullo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_sannullo_bw.jpg",
    "cibali": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_cibali_bw.jpg",
    "milo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_milo_bw.jpg",
    "borgo": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_borgo_bw.jpg",
    "giuffrida": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_giuffrida_bw.jpg",
    "italia": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_italia_bw.jpg",
    "galatea": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_galatea_bw.jpg",
    "giovanni": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_giovanni_bw.jpg",
    "stesicoro": "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_stesicoro_bw.jpg",
}

def get_station_image(estacion_key: str, now: datetime) -> str:
    if is_station_closed(estacion_key, now):
        base_url = STATION_IMAGE_BW.get(estacion_key, STATION_IMAGE.get(estacion_key))
    else:
        base_url = STATION_IMAGE.get(estacion_key)
    if not base_url:
        return None
    cache_buster = int(timer.time())
    return f"{base_url}?v={cache_buster}"

# Convertir strings "HH:MM" a objetos time
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

def get_next_departure_sant_agata(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    current_time = now.time()
    first = get_first_train_sant_agata(station)
    last = get_last_train_sant_agata(station)
    first_min = first.hour * 60 + first.minute
    last_min = last.hour * 60 + last.minute
    if last_min < first_min:
        last_min += 24 * 60
    current_min = current_time.hour * 60 + current_time.minute
    
    if current_min < first_min:
        next_dt = datetime.combine(now.date(), first)
        next_dt = CATANIA_TZ.localize(next_dt)
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec // 60, sec % 60, True)
    if current_min >= last_min:
        tomorrow = now.date() + timedelta(days=1)
        next_dt = datetime.combine(tomorrow, first)
        next_dt = CATANIA_TZ.localize(next_dt)
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec // 60, sec % 60, True)
    
    if current_min < 15 * 60:
        minutes_since_first = max(0, current_min - first_min)
        intervals = (minutes_since_first + 9) // 10
        next_min = first_min + intervals * 10
        if next_min > 15 * 60:
            minutes_from_15 = max(0, current_min - 15 * 60)
            intervals13 = (minutes_from_15 + 12) // 13
            next_min = 15 * 60 + intervals13 * 13
    else:
        minutes_from_15 = max(0, current_min - 15 * 60)
        intervals13 = (minutes_from_15 + 12) // 13
        next_min = 15 * 60 + intervals13 * 13
    
    if next_min > last_min:
        tomorrow = now.date() + timedelta(days=1)
        next_dt = datetime.combine(tomorrow, first)
        next_dt = CATANIA_TZ.localize(next_dt)
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec // 60, sec % 60, True)
    
    next_hour = next_min // 60
    next_minute = next_min % 60
    next_dt = datetime.combine(now.date(), time(next_hour, next_minute))
    next_dt = CATANIA_TZ.localize(next_dt)
    sec = int((next_dt - now).total_seconds())
    return (next_dt, sec // 60, sec % 60, True)

# ============================================================================
# DÍAS FESTIVOS NACIONALES Y NOCHEVIEJA
# ============================================================================
FESTIVI_NAZIONALI = [
    (1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 26)
]

def is_new_years_eve(now: datetime) -> bool:
    if now.month == 12 and now.day == 31:
        return True
    if now.month == 1 and now.day == 1 and now.hour < 3:
        return True
    return False

def get_next_departure_new_years_eve(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    current_time = now.time()
    if station == "Montepo":
        first = time(6, 0)
        last = time(3, 0)
    else:
        first = time(6, 25)
        last = time(3, 0)
    first_min = first.hour * 60 + first.minute
    last_min_next_day = last.hour * 60 + last.minute + 24 * 60
    current_min = current_time.hour * 60 + current_time.minute
    
    all_departures = []
    t = first_min
    while t < 15 * 60:
        all_departures.append(t)
        t += 10
    t = 15 * 60
    while t < 24 * 60:
        all_departures.append(t)
        t += 13
    t = 24 * 60
    while t < last_min_next_day:
        all_departures.append(t)
        t += 13
    
    next_min = None
    for dep in all_departures:
        if dep > current_min:
            next_min = dep
            break
    
    if next_min is None:
        return (None, 0, 0, False)
    
    if next_min >= 24 * 60:
        next_date = now.date() + timedelta(days=1)
        next_min_actual = next_min - 24 * 60
    else:
        next_date = now.date()
        next_min_actual = next_min
    next_hour = next_min_actual // 60
    next_minute = next_min_actual % 60
    next_dt = datetime.combine(next_date, time(next_hour, next_minute))
    next_dt = CATANIA_TZ.localize(next_dt)
    sec = int((next_dt - now).total_seconds())
    return (next_dt, sec // 60, sec % 60, True)

# ============================================================================
# CIERRES TOTALES (NAVIDAD, PASCUA)
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
# FUNCIONES DE HORARIOS (comunes)
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
    if is_festivo_nazionale(now):
        return SCHEDULES[station]["sunday"]
    
    current_time = now.time()
    weekday_num = now.weekday()
    if weekday_num == 4:
        normal_list = SCHEDULES[station]["friday"]
    elif weekday_num == 5:
        normal_list = SCHEDULES[station]["saturday"]
    elif weekday_num == 6:
        normal_list = SCHEDULES[station]["sunday"]
    else:
        normal_list = SCHEDULES[station]["weekday"]
    
    first_train = normal_list[0] if normal_list else None
    if first_train and current_time < first_train:
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
# FUNCIONES PARA ESTACIONES INTERMEDIAS
# ============================================================================
def get_next_train_at_station(now: datetime, estacion_key: str) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    tiempos = build_tiempos_estacion(now)
    if estacion_key not in tiempos:
        return (None, None)
    t_mp, t_st = tiempos[estacion_key]
    
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
