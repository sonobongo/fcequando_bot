import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from horarios_logic import *
import pytz

CATANIA_TZ = pytz.timezone('Europe/Rome')

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
# FUNCIONES AUXILIARES PARA LOCALIZAR EL TREN (versión corregida)
# ============================================================================
def get_total_seconds_from_montepo(station: str, now: datetime) -> int:
    """Devuelve los segundos acumulados desde Monte Po hasta la estación (sin redondear)."""
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in FORWARD_PEAK:
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_FORWARD:
            sec -= 15
        total += sec
        if end == station:
            break
    stations_order = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            if stations_order.index(closed["station"]) < stations_order.index(station):
                total -= closed["reduction_seconds"]
    return max(0, total)

def get_total_seconds_from_stesicoro(station: str, now: datetime) -> int:
    """Devuelve los segundos acumulados desde Stesicoro hasta la estación (sin redondear)."""
    total = 0
    peak = is_peak_hour(now)
    for (start, end, base_sec) in REVERSE_PEAK:
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_REVERSE:
            sec -= 15
        total += sec
        if end == station:
            break
    stations_order_reverse = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            if stations_order_reverse.index(closed["station"]) < stations_order_reverse.index(station):
                total -= closed["reduction_seconds"]
    return max(0, total)

def get_current_station_from_montepo(now: datetime, seconds_passed: int) -> str:
    """
    Determina en qué estación se encuentra actualmente un tren que salió de Monte Po
    hace 'seconds_passed' segundos.
    """
    # Obtener tiempos acumulados desde Monte Po para cada estación
    tiempos = {}
    total = 0
    peak = is_peak_hour(now)
    stations = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    for i in range(len(stations)-1):
        start = stations[i]
        end = stations[i+1]
        # Buscar el tramo en FORWARD_PEAK
        base_sec = None
        for (s, e, sec) in FORWARD_PEAK:
            if s == start and e == end:
                base_sec = sec
                break
        if base_sec is None:
            continue
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_FORWARD:
            sec -= 15
        total += sec
        tiempos[end] = total
    # Aplicar reducciones por estaciones cerradas
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            reduction = closed["reduction_seconds"]
            idx = stations.index(closed["station"])
            for st in stations[idx+1:]:
                if st in tiempos:
                    tiempos[st] -= reduction
    for st in tiempos:
        if tiempos[st] < 0:
            tiempos[st] = 0
    
    # Buscar la estación actual
    for i in range(len(stations)-1):
        current = stations[i]
        next_st = stations[i+1]
        t_current = tiempos.get(current, 0)
        t_next = tiempos.get(next_st, 0)
        if t_current <= seconds_passed < t_next:
            return NOMBRE_MOSTRAR[current]
    if seconds_passed < tiempos.get("fontana", 0):
        return NOMBRE_MOSTRAR["montepo"]
    return NOMBRE_MOSTRAR["stesicoro"]

def get_current_station_from_stesicoro(now: datetime, seconds_passed: int) -> str:
    """
    Determina en qué estación se encuentra actualmente un tren que salió de Stesicoro
    hace 'seconds_passed' segundos.
    """
    tiempos = {}
    total = 0
    peak = is_peak_hour(now)
    stations = ["stesicoro", "giovanni", "galatea", "italia", "giuffrida", "borgo", "milo", "cibali", "sannullo", "nesima", "fontana", "montepo"]
    for i in range(len(stations)-1):
        start = stations[i]
        end = stations[i+1]
        base_sec = None
        for (s, e, sec) in REVERSE_PEAK:
            if s == start and e == end:
                base_sec = sec
                break
        if base_sec is None:
            continue
        sec = base_sec
        if not peak and (start, end) in EXTRA_TRAMOS_REVERSE:
            sec -= 15
        total += sec
        tiempos[end] = total
    for closed in CLOSED_STATIONS:
        if is_station_closed(closed["station"], now):
            reduction = closed["reduction_seconds"]
            idx = stations.index(closed["station"])
            for st in stations[idx+1:]:
                if st in tiempos:
                    tiempos[st] -= reduction
    for st in tiempos:
        if tiempos[st] < 0:
            tiempos[st] = 0
    
    for i in range(len(stations)-1):
        current = stations[i]
        next_st = stations[i+1]
        t_current = tiempos.get(current, 0)
        t_next = tiempos.get(next_st, 0)
        if t_current <= seconds_passed < t_next:
            return NOMBRE_MOSTRAR[current]
    if seconds_passed < tiempos.get("giovanni", 0):
        return NOMBRE_MOSTRAR["stesicoro"]
    return NOMBRE_MOSTRAR["montepo"]

# ============================================================================
# RESPUESTA NORMAL PARA CUALQUIER ESTACIÓN (CON MODO TEST PERSISTENTE)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    simulated_time = context.chat_data.get('test_time') if context.chat_data else None
    if simulated_time:
        now = simulated_time
        test_indicator = "🧪 [TEST MODE] "
    else:
        now = datetime.now(CATANIA_TZ)
        test_indicator = ""
    
    warning = get_closing_warning(now)
    if warning:
        await update.message.reply_text(warning, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    
    special_msg = SANT_AGATA.get("message", "") + "\n\n" if is_sant_agata(now) else ""
    
    if is_closed_all_day(now):
        msg = f"{special_msg}{test_indicator}🚇 Oggi la metropolitana è chiusa tutto il giorno.\n🕒 Riaprirà domani mattina."
        img = get_station_image(estacion_key, now)
        if img:
            await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    if estacion_key in ["montepo", "stesicoro"]:
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open, special_closing_msg = is_metro_closed(now, station)
        if closed:
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure(station, now)
                if not has_first:
                    first_train, _, _, _ = get_next_departure(station, now + timedelta(days=1))
                station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
                msg = f"{special_msg}{test_indicator}{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
            else:
                if special_closing_msg:
                    msg = f"{special_msg}{test_indicator}{special_closing_msg}"
                else:
                    msg = f"{special_msg}{test_indicator}🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
            img = get_station_image(estacion_key, now)
            if img:
                await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            else:
                await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            msg = f"{special_msg}{test_indicator}🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            img = get_station_image(estacion_key, now)
            if img:
                await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            else:
                await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        if station == "Montepo":
            arrival_time = next_dep
        else:
            arrival_time = next_dep - timedelta(minutes=20)
        remaining = next_dep - now
        mins_rest = int(remaining.total_seconds() // 60)
        secs_rest = int(remaining.total_seconds() % 60)
        time_str_rest = format_time(mins_rest, secs_rest)
        
        if mins_rest <= 4:
            msg = f"{special_msg}{test_indicator}🚇 Il treno è in binario. Partirà tra **{time_str_rest}**."
            if mins_rest <= 1:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    time_str2 = format_time(min2, sec2)
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        else:
            time_str = format_time(minutes, seconds)
            if minutes < SHORT_TIME_THRESHOLD:
                msg = f"{special_msg}{test_indicator}🚇 Prossimo treno per {dest} parte tra **{time_str}**."
            else:
                msg = f"{special_msg}{test_indicator}🚇 Prossimo treno per {dest} parte tra **{time_str}**, alle {next_dep.strftime('%H:%M')}."
            if minutes <= 1:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    time_str2 = format_time(min2, sec2)
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        
        last_msg = get_last_train_message(now)
        if last_msg and not is_sant_agata(now):
            msg += f"\n\n{last_msg}"
        img = get_station_image(estacion_key, now)
        if img:
            await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
        else:
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
        return
    
    # Estaciones intermedias
    closed, next_open, special_closing_msg = is_metro_closed(now, "Montepo")
    if closed:
        mins_to_open = int((next_open - now).total_seconds() // 60)
        if mins_to_open <= 60:
            first_train, _, _, has_first = get_next_departure("Montepo", now)
            if not has_first:
                first_train, _, _, _ = get_next_departure("Montepo", now + timedelta(days=1))
            msg = f"{special_msg}{test_indicator}{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Il primo treno da Monte Po partirà alle {first_train.strftime('%H:%M')}."
        else:
            if special_closing_msg:
                msg = f"{special_msg}{test_indicator}{special_closing_msg}"
            else:
                msg = f"{special_msg}{test_indicator}🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
        img = get_station_image(estacion_key, now)
        if img:
            await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    closing_msg = get_closing_message(estacion_key, now)
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    if closing_msg:
        msg = f"{special_msg}{test_indicator}{closing_msg}\n🚆 **Prossimi treni a {nombre}**\n\n"
    else:
        msg = f"{special_msg}{test_indicator}🚆 **Prossimi treni a {nombre}**\n\n"
    
    estaciones_localizacion = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea"]
    
    # Dirección hacia Monte Po (tren que viene de Stesicoro)
    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            line = f"🔺 **Per Monte Po**: treno in arrivo.\n"
        else:
            if mins < SHORT_TIME_THRESHOLD:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**.\n"
            else:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**, alle {paso_st.strftime('%H:%M')}.\n"
        
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins * 60 + secs
            total_seconds = get_total_seconds_from_stesicoro(estacion_key, now)
            seconds_passed = total_seconds - rest_seconds
            if seconds_passed < 0:
                seconds_passed = 0
            current_station = get_current_station_from_stesicoro(now, seconds_passed)
            # Evitar que muestre Stesicoro si aún no ha salido de allí
            if current_station == "Stesicoro" and seconds_passed < 30:
                current_station = "Stesicoro (appena partito)"
            line += f"   (il treno si trova attualmente a {current_station})\n"
        msg += line
        
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            if mins2 < SHORT_TIME_THRESHOLD:
                msg += f"   Il successivo passerà tra {time_str2}.\n"
            else:
                msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🔺 **Per Monte Po**: nessun treno in arrivo al momento.\n"
    
    # Dirección hacia Stesicoro (tren que viene de Monte Po)
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            line = f"🔻 **Per Stesicoro**: treno in arrivo.\n"
        else:
            if mins < SHORT_TIME_THRESHOLD:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**.\n"
            else:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**, alle {paso_mp.strftime('%H:%M')}.\n"
        
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins * 60 + secs
            total_seconds = get_total_seconds_from_montepo(estacion_key, now)
            seconds_passed = total_seconds - rest_seconds
            if seconds_passed < 0:
                seconds_passed = 0
            current_station = get_current_station_from_montepo(now, seconds_passed)
            if current_station == "Monte Po" and seconds_passed < 30:
                current_station = "Monte Po (appena partito)"
            line += f"   (il treno si trova attualmente a {current_station})\n"
        msg += line
        
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            if mins2 < SHORT_TIME_THRESHOLD:
                msg += f"   Il successivo passerà tra {time_str2}.\n"
            else:
                msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🔻 **Per Stesicoro**: nessun treno in arrivo al momento.\n"
    
    last_msg = get_last_train_message(now)
    if last_msg and not is_sant_agata(now):
        msg += f"\n{last_msg}"
    img = get_station_image(estacion_key, now)
    if img:
        await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')

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
    await update.message.reply_text("⬇️ Altre stazioni:", reply_markup=keyboard_altri)

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
        "/fontana, /nesima, /sannullo, /cibali, /borgo, /giuffrida, /italia, /galatea, /giovanni\n"
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/testfin - Disattiva modalità test\n\n"
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
        estacion_key = BOTON_TO_KEY[text]
        await send_station_response(update, context, estacion_key, return_to_main=True)
    else:
        await update.message.reply_text("Scelta non valida. Usa i pulsanti.", reply_markup=keyboard_main)

# ============================================================================
# COMANDOS TEST
# ============================================================================
async def send_station_response_simulated(update, context, estacion_key: str, simulated_now: datetime):
    original = context.chat_data.get('test_time') if context.chat_data else None
    if context.chat_data is None:
        context.chat_data = {}
    context.chat_data['test_time'] = simulated_now
    await send_station_response(update, context, estacion_key, return_to_main=False)
    if original is None:
        context.chat_data.pop('test_time', None)
    else:
        context.chat_data['test_time'] = original

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🧪 **Modalità test**\n\n"
            "Per fissare una data/ora simulata e usare tutti i bottoni:\n"
            "`/test DDMMYYYY HHMM`\n"
            "Esempio: `/test 11022026 1102`\n\n"
            "Per tornare alla realtà: `/testfin`\n\n"
            "Per una singola risposta (senza cambiare modalità):\n"
            "`/test DDMMYYYY HHMM stazione` (M, S, ML, ecc.)",
            parse_mode='Markdown'
        )
        return
    
    if len(args) == 2:
        date_str, time_str = args[0], args[1]
        if len(date_str) != 8 or not date_str.isdigit():
            await update.message.reply_text("Formato data non valido. Usa DDMMYYYY (es. 11022026).")
            return
        if len(time_str) != 4 or not time_str.isdigit():
            await update.message.reply_text("Formato ora non valido. Usa HHMM (es. 1102).")
            return
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year = int(date_str[4:8])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        if hour > 23 or minute > 59:
            await update.message.reply_text("Ora non valida.")
            return
        try:
            simulated = CATANIA_TZ.localize(datetime(year, month, day, hour, minute))
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        if context.chat_data is None:
            context.chat_data = {}
        context.chat_data['test_time'] = simulated
        await update.message.reply_text(
            f"🧪 **Modalità test attivata**\n"
            f"Ora simulata: {simulated.strftime('%d/%m/%Y %H:%M')}\n"
            f"Usa i bottoni normalmente. Per uscire: `/testfin`",
            parse_mode='Markdown'
        )
        return
    
    if len(args) == 3:
        date_str, time_str, station_code = args[0], args[1], args[2].upper()
        if station_code == "M":
            station = "montepo"
        elif station_code == "S":
            station = "stesicoro"
        elif station_code == "ML":
            station = "milo"
        else:
            await update.message.reply_text("Codice stazione non valido. Usa M, S o ML.")
            return
        if len(date_str) != 8 or not date_str.isdigit():
            await update.message.reply_text("Data non valida.")
            return
        if len(time_str) != 4 or not time_str.isdigit():
            await update.message.reply_text("Ora non valida.")
            return
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year = int(date_str[4:8])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        if hour > 23 or minute > 59:
            await update.message.reply_text("Ora non valida.")
            return
        try:
            simulated = CATANIA_TZ.localize(datetime(year, month, day, hour, minute))
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        await send_station_response_simulated(update, context, station, simulated)
        return
    
    await update.message.reply_text("Comando non riconosciuto. Usa /test DDMMYYYY HHMM o /test DDMMYYYY HHMM X")

async def testfin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data and 'test_time' in context.chat_data:
        del context.chat_data['test_time']
        await update.message.reply_text("✅ Modalità test disattivata. Ora reale ripristinata.")
    else:
        await update.message.reply_text("⚠️ Nessuna modalità test attiva.")
