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
    resize_keyboard=True, one_time_keyboard=False
)

keyboard_altri = ReplyKeyboardMarkup(
    [
        ["Fontana", "Nesima", "San Nullo"],
        ["Cibali", "Milo", "Borgo"],
        ["Giuffrida", "Italia", "Galatea"],
        ["Giovanni XXIII", "← Menu"]
    ],
    resize_keyboard=True, one_time_keyboard=False
)

BOTON_TO_KEY = {
    "Monte Po": "montepo", "Stesicoro": "stesicoro", "Fontana": "fontana",
    "Nesima": "nesima", "San Nullo": "sannullo", "Cibali": "cibali",
    "Milo": "milo", "Borgo": "borgo", "Giuffrida": "giuffrida",
    "Italia": "italia", "Galatea": "galatea", "Giovanni XXIII": "giovanni"
}

# ============================================================================
# FUNCIONES AUXILIARES DE LOCALIZACIÓN
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

# ============================================================================
# RESPUESTA PRINCIPAL
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    simulated = context.chat_data.get('test_time') if context.chat_data else None
    now = simulated if simulated else datetime.now(CATANIA_TZ)
    test_indicator = "🧪 [TEST MODE] " if simulated else ""

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

        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        remaining = next_dep - now
        mins_rest = int(remaining.total_seconds() // 60)
        secs_rest = int(remaining.total_seconds() % 60)
        time_str_rest = format_time(mins_rest, secs_rest)

        if mins_rest <= 4:
            msg = f"{special_msg}{test_indicator}🚇 Il treno è in binario. Partirà tra **{time_str_rest}**."
            if mins_rest <= 1:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {format_time(min2, sec2)}, alle {next2.strftime('%H:%M')}."
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
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {format_time(min2, sec2)}, alle {next2.strftime('%H:%M')}."
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

    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            line = f"🔺 **Per Monte Po**: treno in arrivo.\n"
        else:
            line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**.\n"
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins*60 + secs
            total_seconds = get_total_seconds_from_stesicoro(estacion_key, now)
            if rest_seconds < total_seconds:
                seconds_passed = total_seconds - rest_seconds
                if seconds_passed < 0:
                    seconds_passed = 0
                current_station = get_current_station_from_stesicoro(now, seconds_passed)
                if "appena partito" in current_station:
                    line += f"   ({current_station})\n"
                elif "non ancora partito" not in current_station:
                    line += f"   (il treno si trova attualmente a {current_station})\n"
        msg += line
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            msg += f"   Il successivo passerà tra {format_time(mins2, secs2)}.\n"
    else:
        msg += f"🔺 **Per Monte Po**: nessun treno in arrivo al momento.\n"

    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            line = f"🔻 **Per Stesicoro**: treno in arrivo.\n"
        else:
            line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**.\n"
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins*60 + secs
            total_seconds = get_total_seconds_from_montepo(estacion_key, now)
            if rest_seconds < total_seconds:
                seconds_passed = total_seconds - rest_seconds
                if seconds_passed < 0:
                    seconds_passed = 0
                current_station = get_current_station_from_montepo(now, seconds_passed)
                if "appena partito" in current_station:
                    line += f"   ({current_station})\n"
                elif "non ancora partito" not in current_station:
                    line += f"   (il treno si trova attualmente a {current_station})\n"
        msg += line
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            msg += f"   Il successivo passerà tra {format_time(mins2, secs2)}.\n"
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
        await send_station_response(update, context, BOTON_TO_KEY[text], return_to_main=True)
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
            await update.message.reply_text("Formato data non valido. Usa DDMMYYYY.")
            return
        if len(time_str) != 4 or not time_str.isdigit():
            await update.message.reply_text("Formato ora non valido. Usa HHMM.")
            return
        day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
        hour, minute = int(time_str[0:2]), int(time_str[2:4])
        if hour > 23 or minute > 59:
            await update.message.reply_text("Ora non valida.")
            return
        try:
            simulated = CATANIA_TZ.localize(datetime(year, month, day, hour, minute))
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        context.chat_data['test_time'] = simulated
        await update.message.reply_text(
            f"🧪 **Modalità test attivata**\nOra simulata: {simulated.strftime('%d/%m/%Y %H:%M')}\nUsa i bottoni. Per uscire: `/testfin`",
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
        if len(date_str) != 8 or not date_str.isdigit() or len(time_str) != 4 or not time_str.isdigit():
            await update.message.reply_text("Formato data/ora non valido.")
            return
        day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
        hour, minute = int(time_str[0:2]), int(time_str[2:4])
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
