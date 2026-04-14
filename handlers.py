import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

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
# FUNCIÓN PARA ELIMINAR "[]" DE CUALQUIER TEXTO (Y TAMBIÉN MENSAJES VACÍOS)
# ============================================================================
def clean_text_for_display(text: str) -> str:
    """Elimina '[]', '[ ]' y espacios dobles. Si después de limpiar queda vacío, retorna None."""
    if not text:
        return None
    text = text.replace("[]", "").replace("[ ]", "")
    text = ' '.join(text.split())
    if not text or text == "":
        return None
    return text

# ============================================================================
# FUNCIÓN POUR LE BUS NESIMA → HUMANITAS (30 minutes avant)
# ============================================================================
def get_bus_message(now: datetime) -> str:
    """Retourne le prochain autobus Nesima → Humanitas s'il part dans les 30 minutes, sinon vide."""
    if now.weekday() == 6:  # dimanche
        return ""
    if is_festivo_nazionale(now):
        return ""
    horaires = [("7:30", 7*60+30), ("8:30", 8*60+30), ("9:30", 9*60+30), ("10:30", 10*60+30),
                ("11:30", 11*60+30), ("12:30", 12*60+30), ("13:30", 13*60+30), ("14:30", 14*60+30),
                ("15:30", 15*60+30), ("16:30", 16*60+30), ("17:30", 17*60+30), ("18:30", 18*60+30),
                ("19:30", 19*60+30)]
    maintenant = now.hour * 60 + now.minute
    for heure_str, heure_min in horaires:
        if heure_min > maintenant and (heure_min - maintenant) <= 30:
            return f"🚌 Prossimo autobus per Humanitas alle {heure_str}"
    return ""

# ============================================================================
# CONSTRUCCIÓN DE MENSAJES TEMPORALES (msg2 y msg3)
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str):
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    closing_msg = get_closing_message(estacion_key, now)

    msg2 = ""
    current_station_key_mp = None
    tiempo_restante_mp = None
    mins_mp = 0
    if closing_msg:
        msg2 += f"{closing_msg}\n"
    if info_st:
        paso_st, mins, secs, next_info = info_st
        mins_mp = mins
        time_str = format_time(mins, secs)
        tiempo_restante_mp = mins*60 + secs
        if mins == 0 and secs < 30:
            line = f"🔺 **Per Monte Po**: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**, alle {paso_st.strftime('%H:%M')}.\n"
            else:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**.\n"
        estaciones_localizacion = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "fontana"]
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins*60 + secs
            total_seconds = get_total_seconds_from_stesicoro(estacion_key, now)
            if rest_seconds < total_seconds:
                seconds_passed = total_seconds - rest_seconds
                if seconds_passed < 0:
                    seconds_passed = 0
                current_station = get_current_station_from_stesicoro(now, seconds_passed)
                if current_station == "Monte Po":
                    current_station_key_mp = "montepo"
                    current_station_text = "Il treno è appena partito da Monte Po"
                elif current_station == "Stesicoro":
                    current_station_key_mp = "stesicoro"
                    current_station_text = "Il treno è appena partito da Stesicoro"
                elif current_station not in ["non ancora partito da Stesicoro", "Il treno è appena partito da Stesicoro"]:
                    for key, name in NOMBRE_MOSTRAR.items():
                        if name == current_station:
                            current_station_key_mp = key
                            break
                    current_station_text = current_station
                elif current_station == "Il treno è appena partito da Stesicoro":
                    current_station_key_mp = "stesicoro"
                    current_station_text = current_station
                else:
                    current_station_text = None
                if current_station_text:
                    if "appena partito" in current_station_text:
                        line += f"   [{current_station_text}]\n"
                    elif "non ancora partito" not in current_station_text:
                        line += f"   [il treno si trova attualmente a {current_station_text}]\n"
        msg2 += line
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            if mins2 > SHORT_TIME_THRESHOLD:
                msg2 += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
            else:
                msg2 += f"   Il successivo passerà tra {time_str2}.\n"
    else:
        msg2 += f"🔺 **Per Monte Po**: nessun treno in arrivo al momento.\n"

    msg3 = ""
    current_station_key_st = None
    tiempo_restante_st = None
    mins_st = 0
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        mins_st = mins
        time_str = format_time(mins, secs)
        tiempo_restante_st = mins*60 + secs
        if mins == 0 and secs < 30:
            line = f"🔻 **Per Stesicoro**: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**, alle {paso_mp.strftime('%H:%M')}.\n"
            else:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**.\n"
        rest_seconds = tiempo_restante_st
        total_seconds = get_total_seconds_from_montepo(estacion_key, now)
        if rest_seconds < total_seconds:
            seconds_passed = total_seconds - rest_seconds
            if seconds_passed < 0:
                seconds_passed = 0
            current_station = get_current_station_from_montepo(now, seconds_passed)
            if current_station == "Monte Po":
                current_station_key_st = "montepo"
                current_station_text = "Il treno è appena partito da Monte Po"
            elif current_station == "Stesicoro":
                current_station_key_st = "stesicoro"
                current_station_text = "Il treno è appena partito da Stesicoro"
            elif current_station not in ["non ancora partito da Monte Po", "Il treno è appena partito da Monte Po"]:
                for key, name in NOMBRE_MOSTRAR.items():
                    if name == current_station:
                        current_station_key_st = key
                        break
                current_station_text = current_station
            elif current_station == "Il treno è appena partito da Monte Po":
                current_station_key_st = "montepo"
                current_station_text = current_station
            else:
                current_station_text = None
        estaciones_localizacion2 = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni"]
        if estacion_key in estaciones_localizacion2 and 2 <= mins <= 10:
            if rest_seconds < total_seconds and current_station_text:
                if "appena partito" in current_station_text:
                    line += f"   [{current_station_text}]\n"
                elif "non ancora partito" not in current_station_text:
                    line += f"   [il treno si trova attualmente a {current_station_text}]\n"
        msg3 = line
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            if mins2 > SHORT_TIME_THRESHOLD:
                msg3 += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
            else:
                msg3 += f"   Il successivo passerà tra {time_str2}.\n"
    else:
        msg3 = f"🔻 **Per Stesicoro**: nessun treno in arrivo al momento.\n"
        tiempo_restante_st = 9999

    return msg2, msg3, current_station_key_mp, tiempo_restante_mp, current_station_key_st, tiempo_restante_st, mins_mp, mins_st

# ============================================================================
# FUNCIONES DE ENVÍO CON IMAGEN (modo normal)
# ============================================================================
async def send_treno_arrivo(update: Update, msg: str, direction: str):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown')

async def send_treno_arrivo_cabecera(update: Update, msg: str):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva_cabeceras.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown')

async def send_gif(update: Update, msg: str, gif_url: str):
    cache_buster = int(time_module.time())
    gif_url = f"{gif_url}?v={cache_buster}"
    try:
        return await update.message.reply_animation(animation=gif_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await send_default(update, msg)

async def send_default(update: Update, msg: str):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown')

# ============================================================================
# ENVÍO DE MENSAJE 2 (hacia Monte Po) y 3 (hacia Stesicoro) - modo normal
# ============================================================================
async def send_message_2(update: Update, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    if tiempo_restante is not None and (tiempo_restante <= 90 or mins <= 1):
        return await send_treno_arrivo(update, msg, "Monte Po")
    elif current_station_key and current_station_key != "montepo":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_stesicoro_{current_station_key}.gif"
        return await send_gif(update, msg, gif_url)
    else:
        return await send_default(update, msg)

async def send_message_3(update: Update, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str, reply_markup=None):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    if tiempo_restante is not None and (tiempo_restante <= 90 or mins <= 1):
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
        cache_buster = int(time_module.time())
        img_url = f"{img_url}?v={cache_buster}"
        try:
            return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception:
            return await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    elif current_station_key and current_station_key != "stesicoro":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.gif"
        cache_buster = int(time_module.time())
        gif_url = f"{gif_url}?v={cache_buster}"
        try:
            return await update.message.reply_animation(animation=gif_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception:
            return await send_default(update, msg)
    else:
        return await send_default(update, msg)

# ============================================================================
# FUNCIÓN AUXILIAR PARA DETECTAR SI UN MENSAJE ES "DEFAULT"
# ============================================================================
def is_default_message(current_station_key, tiempo_restante, mins):
    if tiempo_restante is not None and (tiempo_restante <= 90 or mins <= 1):
        return False
    if current_station_key:
        return False
    return True

# ============================================================================
# FUNCIÓN PRINCIPAL PARA ENVIAR AMBOS MENSAJES (intermedias)
# ============================================================================
async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False, show_button: bool = False):
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.5)
    
    if estacion_key not in ["montepo", "stesicoro"] and show_button:
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"aggiornare_{estacion_key}")]
        ])
        msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=keyboard_inline)
    else:
        msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=None)
    
    ids = []
    if msg2_obj:
        ids.append(msg2_obj.message_id)
    if msg3_obj:
        ids.append(msg3_obj.message_id)
    return tuple(ids) if ids else None

# ============================================================================
# BUCLE AUTO (30 segundos, 20 ciclos) - pour /auto
# ============================================================================
async def auto_update_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int):
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    if 'auto_msg_ids' in context.chat_data:
        for mid in context.chat_data['auto_msg_ids']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('auto_msg_ids', None)
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=False)
    if ids:
        context.chat_data['auto_msg_ids'] = list(ids)
    context.chat_data['auto_active'] = True
    context.chat_data['auto_cycles_left'] = 19
    for ciclo in range(19):
        await asyncio.sleep(30)
        if not context.chat_data.get('auto_active', False):
            break
        if 'auto_msg_ids' in context.chat_data:
            for mid in context.chat_data['auto_msg_ids']:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
        if simulated:
            now = now + timedelta(seconds=30)
        else:
            now = datetime.now(CATANIA_TZ)
        new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=False)
        if new_ids:
            context.chat_data['auto_msg_ids'] = list(new_ids)
        context.chat_data['auto_cycles_left'] -= 1
    context.chat_data['auto_active'] = False
    context.chat_data.pop('auto_msg_ids', None)
    context.chat_data.pop('auto_cycles_left', None)
    await update.message.reply_text("🔄 Aggiornamenti automatici terminati (20 cicli completati).")

# ============================================================================
# REFRESCO NORMAL (2 ciclos de 30 segundos, con botón en cada ciclo)
# ============================================================================
async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    for ciclo in range(2):
        await asyncio.sleep(30)
        if context.chat_data.get('cancel_refresh', False):
            break
        msg_ids = context.chat_data.get('refresh_msg_ids')
        if msg_ids:
            for mid in msg_ids:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
        if use_simulated and simulated_now:
            now = simulated_now
            if now.tzinfo is None:
                now = CATANIA_TZ.localize(now)
        else:
            now = datetime.now(CATANIA_TZ)
        new_ids = await send_messages_2_and_3(update, estacion_key, now, use_simulated, show_button=True)
        context.chat_data['refresh_msg_ids'] = new_ids if new_ids else None
    context.chat_data['refresh_active'] = False
    context.chat_data.pop('refresh_task', None)
    context.chat_data.pop('cancel_refresh', None)

# ============================================================================
# FUNCIÓN PARA REFRESCAR SOLO MENSAJES 2 y 3 (sin foto)
# ============================================================================
async def refresh_messages_only(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    chat_id = update.effective_chat.id
    msg_ids = context.chat_data.get('refresh_msg_ids')
    if msg_ids:
        for mid in msg_ids:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('refresh_msg_ids', None)
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=True)
    context.chat_data['refresh_msg_ids'] = new_ids if new_ids else None
    context.chat_data['refresh_active'] = True
    task = asyncio.create_task(auto_refresh_loop(update, context, estacion_key, chat_id, "", use_simulated=(simulated is not None), simulated_now=now if simulated else None))
    context.chat_data['refresh_task'] = task

# ============================================================================
# CALLBACK PARA EL BOTÓN INLINE "AGGIORNARE" (modo normal)
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[1]
    fake_update = type('Update', (), {'message': query.message, 'effective_chat': query.message.chat, 'callback_query': query})()
    await refresh_messages_only(fake_update, context, estacion_key)

# ============================================================================
# RESPUESTA PRINCIPAL (foto de estación + msg2/msg3 + aviso de cierre)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    context.chat_data['last_return_to_main'] = return_to_main
    
    if context.chat_data.get('auto_active', False):
        context.chat_data['auto_active'] = False
        if 'auto_task' in context.chat_data:
            task = context.chat_data['auto_task']
            if not task.done():
                task.cancel()
            context.chat_data.pop('auto_task', None)
        if 'auto_msg_ids' in context.chat_data:
            for mid in context.chat_data['auto_msg_ids']:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=mid)
                except Exception:
                    pass
            context.chat_data.pop('auto_msg_ids', None)
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    context.chat_data['cancel_refresh'] = False

    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    test_indicator = "🧪 [TEST MODE] " if simulated else ""

    # === CABECERAS: Monte Po o Stesicoro ===
    if estacion_key in ["montepo", "stesicoro"]:
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open, special_closing_msg = is_metro_closed(now, station)
        if closed:
            if next_open.date() > now.date():
                msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Riaprirà domani alle {next_open.strftime('%H:%M')}."
            else:
                mins_to_open = int((next_open - now).total_seconds() // 60)
                if mins_to_open <= 60:
                    first_train, _, _, has_first = get_next_departure(station, now)
                    if not has_first:
                        first_train, _, _, _ = get_next_departure(station, now + timedelta(days=1))
                    station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
                    msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
                else:
                    msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
            img = get_station_image(estacion_key, now)
            if img:
                await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            else:
                await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return

        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            close_h, close_m = get_closing_time(now, station)
            msg = f"🚇 Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
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
            msg = f"🚇 Il treno è in binario. Partirà tra **{time_str_rest}**."
            if mins_rest <= 1:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {format_time(min2, sec2)}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        else:
            time_str = format_time(minutes, seconds)
            if minutes < SHORT_TIME_THRESHOLD:
                msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**."
            else:
                msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**, alle {next_dep.strftime('%H:%M')}."
            if minutes <= 1:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {format_time(min2, sec2)}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."

        last_msg = get_last_train_message(now)
        if last_msg and not is_sant_agata(now):
            if "01:00" in last_msg:
                last_msg = last_msg.replace("📌", "🕐")
            elif "22:30" in last_msg:
                last_msg = last_msg.replace("📌", "🕙")
            msg += f"\n\n{last_msg}"

        total_seconds_rest = int(remaining.total_seconds())
        if total_seconds_rest <= 90 or mins_rest <= 1:
            await send_treno_arrivo_cabecera(update, msg)
        else:
            img = get_station_image(estacion_key, now)
            if img:
                await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
            else:
                await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
        return

    # ========================================================================
    # ESTACIONES INTERMEDIAS
    # ========================================================================
    closed, next_open, special_closing_msg = is_metro_closed(now, "Montepo")
    if closed:
        if next_open.date() > now.date():
            msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Riaprirà domani alle {next_open.strftime('%H:%M')}."
        else:
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure("Montepo", now)
                if not has_first:
                    first_train, _, _, _ = get_next_departure("Montepo", now + timedelta(days=1))
                msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento. Il primo treno da Monte Po partirà alle {first_train.strftime('%H:%M')}."
            else:
                msg = f"{special_closing_msg}\n🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
        img = get_station_image(estacion_key, now)
        if img:
            await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        else:
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    last_msg = get_last_train_message(now)
    last_msg_text = ""
    if last_msg and not is_sant_agata(now):
        if "01:00" in last_msg:
            last_msg = last_msg.replace("📌", "🕐")
        elif "22:30" in last_msg
