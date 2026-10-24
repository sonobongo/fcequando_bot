import asyncio
import time as time_module
import unicodedata
import logging
import re
import requests
from bs4 import BeautifulSoup
import os
import pytz
from datetime import datetime, timedelta, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from horarios_logic import *
import handlers_bus as bus_handlers
from horarios_logic import CATANIA_TZ, get_extension_message, get_shuttle_stops, get_next_shuttle_departure

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
        ["Giovanni XXIII", "Bus", "← Menu"],
    ],
    resize_keyboard=True, one_time_keyboard=False
)

def get_keyboard_altri(now=None):
    return keyboard_altri

def get_keyboard_bus(now=None):
    """Botonera Bus: Metro Shuttle visibile solo lun-ven / dom notte."""
    show_shuttle = False
    if now is not None:
        wd = now.weekday()
        time_mins = now.hour * 60 + now.minute
        if 0 <= wd <= 3:
            show_shuttle = True
        elif wd == 4:
            show_shuttle = time_mins < 22 * 60 + 30
        elif wd == 6:
            show_shuttle = time_mins >= 22 * 60 + 30
    bus_lines = ["BRT-1", "BRT-5", "109", "Humanitas", "Motta"]
    if show_shuttle:
        bus_lines.insert(0, "Metro Shuttle")
    rows = [[bus_lines[i], bus_lines[i+1]] if i+1 < len(bus_lines) else [bus_lines[i]] for i in range(0, len(bus_lines), 2)]
    rows.append(["← Menu"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)

keyboard_bus = get_keyboard_bus()

BOTON_TO_KEY = {
    "Monte Po": "montepo", "Stesicoro": "stesicoro", "Fontana": "fontana",
    "Nesima": "nesima", "San Nullo": "sannullo", "Cibali": "cibali",
    "Milo": "milo", "Borgo": "borgo", "Giuffrida": "giuffrida",
    "Italia": "italia", "Galatea": "galatea", "Giovanni XXIII": "giovanni",
    "Metro Shuttle": "shuttle"
}

# ============================================================================
# FUNCIÓN PARA OBTENER LA HORA SIMULADA (test estático o live)
# ============================================================================
def get_simulated_now(context: ContextTypes.DEFAULT_TYPE) -> datetime:
    if 'test_time' in context.chat_data:
        sim = context.chat_data['test_time']
        if sim.tzinfo is None:
            sim = CATANIA_TZ.localize(sim)
        return sim
    if 'test_live_base' in context.chat_data:
        base = context.chat_data['test_live_base']
        base_real = context.chat_data.get('test_live_real')
        if base_real is None:
            base_real = datetime.now(CATANIA_TZ)
            context.chat_data['test_live_real'] = base_real
        if base.tzinfo is None:
            base = CATANIA_TZ.localize(base)
        delta = datetime.now(CATANIA_TZ) - base_real
        return base + delta
    return datetime.now(CATANIA_TZ)

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
# FUNCIÓN PARA ALMACENAR IDS
# ============================================================================
async def store_id(context, message):
    if message and hasattr(message, 'message_id'):
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        if message.message_id not in context.chat_data['all_msg_ids']:
            context.chat_data['all_msg_ids'].append(message.message_id)

# ============================================================================
# DETENER ACTUALIZACIÓN AUTOMÁTICA DE SUPER
# ============================================================================
def stop_super_update(context):
    if 'super_task' in context.chat_data:
        context.chat_data['super_active'] = False
        try:
            context.chat_data['super_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('super_task', None)

def stop_shuttle_update(context):
    if 'shuttle_task' in context.chat_data:
        context.chat_data['shuttle_active'] = False
        try:
            context.chat_data['shuttle_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('shuttle_task', None)

# ============================================================================
# BUS FONTANA → HUMANITAS
# ============================================================================
def get_bus_message_fontana(now: datetime) -> str:
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
            return f"🚌 **Navetta gratuita Comune Misterbianco** alle {hora_str}"
    return ""

# ============================================================================
# CONSTRUCCIÓN DE MENSAJES TEMPORALES (msg2 y msg3) con soporte para modo dev
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str, dev_mode: bool = False):
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
        if dev_mode:
            time_str = format_time_precise(mins, secs)
        else:
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
        if estacion_key in estaciones_localizacion and 1 <= mins <= 10 and (mins*60 + secs) > 104:
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
        if (mins*60 + secs) <= 104 and next_info:
            paso2, mins2, secs2 = next_info
            if dev_mode:
                time_str2 = format_time_precise(mins2, secs2)
            else:
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
        if dev_mode:
            time_str = format_time_precise(mins, secs)
        else:
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
        if estacion_key in estaciones_localizacion2 and 1 <= mins <= 10 and (mins*60 + secs) > 104:
            if rest_seconds < total_seconds and current_station_text:
                if "appena partito" in current_station_text:
                    line += f"   [{current_station_text}]\n"
                elif "non ancora partito" not in current_station_text:
                    line += f"   [il treno si trova attualmente a {current_station_text}]\n"
        msg3 = line
        if (mins*60 + secs) <= 104 and next_info:
            paso2, mins2, secs2 = next_info
            if dev_mode:
                time_str2 = format_time_precise(mins2, secs2)
            else:
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
# FUNCIONES DE ENVÍO
# ============================================================================
async def send_treno_arrivo(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, direction: str):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        result = await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        result = await update.message.reply_text(msg, parse_mode='Markdown')
    await store_id(context, result)
    return result

async def send_treno_arrivo_cabecera(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva_cabeceras.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        result = await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        result = await update.message.reply_text(msg, parse_mode='Markdown')
    await store_id(context, result)
    return result

async def send_gif(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, gif_url: str):
    cache_buster = int(time_module.time())
    gif_url = f"{gif_url}?v={cache_buster}"
    try:
        result = await update.message.reply_animation(animation=gif_url, caption=msg, parse_mode='Markdown')
    except Exception:
        result = await send_default(update, context, msg)
    await store_id(context, result)
    return result

async def send_default(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, reply_markup=None):
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        result = await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception:
        result = await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    await store_id(context, result)
    return result

async def send_text_only(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, reply_markup=None):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    result = await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    await store_id(context, result)
    return result

# ============================================================================
# ENVÍO DE MENSAJE 2 y 3
# ============================================================================
async def send_message_2(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    if tiempo_restante is not None and (tiempo_restante <= 104):
        return await send_treno_arrivo(update, context, msg, "Monte Po")
    elif current_station_key and current_station_key != "montepo":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_stesicoro_{current_station_key}.gif"
        return await send_gif(update, context, msg, gif_url)
    else:
        return await send_default(update, context, msg)

async def send_message_3(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str, reply_markup=None):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    if "nessun treno in arrivo al momento" in msg:
        msg = msg.replace("nessun treno in arrivo al momento", "Il servizio è terminato")
        return await send_text_only(update, context, msg, reply_markup)
    if tiempo_restante is not None and (tiempo_restante <= 104):
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
        cache_buster = int(time_module.time())
        img_url = f"{img_url}?v={cache_buster}"
        try:
            result = await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception:
            result = await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
        await store_id(context, result)
        return result
    elif current_station_key and current_station_key != "stesicoro":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.gif"
        cache_buster = int(time_module.time())
        gif_url = f"{gif_url}?v={cache_buster}"
        try:
            result = await update.message.reply_animation(animation=gif_url, caption=msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception:
            result = await send_default(update, context, msg, reply_markup)
        await store_id(context, result)
        return result
    else:
        return await send_default(update, context, msg, reply_markup)

# ============================================================================
# FUNCIÓN PARA ENVIAR msg2 y msg3 (con botón retardado)
# ============================================================================
async def send_messages_2_and_3(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, now: datetime, simulated: bool = False, show_button: bool = True):
    dev_mode = context.chat_data.get('dev_mode', False)
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key, dev_mode)
    
    msg2_obj = await send_message_2(update, context, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.1)
    
    msg3_obj = await send_message_3(update, context, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=None)
    
    ids = []
    if msg2_obj:
        ids.append(msg2_obj.message_id)
    if msg3_obj:
        ids.append(msg3_obj.message_id)
    
    if ids:
        if 'refresh_msg_ids' not in context.chat_data:
            context.chat_data['refresh_msg_ids'] = []
        context.chat_data['refresh_msg_ids'].extend(ids)
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].extend(ids)
    
    if estacion_key not in ["montepo", "stesicoro"] and show_button:
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"aggiornare_{estacion_key}")]
        ])
        async def add_button_later():
            await asyncio.sleep(1)
            try:
                await msg3_obj.edit_reply_markup(reply_markup=keyboard_inline)
            except Exception:
                pass
        asyncio.create_task(add_button_later())
    
    return tuple(ids) if ids else None

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
    
    now = get_simulated_now(context)
    
    new_ids = await send_messages_2_and_3(update, context, estacion_key, now, simulated=(context.chat_data.get('test_time') is not None or context.chat_data.get('test_live_base') is not None), show_button=True)
    if new_ids:
        context.chat_data['refresh_msg_ids'] = list(new_ids)

# ============================================================================
# CALLBACK PARA EL BOTÓN "AGGIORNARE"
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    estacion_key = query.data.split("_")[1]
    
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
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    await send_header_response(chat_id, context, estacion_key, is_update=True)

# ============================================================================
# AUTO-UPDATE CABECERA: actualiza cada 10s cuando queda < 60s, sin botón
# ============================================================================
async def _cabecera_countdown(context, chat_id, message_id, next_dep, station, dest, dev_mode, estacion_key):
    """Edita el caption cada 10s mientras queden < 60s para la salida. Sin botón hasta el final."""
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{estacion_key}")]
    ])
    while True:
        await asyncio.sleep(10)
        if not context.chat_data.get('cabecera_countdown_active', False):
            return
        now = get_simulated_now(context)
        remaining_secs = (next_dep - now).total_seconds()
        if remaining_secs <= 0:
            try:
                await context.bot.edit_message_caption(
                    chat_id=chat_id, message_id=message_id,
                    caption=f"🚇 Il treno per {dest} è partito.",
                    parse_mode='Markdown', reply_markup=keyboard_inline
                )
            except Exception:
                pass
            context.chat_data['cabecera_countdown_active'] = False
            return
        mins_r = int(remaining_secs // 60)
        secs_r = int(remaining_secs % 60)
        time_str = format_time_precise(mins_r, secs_r) if dev_mode else format_time(mins_r, secs_r)
        msg = f"Il treno è in binario. Partirà tra **{time_str}**."
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption=msg, parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error en _cabecera_countdown: {e}")
            break
    context.chat_data['cabecera_countdown_active'] = False

# ============================================================================
# FUNCIÓN AUXILIAR PARA ENVIAR RESPUESTA DE CABECERA (con soporte para modo dev y extensión)
# ============================================================================
async def send_header_response(chat_id, context, estacion_key, is_update=False):
    try:
        now = get_simulated_now(context)
        dev_mode = context.chat_data.get('dev_mode', False)
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open, special_closing_msg = is_metro_closed(now, station)
        
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{estacion_key}")]
        ])
        
        if not is_update:
            img_station = get_station_image(estacion_key, now)
            caption_station = f"🚇 {NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())}"
            if img_station:
                msg1 = await context.bot.send_photo(chat_id=chat_id, photo=img_station, caption=caption_station, parse_mode='Markdown')
            else:
                msg1 = await context.bot.send_message(chat_id=chat_id, text=caption_station, parse_mode='Markdown')
            context.chat_data['main_msg_id'] = msg1.message_id
            await store_id(context, msg1)
        
        if is_sant_agata(now):
            msg = get_sant_agata_message(station, now)
            img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
            await store_id(context, msg2)
            return

        extension_msg = get_extension_message(now)
        
        if (now.month == 12 and now.day == 31 and now.hour >= 12) or (now.month == 1 and now.day == 1 and now.hour < 3):
            msg = "🎉 Orario speciale di Capodanno: il servizio termina alle 03:00. Buon anno! 🎉"
            if extension_msg:
                msg = extension_msg + msg
            img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
            await store_id(context, msg2)
            return
        
        if (now.month == 1 and now.day == 1 and 1 <= now.hour < 3) or (now.month == 2 and now.day in [4,5,6] and 1 <= now.hour < 2):
            msg = "🚇 Il metro è aperto fino alle 03:00. Nessun altro treno in programma."
            if extension_msg:
                msg = extension_msg + msg
            img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
            await store_id(context, msg2)
            return
        
        if closed:
            station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
            if next_open.date() > now.date():
                reopen_str = f"domani alle {next_open.strftime('%H:%M')}"
            else:
                reopen_str = f"alle {next_open.strftime('%H:%M')}"
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure(station, now)
                if not has_first:
                    tomorrow = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(0, 0)))
                    first_train, _, _, has_first = get_next_departure(station, tomorrow)
                if has_first and first_train:
                    msg = f"🚇 La metropolitana è chiusa. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
                else:
                    msg = f"🚇 La metropolitana è chiusa. Riaprirà {reopen_str}."
            else:
                msg = f"🚇 La metropolitana è chiusa. Riaprirà {reopen_str}."
            if extension_msg:
                msg = extension_msg + msg
            img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
            await store_id(context, msg2)
            return
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            close_h, close_m = get_closing_time(now, station)
            msg = f"🚇 Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
            if extension_msg:
                msg = extension_msg + msg
            img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.b
