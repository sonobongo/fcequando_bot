import os
import json
import logging
from datetime import datetime, time, timedelta, date
from typing import Tuple, Optional, List, Dict, Any
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    
    if current_time < first:
        next_dt = datetime.combine(now.date(), first)
        next_dt = CATANIA_TZ.localize(next_dt)
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec // 60, sec % 60, True)
    
    if current_time >= last:
        tomorrow = now.date() + timedelta(days=1)
        next_dt = datetime.combine(tomorrow, first)
        next_dt = CATANIA_TZ.localize(next_dt)
        sec = int((next_dt - now).total_seconds())
        return (next_dt, sec // 60, sec % 60, True)
    
    first_min = first.hour * 60 + first.minute
    last_min = last.hour * 60 + last.minute
    current_min = current_time.hour * 60 + current_time.minute
    
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

# ============================================================================
# FUNCIONES DE HORARIOS (comunes para Monte Po y Stesicoro)
# ============================================================================
def get_opening_time(now: datetime, station: str = None) -> Tuple[int, int]:
    if is_sant_agata(now):
        first = get_first_train_sant_agata(station if station else "Montepo")
        return (first.hour, first.minute)
    else:
        weekday = now.weekday()
        if weekday == 6:
            return (7, 0)
        else:
            return (6, 0)

def get_closing_time(now: datetime, station: str) -> Tuple[int, int]:
    if is_sant_agata(now):
        last = get_last_train_sant_agata(station)
        return (last.hour, last.minute)
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
    weekday_num = now.weekday()
    if weekday_num == 4:
        return SCHEDULES[station]["friday"]
    elif weekday_num == 5:
        return SCHEDULES[station]["saturday"]
    elif weekday_num == 6:
        return SCHEDULES[station]["sunday"]
    else:
        return SCHEDULES[station]["weekday"]

def get_next_departure(station: str, now: datetime) -> Tuple[Optional[datetime], int, int, bool]:
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
    
    schedule_list = get_schedule_list(station, now)
    for dep_time in schedule_list:
        if dep_time > after_time:
            next_dt = datetime.combine(now.date(), dep_time)
            next_dt = CATANIA_TZ.localize(next_dt)
            delta = int((next_dt - now).total_seconds())
            return (next_dt, delta // 60, delta % 60, True)
    return (None, 0, 0, False)

def format_time(minutes: int, seconds: int) -> str:
    if minutes < SHORT_TIME_THRESHOLD:
        if seconds >= 30:
            minutes += 1
        if minutes == 0:
            return "meno di un minuto"
        elif minutes == 1:
            return "1 minuto"
        else:
            return f"{minutes} minuti"
    else:
        return f"{minutes} minuti"

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
# FUNCIONES PARA CUALQUIER ESTACIÓN (CORREGIDO: incluye trenes ya salidos)
# ============================================================================
def get_next_train_at_station(now: datetime, estacion_key: str) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    """
    Retorna (info_tren_hacia_Stesicoro, info_tren_hacia_MontePo)
    Cada info es (hora_paso_por_estacion, minutos_restantes, segundos_restantes, siguiente_info)
    donde siguiente_info es (hora_paso, minutos, segundos) o None.
    Corregido para tener en cuenta trenes ya salidos pero aún no llegados.
    """
    if estacion_key not in TIEMPOS_ESTACION:
        return (None, None)
    
    t_mp, t_st = TIEMPOS_ESTACION[estacion_key]
    now_time = now.time()
    
    # --- Dirección Monte Po -> Stesicoro ---
    info_mp = None
    closed_mp, _ = is_metro_closed(now, "Montepo")
    if not closed_mp:
        # Obtener todos los horarios de salida de Montepo para hoy
        schedule_list = get_schedule_list("Montepo", now)
        # Calcular horas de paso por la estación intermedia
        pasos = []
        for salida in schedule_list:
            paso_dt = datetime.combine(now.date(), salida) + timedelta(minutes=t_mp)
            paso_dt = CATANIA_TZ.localize(paso_dt)
            pasos.append(paso_dt)
        # Encontrar el primer paso que sea > ahora
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
            # Siguiente tren después de este (misma dirección)
            next_info = None
            if next_index + 1 < len(pasos):
                next_paso2 = pasos[next_index + 1]
                delta2 = next_paso2 - now
                mins2 = int(delta2.total_seconds() // 60)
                secs2 = int(delta2.total_seconds() % 60)
                next_info = (next_paso2, mins2, secs2)
            info_mp = (next_paso, mins_rest, secs_rest, next_info)
    
    # --- Dirección Stesicoro -> Monte Po ---
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

# ============================================================================
# RESPUESTA PARA CUALQUIER ESTACIÓN
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, simulated_now: datetime = None, return_to_main: bool = True):
    now = simulated_now if simulated_now is not None else datetime.now(CATANIA_TZ)
    
    warning = get_closing_warning(now)
    if warning:
        await update.message.reply_text(warning, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    
    special_msg = SANT_AGATA.get("message", "") + "\n\n" if is_sant_agata(now) else ""
    
    if is_closed_all_day(now):
        msg = f"{special_msg}🚇 Oggi la metropolitana è chiusa tutto il giorno.\n🕒 Riaprirà domani mattina."
        await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    # Caso especial para Monte Po y Stesicoro (salida desde la estación)
    if estacion_key in ["montepo", "stesicoro"]:
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open = is_metro_closed(now, station)
        if closed:
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure(station, now)
                if not has_first:
                    first_train, _, _, _ = get_next_departure(station, now + timedelta(days=1))
                station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
                msg = f"{special_msg}🚇 La metropolitana è chiusa in questo momento. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
            else:
                msg = f"{special_msg}🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            msg = f"{special_msg}🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        
        # --- NUEVA LÓGICA PARA MENSAJE DE ANDÉN ---
        if minutes == 0:
            # El tren está en el andén (sale en menos de 60 segundos)
            if seconds == 0:
                msg = f"{special_msg}🚇 Il treno è in binario. Partirà subito."
            else:
                msg = f"{special_msg}🚇 Il treno è in binario. Partirà tra meno di un minuto."
            # Mostrar el siguiente tren si existe
            next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
            if has2:
                time_str2 = format_time(min2, sec2)
                msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
            else:
                msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        elif minutes == 0 and seconds < 30:
            # Caso residual: treno appena partito (no debería ocurrir porque minutes==0 ya cubre todo, pero lo dejamos)
            next2, min2, sec2, has2 = get_next_departure(station, now + timedelta(seconds=30))
            if has2:
                msg = f"{special_msg}🚇 Il treno è appena partito da {station_display}. Il prossimo per {dest} sarà alle {next2.strftime('%H:%M')}."
            else:
                msg = f"{special_msg}🚇 Il treno è appena partito da {station_display}. Non ci sono altri treni oggi."
        else:
            time_str = format_time(minutes, seconds)
            # Mostrar mensaje principal
            if minutes < NEXT_TRAIN_THRESHOLD:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}."
            elif minutes < SHORT_TIME_THRESHOLD:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}."
            else:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}, alle {next_dep.strftime('%H:%M')}."
            # Mostrar siguiente tren si existe y faltan menos de NEXT_TRAIN_THRESHOLD minutos
            if minutes < NEXT_TRAIN_THRESHOLD:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    time_str2 = format_time(min2, sec2)
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        
        last_msg = get_last_train_message(now)
        if last_msg and not is_sant_agata(now):
            msg += f"\n\n{last_msg}"
        await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    # Para estaciones intermedias (incluye Milo)
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    
    msg = f"{special_msg}🚆 **Prossimi treni a {nombre}**\n\n"
    
    # Dirección hacia Stesicoro (tren que viene de Monte Po)
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            msg += f"🚇 **Per Stesicoro**: treno in arrivo.\n"
        else:
            msg += f"🚇 **Per Stesicoro**: prossimo treno passa tra {time_str}, alle {paso_mp.strftime('%H:%M')}.\n"
        # Mostrar siguiente si faltan menos de NEXT_TRAIN_THRESHOLD minutos
        if mins < NEXT_TRAIN_THRESHOLD and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🚫 **Per Stesicoro**: nessun treno in arrivo al momento.\n"
    
    # Dirección hacia Monte Po (tren que viene de Stesicoro)
    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            msg += f"🚇 **Per Monte Po**: treno in arrivo.\n"
        else:
            msg += f"🚇 **Per Monte Po**: prossimo treno passa tra {time_str}, alle {paso_st.strftime('%H:%M')}.\n"
        if mins < NEXT_TRAIN_THRESHOLD and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🚫 **Per Monte Po**: nessun treno in arrivo al momento.\n"
    
    last_msg = get_last_train_message(now)
    if last_msg and not is_sant_agata(now):
        msg += f"\n{last_msg}"
    
    await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')

# ============================================================================
# TECLADOS
# ============================================================================
keyboard_main = ReplyKeyboardMarkup(
    [[KeyboardButton("Monte Po"), KeyboardButton("Altri"), KeyboardButton("Stesicoro")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

keyboard_altri = ReplyKeyboardMarkup(
    [
        ["Fontana", "Nesima", "San Nullo"],
        ["Cibali", "Milo", "Borgo"],
        ["Giuffrida", "Italia", "Galatea"],
        ["Giovanni XXIII", "← Menu"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

BOTON_TO_KEY = {
    "Monte Po": "montepo",
    "Stesicoro": "stesicoro",
    "Fontana": "fontana",
    "Nesima": "nesima",
    "San Nullo": "sannullo",
    "Cibali": "cibali",
    "Milo": "milo",
    "Borgo": "borgo",
    "Giuffrida": "giuffrida",
    "Italia": "italia",
    "Galatea": "galatea",
    "Giovanni XXIII": "giovanni"
}

# ============================================================================
# MANEJADORES DE COMANDOS
# ============================================================================
async def cmd_montepo(update, context): await send_station_response(update, context, "montepo", return_to_main=False)
async def cmd_stesicoro(update, context): await send_station_response(update, context, "stesicoro", return_to_main=False)
async def cmd_milo(update, context): await send_station_response(update, context, "milo", return_to_main=False)
async def cmd_fontana(update, context): await send_station_response(update, context, "fontana", return_to_main=False)
async def cmd_nesima(update, context): await send_station_response(update, context, "nesima", return_to_main=False)
async def cmd_sannullo(update, context): await send_station_response(update, context, "sannullo", return_to_main=False)
async def cmd_cibali(update, context): await send_station_response(update, context, "cibali", return_to_main=False)
async def cmd_borgo(update, context): await send_station_response(update, context, "borgo", return_to_main=False)
async def cmd_giuffrida(update, context): await send_station_response(update, context, "giuffrida", return_to_main=False)
async def cmd_italia(update, context): await send_station_response(update, context, "italia", return_to_main=False)
async def cmd_galatea(update, context): await send_station_response(update, context, "galatea", return_to_main=False)
async def cmd_giovanni(update, context): await send_station_response(update, context, "giovanni", return_to_main=False)

async def cmd_altri(update, context):
    await update.message.reply_text("🚇 **Altre stazioni**\nSeleziona una stazione:", reply_markup=keyboard_altri, parse_mode='Markdown')

async def start(update, context):
    user = update.effective_user
    now = datetime.now(CATANIA_TZ)
    last_msg = get_last_train_message(now)
    await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Posso dirti quando passa il prossimo treno della metropolitana di Catania.\n"
        "Premi uno dei pulsanti qui sotto o usa i comandi /montepo, /stesicoro, /milo, /altri, /fontana, ecc.\n\n"
        f"{last_msg}",
        reply_markup=keyboard_main
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Comandi disponibili:\n"
        "/start - Messaggio di benvenuto\n"
        "/help - Questo aiuto\n"
        "/montepo - Prossimi treni a Monte Po\n"
        "/stesicoro - Prossimi treni a Stesicoro\n"
        "/milo - Prossimi treni a Milo\n"
        "/altri - Mostra altre stazioni\n"
        "/fontana, /nesima, /sannullo, /cibali, /borgo, /giuffrida, /italia, /galatea, /giovanni\n\n"
        "/test DDMMYYYY HHMM <stazione> - Simula data/ora (es. /test 05042026 0908 borgo)\n\n"
        "Oppure premi i pulsanti.",
        reply_markup=keyboard_main
    )

async def handle_button(update, context):
    text = update.message.text
    if text == "Altri":
        await cmd_altri(update, context)
    elif text == "← Menu":
        await update.message.reply_text("🔙 Ritorno al menu principale.", reply_markup=keyboard_main)
    elif text in BOTON_TO_KEY:
        await send_station_response(update, context, BOTON_TO_KEY[text], return_to_main=True)
    else:
        await update.message.reply_text("Scelta non valida. Usa i pulsanti.", reply_markup=keyboard_main)

async def test_command(update, context):
    if not context.args or len(context.args) < 3:
        await update.message.reply_text("Formato: /test DDMMYYYY HHMM <stazione>\nEsempio: /test 05042026 0908 borgo\n\nStazioni: montepo, stesicoro, milo, fontana, nesima, sannullo, cibali, borgo, giuffrida, italia, galatea, giovanni")
        return
    date_str, time_str, station_name = context.args[0], context.args[1], context.args[2].lower()
    if station_name not in TIEMPOS_ESTACION:
        await update.message.reply_text(f"Stazione '{station_name}' non valida.")
        return
    if len(date_str)!=8 or not date_str.isdigit() or len(time_str)!=4 or not time_str.isdigit():
        await update.message.reply_text("Formato data/ora non valido.")
        return
    day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
    hour, minute = int(time_str[0:2]), int(time_str[2:4])
    if hour>23 or minute>59:
        await update.message.reply_text("Ora non valida.")
        return
    try:
        simulated_now = CATANIA_TZ.localize(datetime(year, month, day, hour, minute))
    except Exception as e:
        await update.message.reply_text(f"Data non valida: {e}")
        return
    await send_station_response(update, context, station_name, simulated_now, return_to_main=False)

# ============================================================================
# CONFIGURACIÓN DEL LOGGING
# ============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Token mancante")
        return
    app = Application.builder().token(TOKEN).build()
    for cmd, handler in [
        ("start", start), ("help", help_command), ("montepo", cmd_montepo), ("stesicoro", cmd_stesicoro),
        ("milo", cmd_milo), ("altri", cmd_altri), ("fontana", cmd_fontana), ("nesima", cmd_nesima),
        ("sannullo", cmd_sannullo), ("cibali", cmd_cibali), ("borgo", cmd_borgo), ("giuffrida", cmd_giuffrida),
        ("italia", cmd_italia), ("galatea", cmd_galatea), ("giovanni", cmd_giovanni), ("test", test_command)
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(MessageHandler(filters.Text(["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo", "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]), handle_button))
    
    # Pequeña pausa para evitar conflictos con webhook residuales
    import time
    time.sleep(2)
    
    logger.info("Bot avviato. Premi Ctrl+C per fermare.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
