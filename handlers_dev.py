import asyncio
import time as time_module
import json
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

logger = logging.getLogger(__name__)

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
# BUS GRATUITO MONTE PO → MISTERBIANCO
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
            return f"🚌 **Autobus gratuito per Misterbianco** alle {hora_str}"
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

async def send_default(update: Update, msg: str, reply_markup=None):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

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
    
    # Caso especial: ningún tren en dirección Stesicoro
    if "nessun treno in arrivo al momento" in msg:
        msg = msg.replace("nessun treno in arrivo al momento", "Il servizio è terminato")
        return await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    
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
            return await send_default(update, msg, reply_markup=reply_markup)
    else:
        return await send_default(update, msg, reply_markup=reply_markup)

# ============================================================================
# FUNCIÓN PARA ENVIAR msg2 y msg3 (con botón retardado 1 segundo en intermedias)
# ============================================================================
async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False, show_button: bool = True):
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.1)
    
    # Enviar msg3 sin botón primero
    msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=None)
    
    ids = []
    if msg2_obj:
        ids.append(msg2_obj.message_id)
    if msg3_obj:
        ids.append(msg3_obj.message_id)
    
    # Para estaciones intermedias, añadir botón después de 1 segundo
    if estacion_key not in ["montepo", "stesicoro"] and show_button:
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"aggiornare_{estacion_key}")]
        ])
        
        async def add_button_later():
            await asyncio.sleep(1)
            try:
                await msg3_obj.edit_reply_markup(reply_markup=keyboard_inline)
            except Exception as e:
                print(f"Error al añadir botón: {e}")
        
        asyncio.create_task(add_button_later())
    
    return tuple(ids) if ids else None

# ============================================================================
# FUNCIÓN DE LIMPIEZA Y REINICIO AUTOMÁTICO (20 minutos, silencioso)
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
    
    welcome_id = context.chat_data.get('welcome_msg_id')
    for mid in msg_ids:
        if mid == welcome_id:
            continue
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    
    dev_mode = context.chat_data.get('dev_mode', False)
    welcome_id = context.chat_data.get('welcome_msg_id')
    context.chat_data.clear()
    if dev_mode:
        context.chat_data['dev_mode'] = True
    if welcome_id:
        context.chat_data['welcome_msg_id'] = welcome_id

def schedule_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'cleanup_task' in context.chat_data:
        try:
            context.chat_data['cleanup_task'].cancel()
        except Exception:
            pass
    task = asyncio.create_task(auto_clean_and_restart(update, context))
    context.chat_data['cleanup_task'] = task

# ============================================================================
# REFRESCAR SOLO MENSAJES 2 y 3 (sin foto)
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
# CALLBACK PARA EL BOTÓN "AGGIORNARE" (estaciones intermedias) - CON COOLDOWN
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    estacion_key = query.data.split("_")[1]
    
    # Cooldown de 2 segundos por estación
    cooldown_key = f"cooldown_{estacion_key}"
    last_update = context.chat_data.get(cooldown_key, 0)
    now = time_module.time()
    if now - last_update < 2:
        await query.answer()
        return
    
    context.chat_data[cooldown_key] = now
    await query.answer()
    
    fake_update = type('Update', (), {
        'message': query.message,
        'effective_chat': query.message.chat,
        'callback_query': query
    })()
    await refresh_messages_only(fake_update, context, estacion_key)

# ============================================================================
# CALLBACK PARA EL BOTÓN EN CABECERAS (Monte Po y Stesicoro)
# ============================================================================
async def aggiornare_cabecera_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[2]
    chat_id = query.message.chat_id
    
    # Elimina el mensaje principal viejo
    try:
        await query.message.delete()
    except Exception:
        pass
    
    # Regenera todo (incluirá el bus si está presente)
    await send_header_response(chat_id, context, estacion_key)
    
    schedule_cleanup(update, context)

# ============================================================================
# FUNCIÓN AUXILIAR PARA ENVIAR RESPUESTA DE CABECERA (Monte Po / Stesicoro)
# ============================================================================
async def send_header_response(chat_id, context, estacion_key):
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
    closed, next_open, special_closing_msg = is_metro_closed(now, station)
    
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{estacion_key}")]
    ])
    
    # Costruisci il messaggio principale
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
    
    # Aggiungi il messaggio del bus (solo per Monte Po) direttamente nel caption
    if estacion_key == "montepo":
        bus_text = get_bus_message_montepo_advanced(now)
        if bus_text:
            bus_text_clean = bus_text.replace("**", "")
            msg += f"\n\n{bus_text_clean}"
    
    # Ora invia il messaggio principale (foto + caption) con il bottone
    if not closed and has_trains:
        total_seconds_rest = int(remaining.total_seconds())
        mins_rest = int(remaining.total_seconds() // 60)
    else:
        total_seconds_rest = 0
        mins_rest = 0
    
    if not closed and has_trains and (total_seconds_rest <= 90 or mins_rest <= 1):
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva_cabeceras.png"
        cache_buster = int(time_module.time())
        img_url = f"{img_url}?v={cache_buster}"
        msg1 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown')
        await msg1.edit_reply_markup(reply_markup=keyboard_inline)
    else:
        img = get_station_image(estacion_key, now)
        if img:
            msg1 = await context.bot.send_photo(chat_id=chat_id, photo=img, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
        else:
            msg1 = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
    context.chat_data['main_msg_id'] = msg1.message_id

# ============================================================================
# RESPUESTA PRINCIPAL (foto + msg2/msg3)
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

    if estacion_key in ["montepo", "stesicoro"]:
        await send_header_response(update.message.chat_id, context, estacion_key)
        schedule_cleanup(update, context)
        return

    # ESTACIONES INTERMEDIAS
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
# COMANDOS Y WRAPPERS (modo normal)
# ============================================================================
async def cancel_refresh_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE, coro, *args, **kwargs):
    await coro(update, context, *args, **kwargs)

async def start_wrapper(update, context): await cancel_refresh_and_run(update, context, start)
async def help_command_wrapper(update, context): await cancel_refresh_and_run(update, context, help_command)
async def cmd_montepo_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_montepo)
async def cmd_stesicoro_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_stesicoro)
async def cmd_milo_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_milo)
async def cmd_fontana_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_fontana)
async def cmd_nesima_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_nesima)
async def cmd_sannullo_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_sannullo)
async def cmd_cibali_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_cibali)
async def cmd_borgo_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_borgo)
async def cmd_giuffrida_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_giuffrida)
async def cmd_italia_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_italia)
async def cmd_galatea_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_galatea)
async def cmd_giovanni_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_giovanni)
async def cmd_altri_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_altri)
async def handle_button_wrapper(update, context): await cancel_refresh_and_run(update, context, handle_button)
async def cmd_testgif_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_testgif)
async def test_command_wrapper(update, context): await cancel_refresh_and_run(update, context, test_command)
async def testfin_command_wrapper(update, context): await cancel_refresh_and_run(update, context, testfin_command)
async def auto_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_auto)
async def stop_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_stop)

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
    msg = await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Premi i pulsanti o scrive Accessibilità ♿ per aprire il modo accessibile per tutti.\n\n"
        f"{last_msg}",
        reply_markup=keyboard_main
    )
    context.chat_data['welcome_msg_id'] = msg.message_id

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
        "/stop - Ferma gli aggiornamenti automatici\n"
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/testfin - Disattiva modalità test\n"
        "Modalità accessibilità: /accessibilita\n\n"
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

# ============================================================================
# DETECCIÓN DE NOMBRE DE ESTACIÓN EN MODO NORMAL (SOLO GALATEA PARA PRUEBA)
# ============================================================================
async def normal_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Salir si estamos en modo accesibilidad
    if context.chat_data.get('accessibility_mode', False):
        return

    texto = update.message.text.strip()
    import unicodedata
    texto_norm = unicodedata.normalize('NFKD', texto.lower()).encode('ASCII', 'ignore').decode('ASCII')
    texto_limpio = ' '.join(texto_norm.split())

    # ========== ALIAS (sinónimos de estaciones) ==========
    ALIASES = {
        "misterbianco": "montepo",
        "humanitas": "nesima",
        "centro sicilia": "nesima",
        "centrosicilia": "nesima",
    }
    alias_norm = {}
    for alias, clave in ALIASES.items():
        alias_clean = unicodedata.normalize('NFKD', alias.lower()).encode('ASCII', 'ignore').decode('ASCII')
        alias_norm[alias_clean] = clave

    # Función de distancia Levenshtein
    def levenshtein_distance(a: str, b: str) -> int:
        if len(a) < len(b):
            return levenshtein_distance(b, a)
        if len(b) == 0:
            return len(a)
        previous_row = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            current_row = [i + 1]
            for j, cb in enumerate(b):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (ca != cb)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    # Lista para guardar (posición, clave)
    matches = []

    # 1. Coincidencia exacta de alias en el texto
    for alias, clave in alias_norm.items():
        if alias in texto_limpio:
            matches.append((texto_limpio.find(alias), clave))

    # 2. Coincidencia aproximada de alias: buscar palabra por palabra
    if not matches:
        palabras = texto_limpio.split()
        for alias, clave in alias_norm.items():
            for i, palabra in enumerate(palabras):
                dist = levenshtein_distance(palabra, alias)
                if dist <= 2:
                    # Calcular posición aproximada (suma de longitudes anteriores)
                    pos = sum(len(p) + 1 for p in palabras[:i])
                    matches.append((pos, clave))
                    break
            if matches:
                break

    # 3. Coincidencia exacta del nombre completo de la estación (subcadena)
    estaciones = list(NOMBRE_MOSTRAR.items())
    estaciones.sort(key=lambda x: len(x[1]), reverse=True)
    for clave, nombre in estaciones:
        nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
        start = 0
        while True:
            pos = texto_limpio.find(nombre_norm, start)
            if pos == -1:
                break
            matches.append((pos, clave))
            start = pos + 1

    # 4. Coincidencia aproximada de nombres de estación: buscar palabra por palabra
    if not matches:
        palabras = texto_limpio.split()
        for clave, nombre in estaciones:
            nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
            for i, palabra in enumerate(palabras):
                dist = levenshtein_distance(palabra, nombre_norm)
                if dist <= 2:
                    pos = sum(len(p) + 1 for p in palabras[:i])
                    matches.append((pos, clave))
                    break
            if matches:
                break

    # 5. Prefijos (ej. "monte" -> "Monte Po")
    if not matches:
        for clave, nombre in estaciones:
            nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
            if nombre_norm.startswith(texto_limpio) and len(texto_limpio) >= 3:
                matches.append((0, clave))
                break
            if texto_limpio.startswith(nombre_norm) and len(nombre_norm) >= 3:
                matches.append((0, clave))
                break

    # 6. Trucos secretos para Galatea
    if not matches:
        if texto_limpio.startswith("gal"):
            matches.append((0, "galatea"))
        elif "galaxia" in texto_limpio:
            matches.append((0, "galatea"))

    # 7. Excepción especial: "monte" a secas
    if not matches and texto_limpio == "monte":
        matches.append((0, "montepo"))

    if matches:
        matches.sort(key=lambda x: x[0])
        mejor_clave = matches[0][1]
        await send_station_response(update, context, mejor_clave, return_to_main=True)
        return

    # No reconocido
    await update.message.reply_text(
        "Stazione non riconosciuta. Le stazioni disponibili sono: " +
        ", ".join(NOMBRE_MOSTRAR.values()) + ".",
        reply_markup=keyboard_main
    )
