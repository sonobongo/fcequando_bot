import os
import json
import time as timer
from datetime import datetime, time, timedelta, date
from typing import Tuple, Optional, List, Dict, Any
import pytz

# ============================================================================
# CARGAR CONFIGURACIÓN
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
FORWARD_PEAK = [
    ("montepo", "fontana", 87),
    ("fontana", "nesima", 87),
    ("nesima", "sannullo", 98),
    ("sannullo", "cibali", 93),
    ("cibali", "milo", 101),
    ("milo", "borgo", 120),
    ("borgo", "giuffrida", 119),
    ("giuffrida", "italia", 106),
    ("italia", "galatea", 125),
    ("galatea", "giovanni", 179),
    ("giovanni", "stesicoro", 139)
]

REVERSE_PEAK = [
    ("stesicoro", "giovanni", 148),
    ("giovanni", "galatea", 149),
    ("galatea", "italia", 91),
    ("italia", "giuffrida", 113),
    ("giuffrida", "borgo", 97),
    ("borgo", "milo", 120),
    ("milo", "cibali", 126),
    ("cibali", "sannullo", 104),
    ("sannullo", "nesima", 130),
    ("nesima", "fontana", 87),
    ("fontana", "montepo", 87)
]

EXTRA_TRAMOS_FORWARD = [("milo","borgo"), ("borgo","giuffrida"), ("giuffrida","italia"), ("italia","galatea"), ("galatea","giovanni")]
EXTRA_TRAMOS_REVERSE = [
    ("giovanni", "galatea"), ("galatea", "italia"), ("italia", "giuffrida"),
    ("giuffrida", "borgo"), ("borgo", "milo"), ("milo", "cibali"),
    ("cibali", "sannullo"), ("sannullo", "nesima"), ("nesima", "fontana")
]

# ============================================================================
# HORA PUNTA
# ============================================================================
def is_peak_hour(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    if is_festivo_nazionale(now):
        return False
    month = now.month
    if not (month >= 9 or month <= 6):
        return False
    return 7 <= now.hour <= 9

# ============================================================================
# TIEMPOS ACUMULADOS EN SEGUNDOS (EXACTOS, SIN REDONDEAR)
# ============================================================================
def get_total_seconds_from_montepo(station: str, now: datetime) -> int:
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in FORWARD_PEAK:
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_FORWARD:
            sec -= 15
        total += sec
        if end == station:
            break
    # Ajuste por estaciones cerradas
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            if stations_order.index(closed["station"]) < stations_order.index(station):
                total -= closed["reduction_seconds"]
    return max(0, total)

def get_total_seconds_from_stesicoro(station: str, now: datetime) -> int:
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in REVERSE_PEAK:
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_REVERSE:
            sec -= 15
        total += sec
        if end == station:
            break
    stations_order_rev = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            if stations_order_rev.index(closed["station"]) < stations_order_rev.index(station):
                total -= closed["reduction_seconds"]
    return max(0, total)

# ============================================================================
# CIERRE TEMPORAL ESTACIONES
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
        if closed["station"] == station and closed["start"] <= now.date() <= closed["end"]:
            return True
    return False

def get_closing_message(station: str, now: datetime) -> str:
    if is_station_closed(station, now):
        for closed in CLOSED_STATIONS:
            if closed["station"] == station:
                end_date = closed["end"].strftime('%d/%m/%Y')
                return f"⚠️ La stazione {NOMBRE_MOSTRAR.get(station, station).capitalize()} è chiusa per lavori fino al {end_date}. I treni non fermano.\n"
    return ""

def build_tiempos_estacion_segundos(now: datetime) -> Dict[str, Tuple[int, int]]:
    result = {}
    stations = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for st in stations:
        result[st] = (get_total_seconds_from_montepo(st, now), get_total_seconds_from_stesicoro(st, now))
    return result

NOMBRE_MOSTRAR = {
    "montepo": "Monte Po", "fontana": "Fontana", "nesima": "Nesima", "sannullo": "San Nullo",
    "cibali": "Cibali", "milo": "Milo", "borgo": "Borgo", "giuffrida": "Giuffrida",
    "italia": "Italia", "galatea": "Galatea", "giovanni": "Giovanni XXIII", "stesicoro": "Stesicoro"
}

# ============================================================================
# IMÁGENES
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

def get_station_image(estacion_key: str, now: datetime) -> str:
    base = STATION_IMAGE.get(estacion_key)
    if not base:
        return None
    return f"{base}?v={int(timer.time())}"

# ============================================================================
# FUNCIONES DE HORARIOS (sin cambios importantes, solo asegurar que usan segundos donde sea necesario)
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

# Sant'Agata
def is_sant_agata(now: datetime) -> bool:
    return (now.month == SANT_AGATA["month"] and now.day in SANT_AGATA["days"] and SANT_AGATA["active"])

def get_first_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["first"])

def get_last_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["last"])

def get_next_departure_sant_agata(station: str, now: datetime):
    current_time = now.time()
    first = get_first_train_sant_agata(station)
    last = get_last_train_sant_agata(station)
    first_min = first.hour * 60 + first.minute
    last_min = last.hour * 60 + last.minute
    if last_min < first_min:
        last_min += 24*60
    current_min = current_time.hour * 60 + current_time.minute
    if current_min < first_min:
        next_dt = CATANIA_TZ.localize(datetime.combine(now.date(), first))
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec//60, sec%60, True)
    if current_min >= last_min:
        tomorrow = now.date() + timedelta(days=1)
        next_dt = CATANIA_TZ.localize(datetime.combine(tomorrow, first))
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec//60, sec%60, True)
    if current_min < 15*60:
        minutes_since_first = max(0, current_min - first_min)
        intervals = (minutes_since_first + 9)//10
        next_min = first_min + intervals*10
        if next_min > 15*60:
            minutes_from_15 = max(0, current_min - 15*60)
            intervals13 = (minutes_from_15 + 12)//13
            next_min = 15*60 + intervals13*13
    else:
        minutes_from_15 = max(0, current_min - 15*60)
        intervals13 = (minutes_from_15 + 12)//13
        next_min = 15*60 + intervals13*13
    if next_min > last_min:
        tomorrow = now.date() + timedelta(days=1)
        next_dt = CATANIA_TZ.localize(datetime.combine(tomorrow, first))
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec//60, sec%60, True)
    next_hour = next_min // 60
    next_minute = next_min % 60
    next_dt = CATANIA_TZ.localize(datetime.combine(now.date(), time(next_hour, next_minute)))
    sec = int((next_dt - now).total_seconds())
    return (next_dt, sec//60, sec%60, True)

# Festivos
FESTIVI_NAZIONALI = [(1,1),(1,6),(4,25),(5,1),(6,2),(8,15),(11,1),(12,8),(12,26)]

def is_new_years_eve(now: datetime) -> bool:
    return (now.month == 12 and now.day == 31) or (now.month == 1 and now.day == 1 and now.hour < 3)

def get_next_departure_new_years_eve(station: str, now: datetime):
    if station == "Montepo":
        first = time(6,0); last = time(3,0)
    else:
        first = time(6,25); last = time(3,0)
    first_min = first.hour*60+first.minute
    last_min_next = last.hour*60+last.minute+24*60
    cur_min = now.hour*60+now.minute
    deps = []
    t = first_min
    while t < 15*60:
        deps.append(t); t+=10
    t = 15*60
    while t < 24*60:
        deps.append(t); t+=13
    t = 24*60
    while t < last_min_next:
        deps.append(t); t+=13
    nxt = None
    for d in deps:
        if d > cur_min:
            nxt = d
            break
    if nxt is None:
        return (None,0,0,False)
    if nxt >= 24*60:
        next_date = now.date() + timedelta(days=1)
        nxt_actual = nxt - 24*60
    else:
        next_date = now.date()
        nxt_actual = nxt
    next_dt = CATANIA_TZ.localize(datetime.combine(next_date, time(nxt_actual//60, nxt_actual%60)))
    sec = int((next_dt - now).total_seconds())
    return (next_dt, sec//60, sec%60, True)

def is_christmas(now: datetime) -> bool:
    return (now.month == CLOSED_ALL_DAY["christmas"]["month"] and now.day == CLOSED_ALL_DAY["christmas"]["day"] and CLOSED_ALL_DAY["christmas"]["active"])

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
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    return now.date() == date(year, month, day) and now.weekday() == 6

def is_easter_monday(now: datetime) -> bool:
    year = now.year
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    easter_sunday = date(year, month, day)
    return now.date() == easter_sunday + timedelta(days=1)

def is_closed_all_day(now: datetime) -> bool:
    return is_christmas(now) or is_easter_sunday(now)

def get_closing_warning(now: datetime) -> str:
    tomorrow = now + timedelta(days=1)
    if is_closed_all_day(tomorrow) and now.hour >= WARNING_HOUR:
        fest = "Natale" if is_christmas(tomorrow) else "Pasqua"
        return f"⚠️ Attenzione: domani, {fest}, la metropolitana sarà CHIUSA tutto il giorno. ⚠️"
    return ""

def is_festivo_nazionale(now: datetime) -> bool:
    if is_christmas(now) or is_new_years_eve(now) or is_sant_agata(now) or is_easter_sunday(now):
        return False
    if is_easter_monday(now):
        return True
    return (now.month, now.day) in FESTIVI_NAZIONALI

def get_opening_time(now: datetime, station: str = None):
    if is_new_years_eve(now):
        return (6,0) if station=="Montepo" else (6,25)
    if is_sant_agata(now):
        first = get_first_train_sant_agata(station if station else "Montepo")
        return (first.hour, first.minute)
    if is_festivo_nazionale(now) or now.weekday()==6:
        return (7,0)
    return (6,0)

def get_closing_time(now: datetime, station: str):
    if is_new_years_eve(now):
        return (3,0)
    if is_sant_agata(now):
        last = get_last_train_sant_agata(station)
        return (last.hour, last.minute)
    if is_festivo_nazionale(now) or now.weekday()==6:
        return (22,30)
    if now.weekday() in [4,5]:
        return (1,0)
    return (22,30)

def is_metro_closed(now: datetime, station: str):
    if is_closed_all_day(now):
        tomorrow = now + timedelta(days=1)
        oh, om = get_opening_time(tomorrow, station)
        next_open = CATANIA_TZ.localize(datetime.combine(tomorrow.date(), time(oh, om)))
        return (True, next_open, "")
    if is_new_years_eve(now) and (now.hour>=23 or now.hour<3):
        oh, om = get_opening_time(now, station)
        next_open = CATANIA_TZ.localize(datetime.combine(now.date(), time(oh, om)))
        if next_open <= now:
            next_open = CATANIA_TZ.localize(datetime.combine(now.date()+timedelta(days=1), time(oh, om)))
        return (True, next_open, "🚇 Non ci sono informazioni disponibili. Ricorda che oggi l'ultima metropolitana è partita alle 03:00.")
    if now.weekday() in [4,5] and (now.hour>=23 or (now.hour==0 and now.minute<1)):
        oh, om = get_opening_time(now, station)
        next_open = CATANIA_TZ.localize(datetime.combine(now.date(), time(oh, om)))
        if next_open <= now:
            next_open = CATANIA_TZ.localize(datetime.combine(now.date()+timedelta(days=1), time(oh, om)))
        return (True, next_open, "🚇 Non ci sono informazioni disponibili. Ricorda che oggi l'ultima metropolitana è partita alle 01:00.")
    oh, om = get_opening_time(now, station)
    ch, cm = get_closing_time(now, station)
    opening = time(oh, om)
    closing = time(ch, cm)
    if ch < oh or (ch==oh and cm<om):
        if now.time() >= opening or now.time() < closing:
            return (False, None, "")
        next_open = CATANIA_TZ.localize(datetime.combine(now.date(), opening))
        if next_open <= now:
            next_open = CATANIA_TZ.localize(datetime.combine(now.date()+timedelta(days=1), opening))
        return (True, next_open, "")
    else:
        if now.time() >= closing or now.time() < opening:
            if now.time() < opening:
                next_open = CATANIA_TZ.localize(datetime.combine(now.date(), opening))
            else:
                next_open = CATANIA_TZ.localize(datetime.combine(now.date()+timedelta(days=1), opening))
            return (True, next_open, "")
        return (False, None, "")

def get_schedule_list(station: str, now: datetime):
    if is_festivo_nazionale(now):
        return SCHEDULES[station]["sunday"]
    wd = now.weekday()
    if wd == 4:
        lst = SCHEDULES[station]["friday"]
    elif wd == 5:
        lst = SCHEDULES[station]["saturday"]
    elif wd == 6:
        lst = SCHEDULES[station]["sunday"]
    else:
        lst = SCHEDULES[station]["weekday"]
    first = lst[0] if lst else None
    if first and now.time() < first:
        yesterday = now - timedelta(days=1)
        ywd = yesterday.weekday()
        if ywd == 4:
            ylst = SCHEDULES[station]["friday"]
        elif ywd == 5:
            ylst = SCHEDULES[station]["saturday"]
        elif ywd == 6:
            ylst = SCHEDULES[station]["sunday"]
        else:
            ylst = SCHEDULES[station]["weekday"]
        if any(t.hour < 6 for t in ylst):
            return ylst
    return lst

def get_next_departure(station: str, now: datetime):
    if is_new_years_eve(now):
        return get_next_departure_new_years_eve(station, now)
    if is_sant_agata(now):
        return get_next_departure_sant_agata(station, now)
    sched = get_schedule_list(station, now)
    cur = now.time()
    for dep in sched:
        if dep > cur:
            dt = CATANIA_TZ.localize(datetime.combine(now.date(), dep))
            delta = int((dt - now).total_seconds())
            return (dt, delta//60, delta%60, True)
    return (None,0,0,False)

def get_next_departure_after(station: str, now: datetime, after_time: time):
    if is_sant_agata(now) or is_new_years_eve(now):
        fake = CATANIA_TZ.localize(datetime.combine(now.date(), after_time) + timedelta(minutes=1))
        return get_next_departure(station, fake)
    sched = get_schedule_list(station, now)
    for dep in sched:
        if dep > after_time:
            dt = CATANIA_TZ.localize(datetime.combine(now.date(), dep))
            delta = int((dt - now).total_seconds())
            return (dt, delta//60, delta%60, True)
    return (None,0,0,False)

def format_time(minutes: int, seconds: int) -> str:
    if minutes >= SHORT_TIME_THRESHOLD:
        return f"{minutes} minuti"
    if minutes == 0:
        if seconds == 0:
            return "subito"
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
    if now.weekday() in [0,1,2,3]:
        last = "22:30"
    elif now.weekday() in [4,5]:
        last = "01:00"
    else:
        last = "22:30"
    return f"📌 Ricorda che oggi l'ultima metropolitana da Stesicoro parte alle {last}."

# ============================================================================
# NUEVA VERSIÓN: PRÓXIMOS TRENES EN ESTACIONES INTERMEDIAS USANDO SEGUNDOS EXACTOS
# ============================================================================
def get_next_train_at_station(now: datetime, estacion_key: str):
    tiempos_seg = build_tiempos_estacion_segundos(now)  # (seg_mp, seg_st)
    if estacion_key not in tiempos_seg:
        return (None, None)
    seg_mp, seg_st = tiempos_seg[estacion_key]

    info_mp = None
    closed_mp, _, _ = is_metro_closed(now, "Montepo")
    if not closed_mp:
        schedule_list = get_schedule_list("Montepo", now)
        pasos = []
        for salida in schedule_list:
            paso_dt = datetime.combine(now.date(), salida) + timedelta(seconds=seg_mp)
            paso_dt = CATANIA_TZ.localize(paso_dt)
            pasos.append(paso_dt)
        next_paso = None
        next_idx = -1
        for i, p in enumerate(pasos):
            if p > now:
                next_paso = p
                next_idx = i
                break
        if next_paso:
            delta = next_paso - now
            mins_rest = int(delta.total_seconds() // 60)
            secs_rest = int(delta.total_seconds() % 60)
            next_info = None
            if next_idx + 1 < len(pasos):
                p2 = pasos[next_idx+1]
                delta2 = p2 - now
                mins2 = int(delta2.total_seconds() // 60)
                secs2 = int(delta2.total_seconds() % 60)
                next_info = (p2, mins2, secs2)
            info_mp = (next_paso, mins_rest, secs_rest, next_info)

    info_st = None
    closed_st, _, _ = is_metro_closed(now, "Stesicoro")
    if not closed_st:
        schedule_list = get_schedule_list("Stesicoro", now)
        pasos = []
        for salida in schedule_list:
            paso_dt = datetime.combine(now.date(), salida) + timedelta(seconds=seg_st)
            paso_dt = CATANIA_TZ.localize(paso_dt)
            pasos.append(paso_dt)
        next_paso = None
        next_idx = -1
        for i, p in enumerate(pasos):
            if p > now:
                next_paso = p
                next_idx = i
                break
        if next_paso:
            delta = next_paso - now
            mins_rest = int(delta.total_seconds() // 60)
            secs_rest = int(delta.total_seconds() % 60)
            next_info = None
            if next_idx + 1 < len(pasos):
                p2 = pasos[next_idx+1]
                delta2 = p2 - now
                mins2 = int(delta2.total_seconds() // 60)
                secs2 = int(delta2.total_seconds() % 60)
                next_info = (p2, mins2, secs2)
            info_st = (next_paso, mins_rest, secs_rest, next_info)

    return (info_mp, info_st)
