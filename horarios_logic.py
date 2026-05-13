import os
import json
import time as timer
from datetime import datetime, time, timedelta, date
from typing import Tuple, Optional, List, Dict, Any
import pytz
from collections import defaultdict
from statistics import mean

CATANIA_TZ = pytz.timezone('Europe/Rome')

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
# CARGAR MEDICIONES REALES (mediciones.json)
# ============================================================================
MEDICIONES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mediciones.json')
mediciones_por_tramo = defaultdict(list)

def cargar_mediciones():
    if not os.path.exists(MEDICIONES_FILE):
        return
    with open(MEDICIONES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for medicion in data.get('mediciones', []):
            dia = medicion.get('dia_semana', '').lower()
            hora_str = medicion.get('hora', '12:00')
            hora_redondeada = int(hora_str.split(':')[0])
            for t in medicion.get('trayectos_ida', []):
                origen = t['origen'].lower()
                destino = t['destino'].lower()
                key = (origen, destino, 'ida', dia, hora_redondeada)
                mediciones_por_tramo[key].append(t['tiempo_seg'])
            for t in medicion.get('trayectos_vuelta', []):
                origen = t['origen'].lower()
                destino = t['destino'].lower()
                key = (origen, destino, 'vuelta', dia, hora_redondeada)
                mediciones_por_tramo[key].append(t['tiempo_seg'])

cargar_mediciones()

def get_measured_travel_time(origen: str, destino: str, direccion: str, now: datetime) -> Optional[float]:
    weekdays_it = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    dia_actual = weekdays_it[now.weekday()].lower()
    hora_actual = now.hour
    tiempos = []
    for (o, d, dir_m, dia, hora), valores in mediciones_por_tramo.items():
        if o == origen.lower() and d == destino.lower() and dir_m == direccion and dia == dia_actual:
            if abs(hora - hora_actual) <= 1:
                tiempos.extend(valores)
    if tiempos:
        return mean(tiempos)
    return None

# ============================================================================
# CARGAR EVENTOS PUNTUALES (eventos.json)
# ============================================================================
EVENTOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eventos.json')
EVENTOS = {"cierres_estaciones": [], "extensiones_horario": [], "notas": []}

def load_eventos():
    if not os.path.exists(EVENTOS_FILE):
        return
    with open(EVENTOS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for cierre in data.get('cierres_estaciones', []):
            EVENTOS['cierres_estaciones'].append({
                'station': cierre['station'],
                'start': datetime.strptime(cierre['start'], '%Y-%m-%d').date(),
                'end': datetime.strptime(cierre['end'], '%Y-%m-%d').date(),
                'reduction_seconds': cierre['reduction_seconds']
            })
        for ext in data.get('extensiones_horario', []):
            EVENTOS['extensiones_horario'].append({
                'fecha': datetime.strptime(ext['fecha'], '%Y-%m-%d').date(),
                'horario_extendido': ext['horario_extendido'],
                'descripcion': ext.get('descripcion', ''),
                'mantiene_frecuencia': ext.get('mantiene_frecuencia', False),
                'tipo_dia_base': ext.get('tipo_dia_base', None)
            })
        for nota in data.get('notas', []):
            EVENTOS['notas'].append(nota)

load_eventos()

# ============================================================================
# AJUSTE DE DÍA OPERATIVO (empieza a las 05:00)
# ============================================================================
def get_effective_datetime(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    if now.hour < 5:
        return now - timedelta(days=1)
    return now

# ============================================================================
# TIEMPOS BASE ENTRE ESTACIONES (en segundos)
# ============================================================================
FORWARD_PEAK = [
    ("montepo", "fontana", 109), ("fontana", "nesima", 111), ("nesima", "sannullo", 143),
    ("sannullo", "cibali", 115), ("cibali", "milo", 118), ("milo", "borgo", 120),
    ("borgo", "giuffrida", 112), ("giuffrida", "italia", 85), ("italia", "galatea", 91),
    ("galatea", "giovanni", 157), ("giovanni", "stesicoro", 139)
]

REVERSE_PEAK = [
    ("stesicoro", "giovanni", 136), ("giovanni", "galatea", 161), ("galatea", "italia", 112),
    ("italia", "giuffrida", 106), ("giuffrida", "borgo", 119), ("borgo", "milo", 116),
    ("milo", "cibali", 123), ("cibali", "sannullo", 104), ("sannullo", "nesima", 140),
    ("nesima", "fontana", 100), ("fontana", "montepo", 99)
]

EXTRA_TRAMOS_FORWARD = [
    ("milo","borgo"), ("borgo","giuffrida"), ("giuffrida","italia"),
    ("italia","galatea"), ("galatea","giovanni")
]

EXTRA_TRAMOS_REVERSE = [
    ("giovanni", "galatea"), ("galatea", "italia"), ("italia", "giuffrida"),
    ("giuffrida", "borgo"), ("borgo", "milo"), ("milo", "cibali"),
    ("cibali", "sannullo"), ("sannullo", "nesima"), ("nesima", "fontana")
]

# ============================================================================
# DETECCIÓN DE HORA PUNTA (solo lunes a viernes, sin domingos)
# ============================================================================
def is_peak_hour(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    if is_festivo_nazionale(now):
        return False
    month = now.month
    if not (month >= 9 or month <= 6):
        return False
    hour = now.hour
    minute = now.minute
    if 7 <= hour <= 9:
        return True
    if (hour == 12 and minute >= 30) or (hour == 13) or (hour == 14 and minute <= 30):
        return True
    if (hour == 17 and minute >= 15) or (hour == 18) or (hour == 19 and minute <= 45):
        return True
    return False

# ============================================================================
# EXTRA DE 5 SEGUNDOS PARA GIOVANNI XXIII (incluye domingos tarde si lunes laborable)
# ============================================================================
def should_add_giovanni_extra(now: datetime) -> bool:
    if now.weekday() < 5 and not is_festivo_nazionale(now):
        month = now.month
        if (month >= 9 or month <= 6) and 13 <= now.hour < 18:
            return True
    if now.weekday() == 6:
        month = now.month
        if (month >= 9 or month <= 6) and ((now.hour == 17 and now.minute >= 30) or (now.hour == 18) or (now.hour == 19 and now.minute <= 45)):
            tomorrow = now + timedelta(days=1)
            if tomorrow.weekday() < 5 and not is_festivo_nazionale(tomorrow) and (tomorrow.month >= 9 or tomorrow.month <= 6):
                return True
    return False

# ============================================================================
# FUNCIÓN UNIFICADA DE CIERRES ACTIVOS (combina CLOSED_STATIONS fijos + eventos.json)
# ============================================================================
CLOSED_STATIONS_FIJOS = []  # Los cierres temporales se gestionan en eventos.json

def get_active_closed_stations(now: datetime) -> List[dict]:
    activos = []
    for closed in CLOSED_STATIONS_FIJOS:
        if closed["start"] <= now.date() <= closed["end"]:
            activos.append(closed)
    for ev in EVENTOS['cierres_estaciones']:
        if ev['start'] <= now.date() <= ev['end']:
            activos.append({
                "station": ev['station'],
                "reduction_seconds": ev['reduction_seconds']
            })
    return activos

# ============================================================================
# FUNCIONES DE EXTENSIÓN HORARIA
# ============================================================================
def get_extension_horario(now: datetime) -> Optional[dict]:
    hoy = now.date()
    for ext in EVENTOS['extensiones_horario']:
        if ext['fecha'] == hoy:
            return ext
    return None

def get_extension_message(now: datetime) -> str:
    ext = get_extension_horario(now)
    if not ext:
        return ""
    desc = ext.get('descripcion', 'Estensione di orario')
    return f"🕐 Oggi orario prolungato: {desc}.\n"

# ============================================================================
# TIEMPOS DE VIAJE
# ============================================================================
def get_travel_time_from_montepo(station: str, now: datetime) -> int:
    total_seconds = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in FORWARD_PEAK:
        measured = get_measured_travel_time(start, end, 'ida', now)
        if measured is not None:
            sec = measured
        else:
            sec = base_sec
            if not peak and (start, end) in EXTRA_TRAMOS_FORWARD:
                sec -= 10
        total_seconds += sec
        if end == station:
            break
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for closed in get_active_closed_stations(now):
        if closed["station"] == station:
            continue
        if closed["station"] in stations_order and station in stations_order:
            if stations_order.index(closed["station"]) < stations_order.index(station):
                total_seconds -= closed["reduction_seconds"]
    if should_add_giovanni_extra(now):
        idx_station = stations_order.index(station) if station in stations_order else -1
        idx_giovanni = stations_order.index("giovanni")
        if idx_station >= idx_giovanni:
            total_seconds += 5
    if peak and station != "montepo":
        total_seconds += 5
    minutes = (total_seconds + 59) // 60
    return minutes

def get_travel_time_from_stesicoro(station: str, now: datetime) -> int:
    total_seconds = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in REVERSE_PEAK:
        measured = get_measured_travel_time(start, end, 'vuelta', now)
        if measured is not None:
            sec = measured
        else:
            sec = base_sec
            if not peak and (start, end) in EXTRA_TRAMOS_REVERSE:
                sec -= 10
        total_seconds += sec
        if end == station:
            break
    stations_order_rev = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    for closed in get_active_closed_stations(now):
        if closed["station"] == station:
            continue
        if closed["station"] in stations_order_rev and station in stations_order_rev:
            if stations_order_rev.index(closed["station"]) < stations_order_rev.index(station):
                total_seconds -= closed["reduction_seconds"]
    if should_add_giovanni_extra(now):
        idx_station = stations_order_rev.index(station) if station in stations_order_rev else -1
        idx_giovanni = stations_order_rev.index("giovanni")
        if idx_station >= idx_giovanni:
            total_seconds += 5
    if peak and station != "stesicoro":
        total_seconds += 5
    minutes = (total_seconds + 59) // 60
    return max(0, minutes)

# ============================================================================
# FUNCIONES DE CIERRE (mensajes y comprobación)
# ============================================================================
def is_station_closed(station: str, now: datetime) -> bool:
    for closed in get_active_closed_stations(now):
        if closed["station"] == station:
            return True
    return False

def get_closing_message(station: str, now: datetime) -> str:
    for closed in get_active_closed_stations(now):
        if closed["station"] == station:
            for c in CLOSED_STATIONS_FIJOS:
                if c['station'] == station and c['start'] <= now.date() <= c['end']:
                    end_date = c['end'].strftime('%d/%m/%Y')
                    return f"⚠️ La stazione {NOMBRE_MOSTRAR.get(station, station).capitalize()} è chiusa per lavori fino al {end_date}. I treni non fermano.\n"
            for ev in EVENTOS['cierres_estaciones']:
                if ev['station'] == station and ev['start'] <= now.date() <= ev['end']:
                    end_date = ev['end'].strftime('%d/%m/%Y')
                    return f"⚠️ La stazione {NOMBRE_MOSTRAR.get(station, station).capitalize()} è chiusa per lavori fino al {end_date}. I treni non fermano.\n"
    return ""

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
    base_url = STATION_IMAGE.get(estacion_key)
    if not base_url:
        return None
    cache_buster = int(timer.time())
    return f"{base_url}?v={cache_buster}"

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

# ============================================================================
# FUNCIONES PARA SANT'AGATA
# ============================================================================
def is_sant_agata(now: datetime) -> bool:
    eff = get_effective_datetime(now)
    return (eff.month == SANT_AGATA["month"] and 
            eff.day in SANT_AGATA["days"] and 
            SANT_AGATA["active"])

def get_first_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["first"])

def get_last_train_sant_agata(station: str) -> time:
    return str_to_time(SANT_AGATA["special_hours"][station]["last"])

def get_next_departure_sant_agata(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    return (None, 0, 0, False)

def get_sant_agata_message(station: str, now: datetime) -> str:
    first = SANT_AGATA["special_hours"][station]["first"]
    last = SANT_AGATA["special_hours"][station]["last"]
    return (
        f"🎉 **Orario speciale Sant'Agata**\n"
        f"Oggi i treni da {station.replace('Montepo','Monte Po')} circolano dalle **{first}** all'**{last}**.\n"
        f"Frequenza: ogni **5 minuti** in ora di punta, ogni **7 minuti** in ora di valle."
    )

# ============================================================================
# DÍAS FESTIVOS NACIONALES Y NOCHEVIEJA
# ============================================================================
FESTIVI_NAZIONALI = [
    (1, 1), (1, 6), (4, 25), (5, 1), (6, 2), (8, 15), (11, 1), (12, 8), (12, 26)
]

def is_new_years_eve(now: datetime) -> bool:
    eff = get_effective_datetime(now)
    if eff.month == 12 and eff.day == 31 and now.hour >= 12:
        return True
    if eff.month == 1 and eff.day == 1 and now.hour < 3:
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
    eff = get_effective_datetime(now)
    return (eff.month == CLOSED_ALL_DAY["christmas"]["month"] and 
            eff.day == CLOSED_ALL_DAY["christmas"]["day"] and
            CLOSED_ALL_DAY["christmas"]["active"])

def is_easter_sunday(now: datetime) -> bool:
    if not CLOSED_ALL_DAY["easter_sunday"]["active"]:
        return False
    eff = get_effective_datetime(now)
    year = eff.year
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
    return eff.date() == easter and eff.weekday() == 6

def is_easter_monday(now: datetime) -> bool:
    eff = get_effective_datetime(now)
    year = eff.year
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
    return eff.date() == easter_monday

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
    eff = get_effective_datetime(now)
    if is_christmas(eff) or is_new_years_eve(eff) or is_sant_agata(eff):
        return False
    if is_easter_sunday(eff):
        return False
    if is_easter_monday(eff):
        return True
    return (eff.month, eff.day) in FESTIVI_NAZIONALI

# ============================================================================
# HORARIOS DE APERTURA Y CIERRE (con soporte para extensiones)
# ============================================================================
def get_opening_time(now: datetime, station: str = None) -> Tuple[int, int]:
    if is_new_years_eve(now):
        return (12, 0)
    if is_sant_agata(now):
        first = get_first_train_sant_agata(station if station else "Montepo")
        return (first.hour, first.minute)
    # Verificar extensión (solo si define primer_tren)
    ext = get_extension_horario(now)
    if ext and station:
        datos = ext['horario_extendido'].get(station, {})
        if 'primer_tren' in datos:
            h, m = map(int, datos['primer_tren'].split(':'))
            return (h, m)
    if is_festivo_nazionale(now):
        return (7, 0)
    return (6, 0)

def get_closing_time(now: datetime, station: str) -> Tuple[int, int]:
    # Verificar extensión horaria
    ext = get_extension_horario(now)
    if ext and station in ext['horario_extendido']:
        datos = ext['horario_extendido'][station]
        if 'ultimo_tren' in datos:
            h, m = map(int, datos['ultimo_tren'].split(':'))
            return (h, m)
    if is_new_years_eve(now):
        return (3, 0)
    if is_sant_agata(now):
        last = get_last_train_sant_agata(station)
        return (last.hour, last.minute)

    if is_festivo_nazionale(now):
        if now.weekday() in (4, 5, 6):
            return (1, 0)
        else:
            return (22, 30)
    else:
        if now.weekday() in (4, 5):
            return (1, 0)
        else:
            return (22, 30)

# ============================================================================
# FECHAS ESPECIALES (sobrescribir día de la semana)
# ============================================================================
def get_override_weekday(now: datetime) -> Optional[int]:
    eff = get_effective_datetime(now)
    month, day = eff.month, eff.day
    if month == 12 and day == 31:
        return 4
    if month == 1 and day == 1:
        return 6
    if month == 2 and day in [3, 4, 5]:
        return 4
    if month == 2 and day == 6:
        actual_weekday = eff.weekday()
        if actual_weekday == 6:
            return 6
        else:
            return 5
    return None

# ============================================================================
# OBTENER LISTA DE HORARIOS (con extensión de trenes extra)
# ============================================================================
def get_schedule_list(station: str, now: datetime) -> List[time]:
    eff = get_effective_datetime(now)
    override = get_override_weekday(now)
    if override is not None:
        if override == 4:
            schedule_list = SCHEDULES[station]["friday"]
        elif override == 5:
            schedule_list = SCHEDULES[station]["saturday"]
        elif override == 6:
            schedule_list = SCHEDULES[station]["sunday"]
        else:
            schedule_list = SCHEDULES[station]["weekday"]
    else:
        if is_festivo_nazionale(now):
            weekday_eff = eff.weekday()
            if weekday_eff == 4:
                schedule_list = SCHEDULES[station].get("friday_holiday", SCHEDULES[station]["sunday"])
            elif weekday_eff == 5:
                schedule_list = SCHEDULES[station].get("saturday_holiday", SCHEDULES[station]["sunday"])
            elif weekday_eff == 6:
                schedule_list = SCHEDULES[station]["sunday"]
            else:
                schedule_list = SCHEDULES[station].get("weekday_holiday", SCHEDULES[station]["sunday"])
        else:
            weekday_num = now.weekday()
            if weekday_num == 4:
                schedule_list = SCHEDULES[station]["friday"]
            elif weekday_num == 5:
                schedule_list = SCHEDULES[station]["saturday"]
            elif weekday_num == 6:
                schedule_list = SCHEDULES[station]["sunday"]
            else:
                schedule_list = SCHEDULES[station]["weekday"]
    
    if not schedule_list:
        return schedule_list
    current_time = now.time()
    first_train = schedule_list[0]
    if current_time < first_train and current_time.hour < 6:
        yesterday = eff - timedelta(days=1)
        y_override = get_override_weekday(yesterday)
        if y_override is not None:
            if y_override == 4:
                yesterday_list = SCHEDULES[station]["friday"]
            elif y_override == 5:
                yesterday_list = SCHEDULES[station]["saturday"]
            elif y_override == 6:
                yesterday_list = SCHEDULES[station]["sunday"]
            else:
                yesterday_list = SCHEDULES[station]["weekday"]
        else:
            y_weekday = yesterday.weekday()
            if y_weekday == 4:
                yesterday_list = SCHEDULES[station]["friday"]
            elif y_weekday == 5:
                yesterday_list = SCHEDULES[station]["saturday"]
            elif y_weekday == 6:
                yesterday_list = SCHEDULES[station]["sunday"]
            else:
                yesterday_list = SCHEDULES[station]["weekday"]
        if any(t.hour >= 22 or t.hour < 6 for t in yesterday_list):
            return yesterday_list

    # ---- Extensión horaria: añadir trenes extra si corresponde ----
    extension = get_extension_horario(now)
    if extension and extension.get('mantiene_frecuencia') and station in extension['horario_extendido']:
        datos = extension['horario_extendido'][station]
        if 'ultimo_tren' in datos:
            # Calcular frecuencia media a partir de la lista base
            if len(schedule_list) >= 2:
                diffs = []
                for i in range(1, min(10, len(schedule_list))):
                    t1 = schedule_list[-i-1]
                    t2 = schedule_list[-i]
                    diff = (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)
                    if diff > 0:
                        diffs.append(diff)
                freq = int(mean(diffs)) if diffs else 13
            else:
                freq = 13
            
            ultimo_base = schedule_list[-1]
            h_ult, m_ult = map(int, datos['ultimo_tren'].split(':'))
            ultimo_extendido = time(h_ult, m_ult)
            
            # Generar trenes adicionales
            actual = ultimo_base
            while True:
                next_min = (actual.hour * 60 + actual.minute) + freq
                if next_min >= 24 * 60:
                    break
                actual = time(next_min // 60, next_min % 60)
                if actual > ultimo_extendido:
                    break
                # Evitar duplicados exactos
                if actual not in schedule_list:
                    schedule_list.append(actual)
    
    return schedule_list

# ============================================================================
# PRÓXIMO TREN (versión corregida con now.date())
# ============================================================================
def get_next_departure(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
    if 1 <= now.hour < 6:
        if (now.month == 1 and now.day == 1 and 1 <= now.hour < 3) or \
           (now.month == 2 and now.day in [4,5,6] and 1 <= now.hour < 2):
            pass
        else:
            close_h, close_m = get_closing_time(now, station)
            if 1 <= close_h <= 3 and now.time() < time(close_h, close_m):
                pass
            else:
                return (None, 0, 0, False)
    if is_new_years_eve(now):
        return get_next_departure_new_years_eve(station, now)
    if is_sant_agata(now):
        return get_next_departure_sant_agata(station, now)
    
    schedule_list = get_schedule_list(station, now)
    if not schedule_list:
        return (None, 0, 0, False)
    
    current_time = now.time()
    next_dep_time = None
    for dep_time in schedule_list:
        if dep_time > current_time:
            next_dep_time = dep_time
            break
    
    if next_dep_time:
        candidate = datetime.combine(now.date(), next_dep_time)
        if candidate.tzinfo is None:
            candidate = CATANIA_TZ.localize(candidate)
        if candidate <= now:
            candidate += timedelta(days=1)
    else:
        tomorrow = now.date() + timedelta(days=1)
        candidate = datetime.combine(tomorrow, schedule_list[0])
        candidate = CATANIA_TZ.localize(candidate)
    
    delta = int((candidate - now).total_seconds())
    return (candidate, delta // 60, delta % 60, True)

def get_next_departure_after(station: str, now: datetime, after_time: time) -> Tuple[Optional[datetime], int, int, bool]:
    if 1 <= now.hour < 6:
        if (now.month == 1 and now.day == 1 and 1 <= now.hour < 3) or \
           (now.month == 2 and now.day in [4,5,6] and 1 <= now.hour < 2):
            pass
        else:
            close_h, close_m = get_closing_time(now, station)
            if 1 <= close_h <= 3 and now.time() < time(close_h, close_m):
                pass
            else:
                return (None, 0, 0, False)
    if is_sant_agata(now):
        fake_now = datetime.combine(now.date(), after_time) + timedelta(minutes=1)
        fake_now = CATANIA_TZ.localize(fake_now)
        return get_next_departure(station, fake_now)
    if is_new_years_eve(now):
        fake_now = datetime.combine(now.date(), after_time) + timedelta(minutes=1)
        fake_now = CATANIA_TZ.localize(fake_now)
        return get_next_departure(station, fake_now)
    
    schedule_list = get_schedule_list(station, now)
    if not schedule_list:
        return (None, 0, 0, False)
    
    next_dep_time = None
    for dep_time in schedule_list:
        if dep_time > after_time:
            next_dep_time = dep_time
            break
    
    if next_dep_time:
        candidate = datetime.combine(now.date(), next_dep_time)
        if candidate.tzinfo is None:
            candidate = CATANIA_TZ.localize(candidate)
        if candidate <= now:
            candidate += timedelta(days=1)
    else:
        tomorrow = now.date() + timedelta(days=1)
        candidate = datetime.combine(tomorrow, schedule_list[0])
        candidate = CATANIA_TZ.localize(candidate)
    
    delta = int((candidate - now).total_seconds())
    return (candidate, delta // 60, delta % 60, True)

# ============================================================================
# FORMATO DE TIEMPO (con fracciones de 10 segundos cuando ≤ 90 segundos)
# ============================================================================
def format_time(minutes: int, seconds: int) -> str:
    total_seconds = minutes * 60 + seconds

    if total_seconds <= 90:
        rounded_seconds = (seconds + 5) // 10 * 10
        if rounded_seconds == 60:
            minutes += 1
            rounded_seconds = 0
        if minutes == 0:
            return "subito" if rounded_seconds == 0 else f"{rounded_seconds} secondi"
        else:
            return "1 minuto" if rounded_seconds == 0 else f"1 minuto e {rounded_seconds} secondi"

    if total_seconds <= 300:
        rounded_total = (total_seconds + 15) // 30 * 30
        r_min = rounded_total // 60
        r_sec = rounded_total % 60
        if r_sec == 0:
            return f"{r_min} minuti" if r_min != 1 else "1 minuto"
        else:
            return f"{r_min} minuti e {r_sec} secondi" if r_min != 1 else f"1 minuto e {r_sec} secondi"

    rounded_minutes = (total_seconds + 30) // 60
    return f"{rounded_minutes} minuti"

def get_last_train_message(now: datetime, station: str = "Montepo") -> str:
    if (now.month == 12 and now.day == 31 and now.hour >= 12) or (now.month == 1 and now.day == 1 and now.hour < 3):
        return "🎉 Oggi orario speciale: ultimo treno alle 03:00. Buon anno! 🎉"
    if now.hour < 20 or (now.hour == 20 and now.minute < 30):
        return ""
    if is_sant_agata(now) or is_closed_all_day(now):
        return ""
    close_h, close_m = get_closing_time(now, station)
    return f"📌 Oggi la metro chiude alle {close_h:02d}:{close_m:02d}."

def is_metro_closed(now: datetime, station: str) -> Tuple[bool, Optional[datetime], str]:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    
    if is_closed_all_day(now):
        tomorrow = now + timedelta(days=1)
        open_h, open_m = get_opening_time(tomorrow, station)
        next_open = datetime.combine(tomorrow.date(), time(open_h, open_m))
        next_open = CATANIA_TZ.localize(next_open)
        return (True, next_open, "")
    
    if is_new_years_eve(now):
        if now.hour >= 23 or now.hour < 3:
            open_h, open_m = get_opening_time(now, station)
            next_open = datetime.combine(now.date(), time(open_h, open_m))
            if next_open <= now:
                next_open = datetime.combine(now.date() + timedelta(days=1), time(open_h, open_m))
            next_open = CATANIA_TZ.localize(next_open)
            special_msg = "🚇 Non ci sono informazioni disponibili. Ricorda che oggi l'ultima metropolitana è partita alle 03:00."
            return (True, next_open, special_msg)
    
    if 1 <= now.hour < 6:
        close_h_check, close_m_check = get_closing_time(now, station)
        closing_time_check = time(close_h_check, close_m_check)
        is_late_closing = 1 <= close_h_check <= 3
        if is_late_closing and now.time() < closing_time_check:
            pass
        else:
            open_h, open_m = get_opening_time(now, station)
            next_open = CATANIA_TZ.localize(datetime.combine(now.date(), time(open_h, open_m)))
            if next_open <= now:
                tomorrow = datetime.combine(now.date() + timedelta(days=1), time(12, 0))
                tomorrow = CATANIA_TZ.localize(tomorrow)
                open_h, open_m = get_opening_time(tomorrow, station)
                next_open = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(open_h, open_m)))
            return (True, next_open, "🚇 La metropolitana è chiusa in questo momento.")
    
    current_time = now.time()
    open_h, open_m = get_opening_time(now, station)
    close_h, close_m = get_closing_time(now, station)
    opening_time = time(open_h, open_m)
    closing_time = time(close_h, close_m)
    
    if close_h < open_h or (close_h == open_h and close_m < open_m):
        if current_time >= opening_time or current_time < closing_time:
            return (False, None, "")
        else:
            if current_time < opening_time:
                next_open = CATANIA_TZ.localize(datetime.combine(now.date(), opening_time))
            else:
                tomorrow = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(12, 0)))
                oh, om = get_opening_time(tomorrow, station)
                next_open = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(oh, om)))
            return (True, next_open, "")
    else:
        if current_time >= closing_time or current_time < opening_time:
            if current_time < opening_time:
                next_open = CATANIA_TZ.localize(datetime.combine(now.date(), opening_time))
            else:
                tomorrow = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(12, 0)))
                oh, om = get_opening_time(tomorrow, station)
                next_open = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(oh, om)))
            return (True, next_open, "")
        return (False, None, "")

# ============================================================================
# FUNCIONES PARA ESTACIONES INTERMEDIAS
# ============================================================================
def get_total_seconds_from_montepo(station: str, now: datetime) -> int:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in FORWARD_PEAK:
        measured = get_measured_travel_time(start, end, 'ida', now)
        if measured is not None:
            sec = measured
        else:
            sec = base_sec
            if not peak and (start, end) in EXTRA_TRAMOS_FORWARD:
                sec -= 10
        total += sec
        if end == station:
            break
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for closed in get_active_closed_stations(now):
        if is_station_closed(closed["station"], now):
            if stations_order.index(closed["station"]) < stations_order.index(station):
                total -= closed["reduction_seconds"]
    if should_add_giovanni_extra(now):
        idx_station = stations_order.index(station) if station in stations_order else -1
        idx_giovanni = stations_order.index("giovanni")
        if idx_station >= idx_giovanni:
            total += 5
    if peak and station != "montepo":
        total += 5
    return max(0, int(total))

def get_total_seconds_from_stesicoro(station: str, now: datetime) -> int:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in REVERSE_PEAK:
        measured = get_measured_travel_time(start, end, 'vuelta', now)
        if measured is not None:
            sec = measured
        else:
            sec = base_sec
            if not peak and (start, end) in EXTRA_TRAMOS_REVERSE:
                sec -= 10
        total += sec
        if end == station:
            break
    stations_order_rev = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    for closed in get_active_closed_stations(now):
        if is_station_closed(closed["station"], now):
            if stations_order_rev.index(closed["station"]) < stations_order_rev.index(station):
                total -= closed["reduction_seconds"]
    if should_add_giovanni_extra(now):
        idx_station = stations_order_rev.index(station) if station in stations_order_rev else -1
        idx_giovanni = stations_order_rev.index("giovanni")
        if idx_station >= idx_giovanni:
            total += 5
    if peak and station != "stesicoro":
        total += 5
    return max(0, int(total))

def get_next_train_at_station(now: datetime, estacion_key: str) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    tiempos_seg = {}
    stations = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for st in stations:
        tiempos_seg[st] = (get_total_seconds_from_montepo(st, now), get_total_seconds_from_stesicoro(st, now))
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

# ============================================================================
# FUNCIONES DE LOCALIZACIÓN
# ============================================================================
def get_current_station_from_montepo(now: datetime, seconds_passed: int) -> str:
    stations = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    tiempos = {st: get_total_seconds_from_montepo(st, now) for st in stations}
    if 0 < seconds_passed < 30:
        return "Il treno è appena partito da Monte Po"
    for i in range(len(stations)-1):
        cur, nxt = stations[i], stations[i+1]
        if seconds_passed >= tiempos[cur] - 1 and seconds_passed < tiempos[nxt]:
            return NOMBRE_MOSTRAR[cur]
    if seconds_passed >= tiempos["stesicoro"] - 1:
        return NOMBRE_MOSTRAR["stesicoro"]
    if seconds_passed == 0:
        return "non ancora partito da Monte Po"
    return NOMBRE_MOSTRAR["montepo"]

def get_current_station_from_stesicoro(now: datetime, seconds_passed: int) -> str:
    stations = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    tiempos = {st: get_total_seconds_from_stesicoro(st, now) for st in stations}
    if 0 < seconds_passed < 30:
        return "Il treno è appena partito da Stesicoro"
    for i in range(len(stations)-1):
        cur, nxt = stations[i], stations[i+1]
        if seconds_passed >= tiempos[cur] - 1 and seconds_passed < tiempos[nxt]:
            return NOMBRE_MOSTRAR[cur]
    if seconds_passed >= tiempos["montepo"] - 1:
        return NOMBRE_MOSTRAR["montepo"]
    if seconds_passed == 0:
        return "non ancora partito da Stesicoro"
    return NOMBRE_MOSTRAR["stesicoro"]

def format_time_precise(minutes: int, seconds: int) -> str:
    return format_time(minutes, seconds)
