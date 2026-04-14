import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from horarios_logic import *
from horarios_logic import CATANIA_TZ

# ============================================================================
# TECLADOS NORMALES
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
# FUNCIÓN PARA ELIMINAR "[]"
# ============================================================================
def clean_text_for_display(text: str) -> str:
    if not text:
        return None
    text = text.replace("[]", "").replace("[ ]", "")
    text = ' '.join(text.split())
    if not text or text == "":
        return None
    return text

# ============================================================================
# BUS NESIMA → HUMANITAS
# ============================================================================
def get_bus_message_nesima(now: datetime) -> str:
    if now.weekday() == 6 or is_festivo_nazionale(now):
        return ""
    horarios = [("7:30", 7*60+30), ("8:30", 8*60+30), ("9:30", 9*60+30), ("10:30", 10*60+30),
                ("11:30", 11*60+30), ("12:30", 12*60+30), ("13:30", 13*60+30), ("14:30", 14*60+30),
                ("15:30", 15*60+30), ("16:30", 16*60+30), ("17:30", 17*60+30), ("18:30", 18*60+30),
                ("19:30", 19*60+30)]
    ahora_min = now.hour * 60 + now.minute
    for hora_str, hora_min in horarios:
        if hora_min > ahora_min and (hora_min - ahora_min) <= 30:
            return f"🚌 Prossimo autobus per Humanitas alle {hora_str}"
    return ""

# ============================================================================
# BUS GRATUITO MONTE PO → MISTERBIANCO (aviso 15 minutos antes)
# ============================================================================
def get_bus_message_montepo_advanced(now: datetime) -> str:
    if now.weekday() >= 5 or is_festivo_nazionale(now):
        return ""
    ahora_min = now.hour * 60 + now.minute
    manana = [("7:00", 7*60), ("7:15", 7*60+15), ("7:30", 7*60+30), ("7:45", 7*60+45),
              ("8:00", 8*60), ("8:15", 8*60+15), ("8:30", 8*60+30)]
    tarde = [("13:00", 13*60), ("13:15", 13*60+15), ("13:30", 13*60+30), ("13:45", 13*60+45),
             ("14:00", 14*60), ("14:15", 14*60+15), ("14:30", 14*60+30)]
    for hora_str, hora_min in manana + tarde:
        if hora_min > ahora_min and (hora_min - ahora_min) <= 15:
            return f"🚌 **Autobus gratuito per Misterbianco** alle {hora_str} (partenza da Monte Po)"
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
# FUNCIONES DE ENVÍO CON IMAGEN
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
# ENVÍO DE MENSAJE 2 y 3
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
# FUNCIÓN PARA ENVIAR msg2 y msg3 (con o sin botón) - para modo normal
# ============================================================================
async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False, show_button: bool = True):
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.1)
    
    if show_button:
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
# FUNCIÓN DE LIMPIEZA Y REINICIO AUTOMÁTICO (20 minutos)
# ============================================================================
async def auto_clean_and_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(20 * 60)
    chat_id = update.effective_chat.id
    
    msg_ids = []
    if 'main_msg_id' in context.chat_data:
        msg_ids.append(context.chat_data['main_msg_id'])
    if 'refresh_msg_ids' in context.chat_data:
        msg_ids.extend(context.chat_data['refresh_msg_ids'])
    if 'bus_msg_id' in context.chat_data:
        msg_ids.append(context.chat_data['bus_msg_id'])
    # Ya no guardamos mensajes de accesibilidad, así que no los borramos
    
    for mid in msg_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    
    context.chat_data.clear()
    
    from handlers_dev import start
    fake_update = type('Update', (), {
        'message': update.message,
        'effective_chat': update.effective_chat,
        'effective_user': update.effective_user
    })()
    await start(fake_update, context)

def schedule_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'cleanup_task' in context.chat_data:
        try:
            context.chat_data['cleanup_task'].cancel()
        except Exception:
            pass
    task = asyncio.create_task(auto_clean_and_restart(update, context))
    context.chat_data['cleanup_task'] = task

# ============================================================================
# REFRESCAR SOLO MENSAJES 2 y 3 (sin foto) - para modo normal
# ============================================================================
async def refresh_messages_only(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    chat_id = update.effective_chat.id
    
    old_ids = context.chat_data.get('refresh_msg_ids')
    if old_ids:
        for mid in old_ids:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('refresh_msg_ids', None)
    
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=True)
    if new_ids:
        context.chat_data['refresh_msg_ids'] = new_ids
    
    schedule_cleanup(update, context)

# ============================================================================
# CALLBACK PARA EL BOTÓN "AGGIORNARE" (estaciones intermedias) - modo normal
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[1]
    fake_update = type('Update', (), {
        'message': query.message,
        'effective_chat': query.message.chat,
        'callback_query': query
    })()
    await refresh_messages_only(fake_update, context, estacion_key)

# ============================================================================
# CALLBACK PARA EL BOTÓN EN CABECERAS (Monte Po y Stesicoro) - actualiza editando y mantiene el botón
# ============================================================================
async def aggiornare_cabecera_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[2]  # "agg_cabecera_montepo"
    
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
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
    else:
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            close_h, close_m = get_closing_time(now, station)
            msg = f"🚇 Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
        else:
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
    
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{estacion_key}")]
    ])
    
    if query.message.photo:
        await query.edit_message_caption(caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
    else:
        await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
    
    if estacion_key == "montepo":
        bus_text = get_bus_message_montepo_advanced(now)
        bus_msg_id = context.chat_data.get('bus_msg_id')
        if bus_text:
            if bus_msg_id:
                try:
                    await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=bus_msg_id, text=bus_text, parse_mode='Markdown')
                except Exception:
                    pass
            else:
                bus_msg = await query.message.reply_text(bus_text, parse_mode='Markdown')
                context.chat_data['bus_msg_id'] = bus_msg.message_id
        else:
            if bus_msg_id:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=bus_msg_id)
                except Exception:
                    pass
                context.chat_data.pop('bus_msg_id', None)
    
    schedule_cleanup(update, context)

# ============================================================================
# RESPUESTA PRINCIPAL (foto + msg2/msg3) - MODO NORMAL
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    context.chat_data['last_return_to_main'] = return_to_main
    
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
    test_indicator = "🧪 [TEST MODE] " if simulated else ""

    # === CABECERAS: Monte Po o Stesicoro ===
    if estacion_key in ["montepo", "stesicoro"]:
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open, special_closing_msg = is_metro_closed(now, station)
        
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{estacion_key}")]
        ])
        
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
                msg1 = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_inline)
            else:
                msg1 = await update.message.reply_text(msg, reply_markup=keyboard_inline)
            context.chat_data['main_msg_id'] = msg1.message_id
            
            if estacion_key == "montepo":
                bus_text = get_bus_message_montepo_advanced(now)
                if bus_text:
                    bus_msg = await update.message.reply_text(bus_text, parse_mode='Markdown')
                    context.chat_data['bus_msg_id'] = bus_msg.message_id
                else:
                    context.chat_data.pop('bus_msg_id', None)
            
            schedule_cleanup(update, context)
            return

        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            close_h, close_m = get_closing_time(now, station)
            msg = f"🚇 Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
            img = get_station_image(estacion_key, now)
            if img:
                msg1 = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_inline)
            else:
                msg1 = await update.message.reply_text(msg, reply_markup=keyboard_inline)
            context.chat_data['main_msg_id'] = msg1.message_id
            
            if estacion_key == "montepo":
                bus_text = get_bus_message_montepo_advanced(now)
                if bus_text:
                    bus_msg = await update.message.reply_text(bus_text, parse_mode='Markdown')
                    context.chat_data['bus_msg_id'] = bus_msg.message_id
                else:
                    context.chat_data.pop('bus_msg_id', None)
            
            schedule_cleanup(update, context)
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
            msg1 = await send_treno_arrivo_cabecera(update, msg)
            await msg1.edit_reply_markup(reply_markup=keyboard_inline)
        else:
            img = get_station_image(estacion_key, now)
            if img:
                msg1 = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_inline, parse_mode='Markdown')
            else:
                msg1 = await update.message.reply_text(msg, reply_markup=keyboard_inline, parse_mode='Markdown')
        context.chat_data['main_msg_id'] = msg1.message_id
        
        if estacion_key == "montepo":
            bus_text = get_bus_message_montepo_advanced(now)
            if bus_text:
                bus_msg = await update.message.reply_text(bus_text, parse_mode='Markdown')
                context.chat_data['bus_msg_id'] = bus_msg.message_id
            else:
                context.chat_data.pop('bus_msg_id', None)
        
        schedule_cleanup(update, context)
        return

    # ========================================================================
    # ESTACIONES INTERMEDIAS (modo normal, sin cambios)
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
            msg1 = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        else:
            msg1 = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        context.chat_data['main_msg_id'] = msg1.message_id
        schedule_cleanup(update, context)
        return

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    last_msg = get_last_train_message(now)
    last_msg_text = ""
    if last_msg and not is_sant_agata(now):
        if "01:00" in last_msg:
            last_msg = last_msg.replace("📌", "🕐")
        elif "22:30" in last_msg:
            last_msg = last_msg.replace("📌", "🕙")
        last_msg = clean_text_for_display(last_msg)
        if last_msg:
            last_msg_text = f"\n\n{last_msg}"
    
    permanent_caption = f"{test_indicator}🚇 Prossimi treni a {nombre}{last_msg_text}"
    permanent_caption = clean_text_for_display(permanent_caption)
    if not permanent_caption:
        permanent_caption = f"🚇 Prossimi treni a {nombre}"
    
    if estacion_key == "nesima":
        bus_msg = get_bus_message_nesima(now)
        if bus_msg:
            permanent_caption += f"\n\n{bus_msg}"
    
    img_station = get_station_image(estacion_key, now)

    if return_to_main:
        await update.message.reply_text("caricando informazione...", reply_markup=ReplyKeyboardRemove())
    
    if img_station:
        msg1 = await update.message.reply_photo(photo=img_station, caption=permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    else:
        msg1 = await update.message.reply_text(permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    context.chat_data['main_msg_id'] = msg1.message_id

    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=True)
    context.chat_data['refresh_msg_ids'] = ids if ids else None

    schedule_cleanup(update, context)

# ============================================================================
# ACCESIBILIDAD: MODO POR TEXTO (reconoce prefijos como "mon", "fon", "nes", etc.)
# ============================================================================

# Descripciones de estaciones (con "Percorso tattile")
DESCRIPCION_ESTACION = {
    "montepo": "Stazione capolinea con ascensore e servizi igienici.",
    "stesicoro": "Stazione centrale con ascensore e collegamento autobus.",
    "fontana": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Via Felice Fontana.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Felice Fontana e l'Ospedale Garibaldi-Nesima.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "nesima": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Lorenzo Bolano e Via Filippo Eredia.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trova l'uscita per: Viale Lorenzo Bolano.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "sannullo": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "cibali": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio, Angelo Massimino.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "milo": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bronte e Viale Fleming.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bronte e Viale Fleming.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "borgo": "La stazione è dotata di Percorso tattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Empedocle e Via Etnea.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: I treni della FCE, Via Signorelli e Via Caronda.",
    "giuffrida": "La stazione è dotata di Percorso tattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Guardia della Carvana e Piazza Abraham Lincoln.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Caronda e Via Vincenzo Giuffrida.",
    "italia": "La stazione è dotata di Percorso tattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Firenze, Via Ramondetta e Via Oliveto Scammacca.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Viale Vittorio Veneto e Corso Italia.",
    "galatea": "La stazione è dotata di Percorso tattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Jonio, Via Pasubio e via Palmanova.\nSul marciapiede 2 partono i treni in direzione Stesicoro.\nAlla testa del treno si trovano le uscite per: Piazza Galatea, Viale Africa e Via Messina.",
    "giovanni": "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Piazza Giovanni XXIII e Viale Africa.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Archimede, Viale della Libertà e Stazione di Trenitalia Catania Centrale.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
}

def clean_for_accessibility(text: str) -> str:
    """Elimina emojis, asteriscos, negritas."""
    if not text:
        return ""
    replacements = {
        "🔺": "", "🔻": "", "🚇": "", "🕐": "", "🕙": "", "📌": "",
        "**": "", "*": "", "__": "", "`": "", "🔹": "", "▪️": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = ' '.join(text.split())
    return text

def get_station_by_prefix(text: str) -> tuple:
    """
    Devuelve (clave_estacion, nombre_mostrar) si el texto comienza con un prefijo conocido,
    o si hay coincidencia aproximada.
    """
    text = text.lower().strip()
    # Simplificar tildes y caracteres especiales
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    
    # Prefijos únicos para cada estación (ordenados de más largo a más corto para evitar falsos positivos)
    prefijos = [
        ("monte", "montepo"), ("mon", "montepo"),
        ("fontana", "fontana"), ("font", "fontana"), ("fon", "fontana"),
        ("nesima", "nesima"), ("nes", "nesima"),
        ("san nullo", "sannullo"), ("san", "sannullo"), ("sann", "sannullo"),
        ("cibali", "cibali"), ("cib", "cibali"),
        ("milo", "milo"), ("mil", "milo"),
        ("borgo", "borgo"), ("bor", "borgo"),
        ("giuffrida", "giuffrida"), ("giu", "giuffrida"),
        ("italia", "italia"), ("ita", "italia"),
        ("galatea", "galatea"), ("gal", "galatea"),
        ("giovanni", "giovanni"), ("gio", "giovanni"), ("giov", "giovanni"),
        ("stesicoro", "stesicoro"), ("stes", "stesicoro"), ("ste", "stesicoro")
    ]
    
    for prefijo, clave in prefijos:
        if text.startswith(prefijo):
            return clave, NOMBRE_MOSTRAR.get(clave, clave.capitalize())
    
    # Si no hay prefijo, intentar coincidencia exacta (por si escribe el nombre completo)
    mapping = {
        "monte po": "montepo", "montepo": "montepo",
        "stesicoro": "stesicoro",
        "fontana": "fontana",
        "nesima": "nesima",
        "san nullo": "sannullo", "sannullo": "sannullo",
        "cibali": "cibali",
        "milo": "milo",
        "borgo": "borgo",
        "giuffrida": "giuffrida",
        "italia": "italia",
        "galatea": "galatea",
        "giovanni xxiii": "giovanni", "giovanni": "giovanni"
    }
    if text in mapping:
        clave = mapping[text]
        return clave, NOMBRE_MOSTRAR.get(clave, clave.capitalize())
    
    return None, None

async def acc_send_station_info(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    """Envía la información de una estación en modo accesibilidad (sin borrar mensajes anteriores)."""
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_for_accessibility(msg2) or "Nessun treno in arrivo verso Monte Po."
    msg3_clean = clean_for_accessibility(msg3) or "Nessun treno in arrivo verso Stesicoro."
    
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    descripcion = DESCRIPCION_ESTACION.get(estacion_key, "Stazione accessibile.")
    
    nombre_imagen = nombre.replace(" ", "").replace("XXIII", "XXIII")
    if nombre_imagen == "SanNullo":
        nombre_imagen = "SanNullo"
    elif nombre_imagen == "GiovanniXXIII":
        nombre_imagen = "GiovanniXXIII"
    img_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_a{nombre_imagen}.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    
    # Enviar todos los mensajes sin borrar nada
    await update.message.reply_photo(photo=img_url, caption=f"Stazione {nombre}", parse_mode=None)
    await update.message.reply_text(descripcion, parse_mode=None)
    await update.message.reply_text(f"Prossimi treni verso Monte Po:\n{msg2_clean}", parse_mode=None)
    await update.message.reply_text(f"Prossimi treni verso Stesicoro:\n{msg3_clean}", parse_mode=None)

async def acc_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto cuando el modo accesibilidad está activo."""
    if not context.chat_data.get('accessibility_mode', False):
        return
    
    text = update.message.text.strip()
    # Comprobar si el usuario quiere salir
    if text.lower() in ["/uscire", "uscire", "exit", "salir"]:
        await cmd_uscire(update, context)
        return
    
    # Buscar estación por prefijo o nombre
    estacion_key, nombre_estacion = get_station_by_prefix(text)
    if estacion_key:
        # Confirmar la elección antes de enviar la información
        await update.message.reply_text(f"Hai scelto {nombre_estacion}. Ecco le informazioni:")
        await acc_send_station_info(update, context, estacion_key)
    else:
        # No reconocido: recordar opciones
        await update.message.reply_text(
            "Stazione non riconosciuta. Le stazioni disponibili sono:\n"
            "Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro\n\n"
            "Puoi scrivere solo l'inizio del nome (es. 'mon', 'fon', 'nes', 'gio').\n"
            "Per uscire dalla modalità accessibilità, scrivi /uscire"
        )

async def cmd_accesibilidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo accesibilidad (entrada por texto con prefijos)."""
    context.chat_data['accessibility_mode'] = True
    await update.message.reply_text(
        "♿ Modalità accessibilità attivata.\n\n"
        "Puoi scrivere o dire in voce il nome della stazione o anche solo l'inizio:\n"
        "• 'mon' per Monte Po\n"
        "• 'fon' per Fontana\n"
        "• 'nes' per Nesima\n"
        "• 'san' per San Nullo\n"
        "• 'cib' per Cibali\n"
        "• 'mil' per Milo\n"
        "• 'bor' per Borgo\n"
        "• 'giu' per Giuffrida\n"
        "• 'ita' per Italia\n"
        "• 'gal' per Galatea\n"
        "• 'gio' per Giovanni XXIII\n"
        "• 'ste' per Stesicoro\n\n"
        "Esempio: scrivi 'mon' e ti mostrerò le informazioni di Monte Po.\n\n"
        "Per uscire, scrivi /uscire"
    )

async def cmd_uscire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el modo accesibilidad y vuelve al modo normal."""
    if context.chat_data.get('accessibility_mode', False):
        context.chat_data['accessibility_mode'] = False
        await update.message.reply_text(
            "✅ Modalità accessibilità disattivata. Sei tornato al menu principale.",
            reply_markup=keyboard_main
        )
    else:
        await update.message.reply_text("⚠️ Non sei in modalità accessibilità.")

# ============================================================================
# FUNCIONES DE COMANDOS (wrappers y comandos originales)
# ============================================================================
async def start_wrapper(update, context): await start(update, context)
async def help_command_wrapper(update, context): await help_command(update, context)
async def cmd_montepo_wrapper(update, context): await cmd_montepo(update, context)
async def cmd_stesicoro_wrapper(update, context): await cmd_stesicoro(update, context)
async def cmd_milo_wrapper(update, context): await cmd_milo(update, context)
async def cmd_fontana_wrapper(update, context): await cmd_fontana(update, context)
async def cmd_nesima_wrapper(update, context): await cmd_nesima(update, context)
async def cmd_sannullo_wrapper(update, context): await cmd_sannullo(update, context)
async def cmd_cibali_wrapper(update, context): await cmd_cibali(update, context)
async def cmd_borgo_wrapper(update, context): await cmd_borgo(update, context)
async def cmd_giuffrida_wrapper(update, context): await cmd_giuffrida(update, context)
async def cmd_italia_wrapper(update, context): await cmd_italia(update, context)
async def cmd_galatea_wrapper(update, context): await cmd_galatea(update, context)
async def cmd_giovanni_wrapper(update, context): await cmd_giovanni(update, context)
async def cmd_altri_wrapper(update, context): await cmd_altri(update, context)
async def handle_button_wrapper(update, context): await handle_button(update, context)
async def cmd_testgif_wrapper(update, context): await cmd_testgif(update, context)
async def test_command_wrapper(update, context): await test_command(update, context)
async def testfin_command_wrapper(update, context): await testfin_command(update, context)
async def auto_wrapper(update, context): await cmd_auto(update, context)
async def stop_wrapper(update, context): await cmd_stop(update, context)
# Wrappers accesibilidad
async def acc_wrapper(update, context): await cmd_accesibilidad(update, context)
async def acc_station_wrapper(update, context): pass  # Ya no se usan los comandos /a... pero los dejamos por compatibilidad

# Funciones originales (modo normal)
async def cmd_montepo(update, context):
    context.chat_data['last_station'] = "montepo"
    await send_station_response(update, context, "montepo", return_to_main=False)
async def cmd_stesicoro(update, context):
    context.chat_data['last_station'] = "stesicoro"
    await send_station_response(update, context, "stesicoro", return_to_main=False)
async def cmd_milo(update, context):
    context.chat_data['last_station'] = "milo"
    await send_station_response(update, context, "milo", return_to_main=False)
async def cmd_fontana(update, context):
    context.chat_data['last_station'] = "fontana"
    await send_station_response(update, context, "fontana", return_to_main=False)
async def cmd_nesima(update, context):
    context.chat_data['last_station'] = "nesima"
    await send_station_response(update, context, "nesima", return_to_main=False)
async def cmd_sannullo(update, context):
    context.chat_data['last_station'] = "sannullo"
    await send_station_response(update, context, "sannullo", return_to_main=False)
async def cmd_cibali(update, context):
    context.chat_data['last_station'] = "cibali"
    await send_station_response(update, context, "cibali", return_to_main=False)
async def cmd_borgo(update, context):
    context.chat_data['last_station'] = "borgo"
    await send_station_response(update, context, "borgo", return_to_main=False)
async def cmd_giuffrida(update, context):
    context.chat_data['last_station'] = "giuffrida"
    await send_station_response(update, context, "giuffrida", return_to_main=False)
async def cmd_italia(update, context):
    context.chat_data['last_station'] = "italia"
    await send_station_response(update, context, "italia", return_to_main=False)
async def cmd_galatea(update, context):
    context.chat_data['last_station'] = "galatea"
    await send_station_response(update, context, "galatea", return_to_main=False)
async def cmd_giovanni(update, context):
    context.chat_data['last_station'] = "giovanni"
    await send_station_response(update, context, "giovanni", return_to_main=False)
async def cmd_altri(update, context):
    await update.message.reply_text("⬇️ Altre stazioni:", reply_markup=keyboard_altri)

async def start(update, context):
    user = update.effective_user
    now = datetime.now(CATANIA_TZ)
    last_msg = get_last_train_message(now)
    if "01:00" in last_msg:
        last_msg = last_msg.replace("📌", "🕐")
    elif "22:30" in last_msg:
        last_msg = last_msg.replace("📌", "🕙")
    await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Quando arriva la metropolitana di Catania?\n"
        "Premi o usa i comandi /accessibilita ♿ per aprire il modo accessibile per tutti.\n\n"
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
        "/auto - Avvia aggiornamenti ogni 30 secondi (20 cicli)\n"
        "/stop - Ferma gli aggiornamenti automatici\n"
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/test DDMMYYYY HHMM X - Test con 3 cicli (M, S, ML)\n"
        "/testfin - Disattiva modalità test\n"
        "/testgif - Invia GIF di prova e lo cancella dopo 1 minuto\n\n"
        "Modalità accessibilità: /accessibilita (scrivi il nome della stazione)\n\n"
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
        est_key = BOTON_TO_KEY[text]
        context.chat_data['last_station'] = est_key
        await send_station_response(update, context, est_key, return_to_main=True)
    else:
        await update.message.reply_text("Scelta non valida. Usa i pulsanti.", reply_markup=keyboard_main)

async def cmd_testgif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_stesicoro_fontana.gif"
    text_msg = (
        "🚆 Prossimi treni a Nesima\n\n"
        "🔺 Per Monte Po: Passa tra 3 minuti.\n"
        "   [il treno si trova attualmente a Monte Po]"
    )
    await update.message.reply_text(text_msg)
    gif_message = await update.message.reply_animation(animation=gif_url)
    await asyncio.sleep(60)
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=gif_message.message_id)
    except Exception as e:
        print(f"Error al borrar el GIF: {e}")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🧪 **Modalità test**\n\n"
            "Per fissare una data/ora simulata e usare tutti i bottoni:\n"
            "`/test DDMMYYYY HHMM`\n"
            "Esempio: `/test 11022026 1102`\n\n"
            "Per tornare alla realtà: `/testfin`\n\n"
            "Per una simulazione con aggiornamenti automatici (3 cicli):\n"
            "`/test DDMMYYYY HHMM stazione` (M, S, ML)\n"
            "Esempio: `/test 09042026 0815 ML`",
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
            simulated = datetime(year, month, day, hour, minute)
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        simulated = CATANIA_TZ.localize(simulated)
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
        if len(date_str) != 8 or not date_str.isdigit():
            await update.message.reply_text("Data non valida. Usa DDMMYYYY.")
            return
        if len(time_str) != 4 or not time_str.isdigit():
            await update.message.reply_text("Ora non valida. Usa HHMM.")
            return
        day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
        hour, minute = int(time_str[0:2]), int(time_str[2:4])
        if hour > 23 or minute > 59:
            await update.message.reply_text("Ora non valida.")
            return
        try:
            simulated = datetime(year, month, day, hour, minute)
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        simulated = CATANIA_TZ.localize(simulated)
        context.chat_data['test_time'] = simulated
        context.chat_data['last_station'] = station
        await send_station_response(update, context, station, return_to_main=False)
        return
    await update.message.reply_text("Comando non riconosciuto. Usa /test DDMMYYYY HHMM o /test DDMMYYYY HHMM X")

async def testfin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data and 'test_time' in context.chat_data:
        del context.chat_data['test_time']
        await update.message.reply_text("✅ Modalità test disattivata. Ora reale ripristinata.")
    else:
        await update.message.reply_text("⚠️ Nessuna modalità test attiva.")

async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ L'auto-refresh è stato disattivato. Usa il pulsante 'Aggiornare' per aggiornare manualmente i dati.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ L'auto-refresh non è più attivo. Non c'è nulla da fermare.")
