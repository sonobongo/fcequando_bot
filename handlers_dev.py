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
    rows = [["BRT-1"], ["Humanitas"], ["Motta"], ["← Menu"]]
    if show_shuttle:
        rows.insert(0, ["Metro Shuttle"])
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
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=keyboard_inline)
            await store_id(context, msg2)
            return
        
        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        remaining = next_dep - now
        mins_rest = int(remaining.total_seconds() // 60)
        secs_rest = int(remaining.total_seconds() % 60)
        total_seconds_rest = int(remaining.total_seconds())
        
        if dev_mode:
            time_str_rest = format_time_precise(mins_rest, secs_rest)
            time_str = format_time_precise(minutes, seconds)
        else:
            time_str_rest = format_time(mins_rest, secs_rest)
            time_str = format_time(minutes, seconds)
        
        if mins_rest <= 4:
            msg = f"Il treno è in binario. Partirà tra **{time_str_rest}**."
        else:
            if minutes < SHORT_TIME_THRESHOLD:
                msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**."
            else:
                msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**, alle {next_dep.strftime('%H:%M')}."
        
        if mins_rest <= 1:
            next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
            if has2:
                if dev_mode:
                    next_time_str = format_time_precise(min2, sec2)
                else:
                    next_time_str = format_time(min2, sec2)
                msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {next_time_str}, alle {next2.strftime('%H:%M')}."
            else:
                msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        
        last_msg = get_last_train_message(now, station)
        if last_msg and not is_sant_agata(now):
            if "01:00" in last_msg:
                last_msg = last_msg.replace("📌", "🕐")
            elif "22:30" in last_msg:
                last_msg = last_msg.replace("📌", "🕙")
            msg += f"\n\n{last_msg}"
        
        if extension_msg and extension_msg not in msg:
            msg = extension_msg + msg
        
        if estacion_key == "montepo":
            bus_text = get_bus_message_montepo_advanced(now)
            if bus_text:
                bus_text_clean = bus_text.replace("**", "")
                msg += f"\n\n{bus_text_clean}"
        
        img_url = None
        if mins_rest <= 4:
            if total_seconds_rest <= 90:
                img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva_cabeceras.png"
            else:
                if estacion_key == "montepo":
                    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_binario_montepo.jpg"
                else:
                    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_binario_stesicoro.jpg"
        
        use_countdown = total_seconds_rest < 60
        send_keyboard = keyboard_inline if not use_countdown else None

        if img_url:
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg2 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=msg, parse_mode='Markdown', reply_markup=send_keyboard)
        else:
            msg2 = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', reply_markup=send_keyboard)
        await store_id(context, msg2)

        if use_countdown:
            if 'cabecera_countdown_task' in context.chat_data:
                try:
                    context.chat_data['cabecera_countdown_task'].cancel()
                except Exception:
                    pass
            context.chat_data['cabecera_countdown_active'] = True
            task = asyncio.create_task(
                _cabecera_countdown(context, chat_id, msg2.message_id, next_dep, station, dest, dev_mode, estacion_key)
            )
            context.chat_data['cabecera_countdown_task'] = task
    
    except Exception as e:
        logger.error(f"Error en send_header_response: {e}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Errore nel recupero informazioni: {str(e)}", reply_markup=keyboard_inline)
        except:
            pass

# ============================================================================
# RESPUESTA PRINCIPAL (foto + msg2/msg3)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    stop_super_update(context)
    stop_shuttle_update(context)
    context.chat_data['last_return_to_main'] = return_to_main
    now = get_simulated_now(context)
    demo_mode = context.chat_data.get('demo_mode', False)

    test_indicator = ""
    if (context.chat_data.get('test_time') is not None or context.chat_data.get('test_live_base') is not None) and not demo_mode:
        test_indicator = "🧪 [TEST MODE] "

    if estacion_key in ["montepo", "stesicoro"]:
        await send_header_response(update.message.chat_id, context, estacion_key, is_update=False)
        return

    if is_sant_agata(now):
        nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
        msg_agata = get_sant_agata_message("Montepo", now)
        img_station = get_station_image(estacion_key, now)
        if img_station:
            msg1 = await update.message.reply_photo(photo=img_station, caption=f"🚇 {nombre}\n\n{msg_agata}", parse_mode='Markdown', reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
        else:
            msg1 = await update.message.reply_text(f"🚇 {nombre}\n\n{msg_agata}", parse_mode='Markdown', reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
        context.chat_data['main_msg_id'] = msg1.message_id
        await store_id(context, msg1)
        return

    closed, next_open, special_closing_msg = is_metro_closed(now, "Montepo")
    if closed:
        if next_open.date() > now.date():
            reopen_str = f"domani alle {next_open.strftime('%H:%M')}"
        else:
            reopen_str = f"alle {next_open.strftime('%H:%M')}"
        mins_to_open = int((next_open - now).total_seconds() // 60)
        if mins_to_open <= 60:
            try:
                first_train, _, _, has_first = get_next_departure("Montepo", now)
                if not has_first:
                    tomorrow = CATANIA_TZ.localize(datetime.combine(now.date() + timedelta(days=1), time(0, 0)))
                    first_train, _, _, has_first = get_next_departure("Montepo", tomorrow)
                if has_first and first_train:
                    msg = f"🚇 La metropolitana è chiusa. Il primo treno da Monte Po partirà alle {first_train.strftime('%H:%M')}."
                else:
                    msg = f"🚇 La metropolitana è chiusa. Riaprirà {reopen_str}."
            except Exception:
                msg = f"🚇 La metropolitana è chiusa. Riaprirà {reopen_str}."
        else:
            msg = f"🚇 La metropolitana è chiusa. Riaprirà {reopen_str}."
        try:
            img = get_station_image(estacion_key, now)
            if img:
                msg1 = await update.message.reply_photo(photo=img, caption=msg, parse_mode='Markdown', reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
            else:
                msg1 = await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
            context.chat_data['main_msg_id'] = msg1.message_id
            await store_id(context, msg1)
        except Exception as e:
            logger.error(f"Error enviando mensaje de metro cerrado: {e}")
            try:
                msg1 = await update.message.reply_text(msg, reply_markup=keyboard_main)
                context.chat_data['main_msg_id'] = msg1.message_id
            except Exception:
                pass
        return

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    last_msg = get_last_train_message(now, "Montepo")
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
    
    if img_station:
        msg1 = await update.message.reply_photo(photo=img_station, caption=permanent_caption, reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
    else:
        msg1 = await update.message.reply_text(permanent_caption, reply_markup=keyboard_main if return_to_main else get_keyboard_altri(now))
    context.chat_data['main_msg_id'] = msg1.message_id
    await store_id(context, msg1)

    ids = await send_messages_2_and_3(update, context, estacion_key, now, simulated=(context.chat_data.get('test_time') is not None or context.chat_data.get('test_live_base') is not None), show_button=True)
    if ids:
        context.chat_data['refresh_msg_ids'] = list(ids)

# ============================================================================
# COMANDOS Y WRAPPERS
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
async def news_command_wrapper(update, context): await cancel_refresh_and_run(update, context, news_command)

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
    await update.message.reply_text("⬇️ Altre stazioni:", reply_markup=get_keyboard_altri(get_simulated_now(context)))

async def start(update, context):
    user = update.effective_user
    now = datetime.now(CATANIA_TZ)
    last_msg = get_last_train_message(now, "Montepo")
    msg = await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Premi i pulsanti o scrive il nome della stazione che desideri controllare. Puoi accedere alla modalità Accessibile ♿, scrivendo Accessibilità.\n\n"
        f"{last_msg}",
        reply_markup=keyboard_main
    )
    context.chat_data['welcome_msg_id'] = msg.message_id
    await store_id(context, msg)

async def help_command(update, context):
    msg = await update.message.reply_text(
        "Comandi disponibili:\n"
        "/start - Messaggio di benvenuto\n"
        "/help - Questo aiuto\n"
        "/montepo - Prossimi treni a Monte Po\n"
        "/stesicoro - Prossimi treni a Stesicoro\n"
        "/milo - Prossimi treni a Milo\n"
        "/altri - Mostra altre stazioni\n"
        "/fontana, /nesima, /sannullo, /cibali, /borgo, /giuffrida, /italia, /galatea, /giovanni\n"
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/testfin - Disattiva modalità test\n"
        "/news - Ultima notizia dalla FCE\n"
        "/about - Info sul bot\n"
        "/grazie - Info sul bot\n"
        "super - Mostra treni in arrivo in ≤59 secondi\n"
        "Shuttle - Orari del Metro Shuttle (bus)\n"
        "Oppure premi i pulsanti.",
        reply_markup=keyboard_main
    )
    await store_id(context, msg)

async def handle_button(update, context):
    stop_super_update(context)
    stop_shuttle_update(context)
    
    text = update.message.text
    if text == "Altri":
        await cmd_altri(update, context)
    elif text == "← Menu":
        await update.message.reply_text("🔙 Ritorno al menu principale.", reply_markup=keyboard_main)
    elif text == "Bus":
        now = get_simulated_now(context)
        await update.message.reply_text("🚌 Servizi Bus:", reply_markup=get_keyboard_bus(now))
    elif text == "Metro Shuttle":
        await send_shuttle_response(update, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="​", reply_markup=keyboard_main, disable_notification=True)
    elif text == "BRT-1":
        await bus_handlers.send_brt1_response(update, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="​", reply_markup=keyboard_main, disable_notification=True)
    elif text == "Humanitas":
        await bus_handlers.send_humanitas_response(update, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="​", reply_markup=keyboard_main, disable_notification=True)
    elif text == "Motta":
        await bus_handlers.send_motta_response(update, context)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="​", reply_markup=keyboard_main, disable_notification=True)
    elif text in BOTON_TO_KEY:
        est_key = BOTON_TO_KEY[text]
        context.chat_data['last_station'] = est_key
        await send_station_response(update, context, est_key, return_to_main=True)
    else:
        await update.message.reply_text("Scelta non valida. Usa i pulsanti.", reply_markup=keyboard_main)

# ============================================================================
# MODO TEST
# ============================================================================
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_super_update(context)
    stop_shuttle_update(context)
    
    args = context.args
    if not args:
        msg = await update.message.reply_text(
            "🧪 **Modalità test**\n\n"
            "Per fissare una data/ora simulata:\n"
            "`/test DDMMYYYY HHMM`\n"
            "Esempio: `/test 11022026 1102`\n\n"
            "Per tornare alla realtà: `/testfin`\n\n"
            "In modalità test, puoi avanzare/retrocedere di secondi (es. +10s, -30s) o minuti (es. +5m, -2m).",
            parse_mode='Markdown'
        )
        await store_id(context, msg)
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
        context.chat_data.pop('demo_mode', None)
        msg = await update.message.reply_text(
            f"🧪 **Modalità test attivata**\nOra simulata: {simulated.strftime('%d/%m/%Y %H:%M')}\nUsa i bottoni. Per uscire: `/testfin`\nPer avanzare/retrocedere scrivi +10s, -30s, +5m, -2m, ecc.",
            parse_mode='Markdown'
        )
        await store_id(context, msg)
        return
    await update.message.reply_text("Comando non riconosciuto. Usa /test DDMMYYYY HHMM")

async def testfin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_super_update(context)
    stop_shuttle_update(context)
    
    if context.chat_data and 'test_time' in context.chat_data:
        del context.chat_data['test_time']
        context.chat_data.pop('demo_mode', None)
        await update.message.reply_text("✅ Modalità test/demo disattivata. Ora reale ripristinata.")
    else:
        await update.message.reply_text("⚠️ Nessuna modalità test/demo attiva.")

# ============================================================================
# NEWSLETTER DIARIA DE LA FCE
# ============================================================================
LAST_NEWS_FILE = "last_news_url.txt"
NEWS_CHAT_ID = os.environ.get("NEWS_CHAT_ID")

def get_latest_news():
    url = "https://www.circumetnea.it/category/news/"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; FCEBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.find('article')
        if not article:
            article = soup.find('a', href=lambda h: h and '/news/' in h)
        
        if article:
            title_tag = article.find(['h2', 'h3', 'h4']) or article
            title = title_tag.get_text(strip=True)
            
            link = article.get('href')
            if not link and article.name == 'article':
                link = article.find('a').get('href')
            
            if title and link:
                if link.startswith('/'):
                    link = 'https://www.circumetnea.it' + link
                return title, link
    except Exception as e:
        logger.error(f"Error al obtener noticias: {e}")
    
    return None, None

async def enviar_noticia_diaria(context: ContextTypes.DEFAULT_TYPE):
    if not NEWS_CHAT_ID:
        logger.warning("NEWS_CHAT_ID no definido. No se enviará la newsletter.")
        return
    
    titulo, url = get_latest_news()
    if not titulo or not url:
        logger.info("No se pudo obtener la noticia de hoy.")
        return
    
    last_url = ""
    if os.path.exists(LAST_NEWS_FILE):
        with open(LAST_NEWS_FILE, 'r') as f:
            last_url = f.read().strip()
    
    if url == last_url:
        logger.info("La noticia más reciente ya fue enviada.")
        return
    
    mensaje = f"📰 <b>{titulo}</b>\n\n<a href='{url}'>Leggi la notizia completa</a>"
    try:
        await context.bot.send_message(
            chat_id=NEWS_CHAT_ID,
            text=mensaje,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
        with open(LAST_NEWS_FILE, 'w') as f:
            f.write(url)
        logger.info(f"Noticia enviada: {titulo}")
    except Exception as e:
        logger.error(f"Error al enviar la noticia: {e}")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    titulo, url = get_latest_news()
    if not titulo or not url:
        await update.message.reply_text("❌ No se pudo obtener la noticia.")
        return
    
    mensaje = f"📰 <b>{titulo}</b>\n\n<a href='{url}'>Leggi la notizia completa</a>"
    await update.message.reply_text(mensaje, parse_mode='HTML', disable_web_page_preview=False)

# ============================================================================
# METRO SHUTTLE
# ============================================================================
def get_shuttle_status(now: datetime) -> str:
    from horarios_logic import SHUTTLE_SCHEDULES
    stops = get_shuttle_stops()
    if not stops:
        return "🚌 Servizio Shuttle non disponibile."
    if now.weekday() >= 5:
        return "🚌 Il Metro Shuttle è attivo solo dal lunedì al venerdì."

    # Assicurarsi che now sia in timezone locale (Europe/Rome)
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    else:
        now = now.astimezone(CATANIA_TZ)
    current_time = now.time()

    # Per ogni fermata: orario schedulato precedente e prossimo
    stop_data = []
    for stop in stops:
        schedule = SHUTTLE_SCHEDULES.get(stop, {}).get('weekday', [])
        prev_t = None
        next_t = None
        for t in schedule:
            if t <= current_time:
                prev_t = t
            else:
                next_t = t
                break
        if next_t:
            dep_dt = CATANIA_TZ.localize(datetime.combine(now.date(), next_t))
            secs_to_next = (dep_dt - now).total_seconds()
        else:
            secs_to_next = None
        if prev_t:
            prev_dt = CATANIA_TZ.localize(datetime.combine(now.date(), prev_t))
            secs_since_prev = (now - prev_dt).total_seconds()
        else:
            secs_since_prev = None
        stop_data.append((stop, next_t, secs_to_next, prev_t, secs_since_prev))

    # Trovare fermate dove il bus è appena passato (≤30s fa)
    appena_passato = set()
    for i, (stop, next_t, secs_to_next, prev_t, secs_since_prev) in enumerate(stop_data):
        if secs_since_prev is not None and 0 < secs_since_prev <= 30:
            appena_passato.add(i)

    # Parpadeo: alterna 🔻 y ⬇️ ogni secondo
    bus_icon = "🔻" if now.second % 2 == 0 else "⬇️"

    from datetime import datetime as _dt

    # Trovare TUTTI i tratti dove ci sono bus attivi (più veicoli contemporaneamente).
    # Per ogni tratto i→i+1, cercare una corsa j tale che:
    #   sched_i[j] <= now < sched_i1[j]
    # Se secs_to_i1 <= 30: il triangolo va sulla fermata i+1 (arrivo imminente).
    # Se secs_to_i1 > 30: il triangolo va nel tratto.

    bus_tratti = set()    # tratti con bus in transito
    bus_fermate = set()   # fermate con bus in arrivo (≤30s)

    for i in range(len(stop_data) - 1):
        sched_i  = SHUTTLE_SCHEDULES.get(stop_data[i][0],   {}).get('weekday', [])
        sched_i1 = SHUTTLE_SCHEDULES.get(stop_data[i+1][0], {}).get('weekday', [])
        for j in range(min(len(sched_i), len(sched_i1))):
            if sched_i[j] <= current_time < sched_i1[j]:
                dt_i1 = CATANIA_TZ.localize(_dt.combine(now.date(), sched_i1[j]))
                secs = (dt_i1 - now).total_seconds()
                if secs <= 30:
                    bus_fermate.add(i + 1)
                else:
                    bus_tratti.add(i)

    # Se nessun bus trovato (tra corse): mostrare al primo tratto
    if not bus_tratti and not bus_fermate:
        sched_0 = SHUTTLE_SCHEDULES.get(stop_data[0][0], {}).get('weekday', [])
        for t in sched_0:
            if t > current_time:
                bus_tratti.add(0)
                break
        if not bus_tratti:
            bus_tratti.add(len(stop_data) - 2)

    lines = ["🚌 **Metro Shuttle – Monitoraggio in tempo reale**\n"]
    N = len(stop_data)

    for i, (stop, next_t, secs_to_next, prev_t, secs_since_prev) in enumerate(stop_data):
        # --- Riga della fermata ---
        if i in bus_fermate:
            s = max(0, int(secs_to_next)) if secs_to_next is not None else 0
            tag = f"{bus_icon} {s//60:02d}:{s%60:02d}"
            lines.append(f"⚪️ **{stop}**  {tag}")
        elif i in appena_passato:
            lines.append(f"⚪️ **{stop}**  _Appena passato_")
        elif next_t is not None:
            lines.append(f"⚪️ {stop}  {next_t.strftime('%H:%M')}")
        else:
            lines.append(f"⚪️ {stop}  —")

        # --- Tratto: triangolo solo nei tratti con bus ---
        if i < N - 1:
            if i in bus_tratti:
                lines.append(f"▫️  {bus_icon}")
            else:
                lines.append("▫️")

    return "\n".join(lines)

async def auto_update_shuttle(context, chat_id, message_id, cycles=40, interval=3):
    last_sent_msg = None
    for ciclo in range(1, cycles + 1):
        for _ in range(interval):
            await asyncio.sleep(1)
            if not context.chat_data.get('shuttle_active', False):
                return
        if not context.chat_data.get('shuttle_active', False):
            return
        now = get_simulated_now(context)
        new_msg = get_shuttle_status(now)
        if new_msg != last_sent_msg:
            try:
                await context.bot.edit_message_text(
                    text=new_msg, chat_id=chat_id,
                    message_id=message_id, parse_mode='Markdown'
                )
                last_sent_msg = new_msg
            except Exception as e:
                logger.error(f"Errore aggiornamento shuttle: {e}")
                break
    if context.chat_data.get('shuttle_active', False):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_shuttle")
        ]])
        try:
            await context.bot.edit_message_text(
                text=new_msg, chat_id=chat_id,
                message_id=message_id, parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception:
            pass
        context.chat_data['shuttle_active'] = False
        context.chat_data.pop('shuttle_task', None)

async def aggiornare_shuttle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stop_shuttle_update(context)
    now = get_simulated_now(context)
    msg = get_shuttle_status(now)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    context.chat_data['shuttle_active'] = True
    task = asyncio.create_task(auto_update_shuttle(context, chat_id, message_id))
    context.chat_data['shuttle_task'] = task
    try:
        await context.bot.edit_message_text(
            text=msg, chat_id=chat_id,
            message_id=message_id, parse_mode='Markdown'
        )
    except Exception:
        pass

async def send_shuttle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_shuttle_update(context)
    now = get_simulated_now(context)
    msg = get_shuttle_status(now)
    result = await update.message.reply_text(msg, parse_mode='Markdown')
    message_id = result.message_id
    chat_id = update.effective_chat.id
    context.chat_data['shuttle_active'] = True
    task = asyncio.create_task(auto_update_shuttle(context, chat_id, message_id))
    context.chat_data['shuttle_task'] = task

# ============================================================================
# FUNCIONES PARA "SUPER" - Tracking de posición de trenes en tiempo real
# ============================================================================

def _build_train_positions(now: datetime):
    from horarios_logic import (
        get_schedule_list, get_total_seconds_from_montepo,
        get_total_seconds_from_stesicoro, is_metro_closed, CATANIA_TZ
    )

    STATIONS = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo",
                "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    N = len(STATIONS)

    t_fwd = [get_total_seconds_from_montepo(st, now) for st in STATIONS]
    t_fwd[0] = 0

    rev_route = list(reversed(range(N)))
    rev_times = [get_total_seconds_from_stesicoro(STATIONS[i], now) for i in rev_route]
    rev_times[0] = 0

    forward_trains = []
    reverse_trains = []

    closed_mp, _, _ = is_metro_closed(now, "Montepo")
    if not closed_mp:
        total_fwd = t_fwd[N - 1]
        for salida_t in get_schedule_list("Montepo", now):
            dep_dt = CATANIA_TZ.localize(datetime.combine(now.date(), salida_t))
            elapsed = (now - dep_dt).total_seconds()
            if elapsed < 0:
                continue
            if elapsed > total_fwd + 120:
                continue

            pos_type = segment_idx = station_idx = secs_remaining = None

            for i in range(N - 1):
                if t_fwd[i] <= elapsed < t_fwd[i + 1]:
                    secs_to_next = t_fwd[i + 1] - elapsed
                    if secs_to_next <= 59:
                        pos_type, station_idx, secs_remaining = 'arriving', i + 1, int(secs_to_next)
                    else:
                        pos_type, segment_idx, secs_remaining = 'between', i, int(secs_to_next)
                    break

            if pos_type is None and elapsed >= t_fwd[N - 1]:
                pos_type, station_idx, secs_remaining = 'arriving', N - 1, 0

            if pos_type:
                forward_trains.append({
                    'pos_type': pos_type,
                    'segment_idx': segment_idx,
                    'station_idx': station_idx,
                    'secs_remaining': secs_remaining,
                    'elapsed': elapsed,
                    'dep_dt': dep_dt,
                })

    closed_st, _, _ = is_metro_closed(now, "Stesicoro")
    if not closed_st:
        total_rev = rev_times[N - 1]
        for salida_t in get_schedule_list("Stesicoro", now):
            dep_dt = CATANIA_TZ.localize(datetime.combine(now.date(), salida_t))
            elapsed = (now - dep_dt).total_seconds()
            if elapsed < 0:
                continue
            if elapsed > total_rev + 120:
                continue

            pos_type = segment_idx = station_idx = secs_remaining = None

            for k in range(N - 1):
                if rev_times[k] <= elapsed < rev_times[k + 1]:
                    secs_to_next = rev_times[k + 1] - elapsed
                    next_sta_idx = rev_route[k + 1]
                    if secs_to_next <= 59:
                        pos_type = 'arriving'
                        station_idx = next_sta_idx
                        secs_remaining = int(secs_to_next)
                    else:
                        pos_type = 'between'
                        segment_idx = min(rev_route[k], rev_route[k + 1])
                        secs_remaining = int(secs_to_next)
                    break

            if pos_type is None and elapsed >= total_rev:
                pos_type, station_idx, secs_remaining = 'arriving', 0, 0

            if pos_type:
                reverse_trains.append({
                    'pos_type': pos_type,
                    'segment_idx': segment_idx,
                    'station_idx': station_idx,
                    'secs_remaining': secs_remaining,
                    'elapsed': elapsed,
                    'dep_dt': dep_dt,
                })

    return forward_trains, reverse_trains, t_fwd, rev_times, rev_route


def _get_train_position_idx(train):
    if train['pos_type'] == 'arriving':
        return float(train['station_idx'])
    else:
        return float(train['segment_idx']) + 0.5


def _filter_trains_min_separation(trains, min_gap_stations=3):
    if not trains:
        return trains
    sorted_t = sorted(trains, key=_get_train_position_idx)
    filtered = []
    for t in sorted_t:
        pos_t = _get_train_position_idx(t)
        too_close = any(
            abs(pos_t - _get_train_position_idx(f)) < min_gap_stations
            for f in filtered
        )
        if not too_close:
            filtered.append(t)
    return filtered


async def get_super_status(now: datetime) -> str:
    from horarios_logic import get_schedule_list, is_metro_closed, CATANIA_TZ

    STATIONS = ["montepo", "fontana", "nesima", "sannullo", "cibali", "milo",
                "borgo", "giuffrida", "italia", "galatea", "giovanni", "stesicoro"]
    N = len(STATIONS)

    forward_trains, reverse_trains, t_fwd, rev_times, rev_route = _build_train_positions(now)

    forward_trains = _filter_trains_min_separation(forward_trains, min_gap_stations=3)
    reverse_trains = _filter_trains_min_separation(reverse_trains, min_gap_stations=3)

    mp_label = None
    closed_mp, _, _ = is_metro_closed(now, "Montepo")
    if not closed_mp:
        for salida_t in get_schedule_list("Montepo", now):
            dep_dt = CATANIA_TZ.localize(datetime.combine(now.date(), salida_t))
            secs_to_dep = (dep_dt - now).total_seconds()
            if secs_to_dep > 0:
                if secs_to_dep <= 59:
                    mp_label = f"🔻 {int(secs_to_dep)//60:02d}:{int(secs_to_dep)%60:02d}"
                elif secs_to_dep <= 240:
                    mp_label = "🔻 In Binario"
                break

    st_label = None
    closed_st, _, _ = is_metro_closed(now, "Stesicoro")
    if not closed_st:
        for salida_t in get_schedule_list("Stesicoro", now):
            dep_dt = CATANIA_TZ.localize(datetime.combine(now.date(), salida_t))
            secs_to_dep = (dep_dt - now).total_seconds()
            if secs_to_dep > 0:
                if secs_to_dep <= 59:
                    st_label = f"🔺 {int(secs_to_dep)//60:02d}:{int(secs_to_dep)%60:02d}"
                elif secs_to_dep <= 240:
                    st_label = "🔺 In Binario"
                break

    fwd_at_station = {}
    fwd_at_segment = set()
    for tr in forward_trains:
        if tr['pos_type'] == 'arriving':
            idx = tr['station_idx']
            if idx not in fwd_at_station or tr['secs_remaining'] < fwd_at_station[idx]:
                fwd_at_station[idx] = tr['secs_remaining']
        else:
            fwd_at_segment.add(tr['segment_idx'])

    rev_at_station = {}
    rev_at_segment = set()
    for tr in reverse_trains:
        if tr['pos_type'] == 'arriving':
            idx = tr['station_idx']
            if idx not in rev_at_station or tr['secs_remaining'] < rev_at_station[idx]:
                rev_at_station[idx] = tr['secs_remaining']
        else:
            rev_at_segment.add(tr['segment_idx'])

    lines = []
    for i, estacion in enumerate(STATIONS):
        nombre = NOMBRE_MOSTRAR.get(estacion, estacion.capitalize())
        tags = []

        if estacion == "montepo":
            if i in rev_at_station:
                s = rev_at_station[i]
                tags.append("🔺 In Binario" if s == 0 else f"🔺 {s//60:02d}:{s%60:02d}")
            if mp_label:
                tags.append(mp_label)

        elif estacion == "stesicoro":
            if i in fwd_at_station:
                s = fwd_at_station[i]
                tags.append("🔻 In Binario" if s == 0 else f"🔻 {s//60:02d}:{s%60:02d}")
            if st_label:
                tags.append(st_label)

        else:
            if i in fwd_at_station:
                s = fwd_at_station[i]
                tags.append(f"🔻 {s//60:02d}:{s%60:02d}")
            if i in rev_at_station:
                s = rev_at_station[i]
                tags.append(f"🔺 {s//60:02d}:{s%60:02d}")

        if tags:
            lines.append(f"⚪️ {nombre}  {'  '.join(tags)}")
        else:
            lines.append(f"⚪️ {nombre}")

        if i < N - 1:
            seg_tags = []
            if i in fwd_at_segment:
                seg_tags.append("🔻")
            if i in rev_at_segment:
                seg_tags.append("🔺")
            if seg_tags:
                lines.append(f"▫️  {'  '.join(seg_tags)}")
            else:
                lines.append("▫️")

    return "🛂 **SUPERVISORE: Monitoraggio degli arrivi dei treni**\n\n" + "\n".join(lines)

async def auto_update_super(context, chat_id, message_id, cycles=40, interval=3):
    last_sent_msg = None
    for ciclo in range(1, cycles + 1):
        for _ in range(interval):
            await asyncio.sleep(1)
            if not context.chat_data.get('super_active', False):
                return
        if not context.chat_data.get('super_active', False):
            return
        now = get_simulated_now(context)
        new_msg = await get_super_status(now)
        has_numbers = any(c.isdigit() for c in new_msg.split("SUPERVISORE")[-1])
        msg_changed = new_msg != last_sent_msg
        if msg_changed and (has_numbers or last_sent_msg is None):
            try:
                await context.bot.edit_message_text(text=new_msg, chat_id=chat_id, message_id=message_id, parse_mode='Markdown')
                last_sent_msg = new_msg
            except Exception as e:
                logger.error(f"Error al actualizar super: {e}")
                break
    if context.chat_data.get('super_active', False):
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_super")]])
        try:
            await context.bot.edit_message_text(text=new_msg, chat_id=chat_id, message_id=message_id, parse_mode='Markdown', reply_markup=keyboard)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=new_msg, parse_mode='Markdown', reply_markup=keyboard)
        context.chat_data['super_active'] = False
        context.chat_data.pop('super_task', None)

async def send_super_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'super_task' in context.chat_data:
        context.chat_data['super_active'] = False
        try:
            context.chat_data['super_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('super_task', None)
    
    now = get_simulated_now(context)
    msg = await get_super_status(now)
    result = await update.message.reply_text(msg, parse_mode='Markdown')
    message_id = result.message_id
    chat_id = update.effective_chat.id
    context.chat_data['super_msg_id'] = message_id
    context.chat_data['super_chat_id'] = chat_id
    context.chat_data['super_active'] = True
    task = asyncio.create_task(auto_update_super(context, chat_id, message_id, cycles=40, interval=3))
    context.chat_data['super_task'] = task

async def ritornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ricarica la stazione da zero come nuova richiesta."""
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[1]
    fake_update = type("Update", (), {
        "message": query.message,
        "effective_chat": query.message.chat,
        "callback_query": query
    })()
    await send_station_response(fake_update, context, estacion_key, return_to_main=True)

async def aggiornare_super_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if 'super_task' in context.chat_data:
        context.chat_data['super_active'] = False
        try:
            context.chat_data['super_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('super_task', None)
    message = query.message
    chat_id = message.chat_id
    message_id = message.message_id
    now = get_simulated_now(context)
    new_msg = await get_super_status(now)
    try:
        await query.edit_message_text(text=new_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error al editar super: {e}")
        new_result = await message.reply_text(new_msg, parse_mode='Markdown')
        message_id = new_result.message_id
        try:
            await message.delete()
        except:
            pass
    context.chat_data['super_msg_id'] = message_id
    context.chat_data['super_chat_id'] = chat_id
    context.chat_data['super_active'] = True
    task = asyncio.create_task(auto_update_super(context, chat_id, message_id, cycles=40, interval=3))
    context.chat_data['super_task'] = task

# ============================================================================
# MODO NONNA: DETECCIÓN DE NOMBRE DE ESTACIÓN CON ERRORES TIPOGRÁFICOS Y ALIAS
# ============================================================================
async def normal_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stop_super_update(context)
    stop_shuttle_update(context)
    
    texto = update.message.text.strip()
    
    # ========== RESPUESTA A PREGUNTAS SOBRE LA HORA DE CIERRE ==========
    texto_lower = texto.lower()
    if any(frase in texto_lower for frase in [
        "chiude", "chiusura", "ultimo treno", "ultima corsa",
        "fino a che ora", "fino a quando", "orario chiusura",
        "quando chiude", "a che ora chiude", "ultimi treni",
        "ultimo treno oggi", "ultima corsa oggi"
    ]):
        now = get_simulated_now(context)
        mp_schedule = get_schedule_list("Montepo", now)
        st_schedule = get_schedule_list("Stesicoro", now)

        last_mp = mp_schedule[-1]
        last_st = st_schedule[-1]

        msg = (
            f"🚇 **Ultime partenze di oggi**\n"
            f"▪️ Da Monte Po verso Stesicoro: **{last_mp.strftime('%H:%M')}**\n"
            f"▪️ Da Stesicoro verso Monte Po: **{last_st.strftime('%H:%M')}**"
        )
        extension_msg = get_extension_message(now)
        if extension_msg:
            msg = extension_msg.rstrip() + "\n\n" + msg
        await update.message.reply_text(msg, parse_mode='Markdown')
        return
    
    # ========== RESPUESTA A "shuttle" (palabra exacta) ==========
    if texto_lower in ("shuttle", "metro shuttle"):
        await send_shuttle_response(update, context)
        return
    if texto_lower in ("brt1", "brt-1", "brt 1"):
        await bus_handlers.send_brt1_response(update, context)
        return
    if texto_lower == "humanitas":
        await bus_handlers.send_humanitas_response(update, context)
        return
    if texto_lower == "motta":
        await bus_handlers.send_motta_response(update, context)
        return
    if texto_lower == "bus":
        now = get_simulated_now(context)
        await update.message.reply_text("🚌 Servizi Bus:", reply_markup=get_keyboard_bus(now))
        return
    
    # ========== RESPUESTA A PALABRAS CLAVE (about, grazie) ==========
    texto_lower = texto.lower()
    texto_normalized = re.sub(r'^/', '', texto_lower)
    texto_normalized = re.sub(r'\.$', '', texto_normalized)
    if texto_normalized in ["about", "grazie"]:
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/FOTOMASTER.jpg"
        caption = "Chatbot sviluppato con grande impegno da Àlex Naranjo. Se ti piace, condividilo con i tuoi amici e familiari. https://t.me/FCEQuando_bot"
        try:
            result = await update.message.reply_photo(photo=img_url, caption=caption, parse_mode='Markdown')
        except Exception:
            result = await update.message.reply_text(caption, parse_mode='Markdown')
        await store_id(context, result)
        return
    
    # ========== RESPUESTA A "super" (solo palabra exacta) ==========
    if re.match(r'^(/?)super[.!?]*$', texto_normalized):
        await send_super_response(update, context)
        return
    
    # ========== AVANCE/RETROCESO DE TIEMPO EN MODO TEST (+/- segundos o minutos) ==========
    if 'test_time' in context.chat_data:
        match = re.match(r'^([+-])(\d+)([sm]?)$', texto_normalized)
        if match:
            signo = match.group(1)
            cantidad = int(match.group(2))
            unidad = match.group(3) if match.group(3) else 'm'
            if unidad == 's':
                delta = timedelta(seconds=cantidad)
            else:
                delta = timedelta(minutes=cantidad)
            if signo == '-':
                delta = -delta
            simulated = context.chat_data['test_time']
            if simulated.tzinfo is None:
                simulated = CATANIA_TZ.localize(simulated)
            nueva_simulacion = simulated + delta
            context.chat_data['test_time'] = nueva_simulacion
            last_station = context.chat_data.get('last_station')
            if last_station:
                await send_station_response(update, context, last_station, return_to_main=False)
            else:
                await update.message.reply_text(f"⏩ Modifica di {cantidad}{unidad}. Nuovo orario simulato: {nueva_simulacion.strftime('%d/%m/%Y %H:%M:%S')}")
            return
    
    if 'test_time' in context.chat_data and texto_normalized.startswith('+'):
        try:
            minutos = int(texto_normalized[1:])
            if 1 <= minutos <= 99:
                simulated = context.chat_data['test_time']
                if simulated.tzinfo is None:
                    simulated = CATANIA_TZ.localize(simulated)
                nueva_simulacion = simulated + timedelta(minutes=minutos)
                context.chat_data['test_time'] = nueva_simulacion
                last_station = context.chat_data.get('last_station')
                if last_station:
                    await send_station_response(update, context, last_station, return_to_main=False)
                else:
                    await update.message.reply_text(f"⏩ Avanzati {minutos} minuti. Nuovo orario simulato: {nueva_simulacion.strftime('%d/%m/%Y %H:%M')}")
                return
            else:
                await update.message.reply_text("Puoi avanzare da 1 a 99 minuti. Esempio: +5")
                return
        except ValueError:
            pass
    
    import unicodedata
    texto_norm = unicodedata.normalize('NFKD', texto.lower()).encode('ASCII', 'ignore').decode('ASCII')
    texto_limpio_orig = ' '.join(texto_norm.split())

    # Estrarre ora PRIMA del matching per non confondere Levenshtein
    hora_schedule = None
    hora_match_pre = re.search(r'\b(\d{1,2})(?:[:\.]?(\d{2}))?\b', texto_limpio_orig)
    if hora_match_pre:
        hora_int_pre = int(hora_match_pre.group(1))
        if 0 <= hora_int_pre <= 23:
            hora_schedule = hora_int_pre

    # Rilevazione anticipata stazioni terminali + ora (prima del Levenshtein)
    if hora_schedule is not None:
        texto_sin_num = re.sub(r'\b\d{1,4}\b', '', texto_limpio_orig).strip()
        texto_sin_num = ' '.join(texto_sin_num.split())
        TERMINAL_ALIASES = {
            "montepo": ["montepo","monte po","monte","misterbianco","monterosso"],
            "stesicoro": ["stesicoro","stesi","stesic"],
        }
        for t_key, aliases in TERMINAL_ALIASES.items():
            if any(texto_sin_num == a or texto_sin_num.startswith(a) for a in aliases):
                now = get_simulated_now(context)
                nombre_est = NOMBRE_MOSTRAR[t_key]
                hora_int = hora_schedule
                TERMINAL_DIR = {"montepo": ("1️⃣", "🔻", "Stesicoro"), "stesicoro": ("2️⃣", "🔺", "Monte Po")}
                num_emoji, arrow, dest_name = TERMINAL_DIR[t_key]
                target_date = now.date()
                giorno_str = "oggi"
                hora_fine = CATANIA_TZ.localize(datetime.combine(now.date(), time(hora_int, 59)))
                if hora_fine < now:
                    target_date = now.date() + timedelta(days=1)
                    giorno_str = "domani"
                sched_key = "Montepo" if t_key == "montepo" else "Stesicoro"
                schedule_list = get_schedule_list(sched_key, CATANIA_TZ.localize(datetime.combine(target_date, time(12, 0))))
                pasos = []
                for salida in schedule_list:
                    paso_dt = CATANIA_TZ.localize(datetime.combine(target_date, salida))
                    if paso_dt.hour == hora_int:
                        if giorno_str == "oggi" and paso_dt <= now:
                            continue
                        pasos.append(paso_dt)
                img_url = get_station_image(t_key, now)
                caption1 = f"🕐 **Partenze programmate a {nombre_est} {giorno_str} alle {hora_int:02d}:00**"
                if img_url:
                    msg1 = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_url, caption=caption1, parse_mode="Markdown")
                else:
                    msg1 = await update.message.reply_text(caption1, parse_mode="Markdown")
                await store_id(context, msg1)
                if pasos:
                    lineas = [f"{num_emoji} {p.strftime('%H:%M')} {arrow} {dest_name}" for p in pasos]
                    msg2_text = "\n".join(lineas)
                else:
                    msg2_text = f"Nessun treno programmato a {nombre_est} alle {hora_int:02d}:00."
                nombre_boton = "Monte Po" if t_key == "montepo" else "Stesicoro"
                keyboard_ritorna = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔄 Ritornare a {nombre_boton}", callback_data=f"ritornare_{t_key}")
                ]])
                msg2 = await update.message.reply_text(msg2_text, parse_mode="Markdown", reply_markup=keyboard_ritorna)
                await store_id(context, msg2)
                return

    # Rimuovere numeri per il matching
    texto_limpio = re.sub(r'\b\d{1,4}\b', '', texto_limpio_orig).strip()
    texto_limpio = ' '.join(texto_limpio.split())
    palabras = texto_limpio.split()

    # ===== CHIUDE =====
    texto_lower_chiude = texto.lower()
    if any(frase in texto_lower_chiude for frase in [
        "chiude", "chiusura", "ultimo treno", "ultima corsa",
        "fino a che ora", "fino a quando", "orario chiusura",
        "quando chiude", "a che ora chiude", "ultimi treni",
        "ultimo treno oggi", "ultima corsa oggi"
    ]):
        now = get_simulated_now(context)
        is_special = is_new_years_eve(now) or is_sant_agata(now) or get_extension_horario(now) is not None
        if is_special:
            mp_h, mp_m = get_closing_time(now, "Montepo")
            st_h, st_m = get_closing_time(now, "Stesicoro")
            last_mp_str = f"{mp_h:02d}:{mp_m:02d}"
            last_st_str = f"{st_h:02d}:{st_m:02d}"
        else:
            eff = get_effective_datetime(now)
            tomorrow_noon = CATANIA_TZ.localize(
                datetime.combine((eff + timedelta(days=1)).date(), time(12, 0))
            )
            mp_today = get_schedule_list("Montepo", now)
            st_today = get_schedule_list("Stesicoro", now)
            mp_tomorrow = get_schedule_list("Montepo", tomorrow_noon)
            st_tomorrow = get_schedule_list("Stesicoro", tomorrow_noon)
            mp_madru = [t for t in mp_tomorrow if t.hour < 5]
            st_madru = [t for t in st_tomorrow if t.hour < 5]
            last_mp = mp_madru[-1] if mp_madru else mp_today[-1]
            last_st = st_madru[-1] if st_madru else st_today[-1]
            last_mp_str = last_mp.strftime("%H:%M")
            last_st_str = last_st.strftime("%H:%M")
        msg = (
            f"🚇 **Ultime partenze di oggi**\n"
            f"▪️ Da Monte Po verso Stesicoro: **{last_mp_str}**\n"
            f"▪️ Da Stesicoro verso Monte Po: **{last_st_str}**"
        )
        extension_msg = get_extension_message(now)
        if extension_msg:
            msg = extension_msg.rstrip() + "\n\n" + msg
        await update.message.reply_text(msg, parse_mode='Markdown')
        return

    KEYWORDS = {
        "corso sicilia": "stesicoro",
        "repubblica": "stesicoro",
        "archimede": "giovanni",
        "liberta": "giovanni",
        "centrale": "giovanni",
        "jonio": "galatea",
        "pasubio": "galatea",
        "palmanova": "galatea",
        "messina": "galatea",
        "firenze": "italia",
        "ramondetta": "italia",
        "scammacca": "italia",
        "veneto": "italia",
        "carvana": "giuffrida",
        "abraham": "giuffrida",
        "lincoln": "giuffrida",
        "empedocle": "borgo",
        "signorelli": "borgo",
        "bronte": "milo",
        "fleming": "milo",
        "bergamo": "cibali",
        "galermo": "cibali",
        "massimino": "cibali",
        "stadio": "cibali",
        "usodimare": "sannullo",
        "uso di mare": "sannullo",
        "sebastiano": "sannullo",
        "lorenzo": "nesima",
        "bolano": "nesima",
        "filippo": "nesima",
        "eredia": "nesima",
        "garibaldi": "fontana",
        "carlo": "montepo",
        "marx": "montepo",
    }
    KEYWORDS_NORM = {}
    for kw, station in KEYWORDS.items():
        kw_norm = unicodedata.normalize('NFKD', kw.lower()).encode('ASCII', 'ignore').decode('ASCII')
        KEYWORDS_NORM[kw_norm] = station

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

    mejor_clave_kw = None
    for kw_norm, station in KEYWORDS_NORM.items():
        if kw_norm in texto_limpio:
            mejor_clave_kw = station
            break
    if not mejor_clave_kw:
        palabras_limpio = texto_limpio.split()
        for kw_norm, station in KEYWORDS_NORM.items():
            kw_palabras = kw_norm.split()
            if len(kw_palabras) > 1:
                continue
            kw_len = len(kw_norm)
            for palabra in palabras_limpio:
                if len(palabra) <= 2:
                    continue
                dist = levenshtein_distance(palabra, kw_norm)
                if kw_len <= 4:
                    if dist == 0:
                        mejor_clave_kw = station
                        break
                else:
                    if dist <= 1:
                        mejor_clave_kw = station
                        break
            if mejor_clave_kw:
                break
    if mejor_clave_kw:
        await send_station_response(update, context, mejor_clave_kw, return_to_main=True)
        return

    for palabra in palabras:
        palabra_lower = palabra.lower()
        if (palabra_lower.startswith('este') or palabra_lower.startswith('ste')) or \
           (palabra_lower.endswith('coro') or palabra_lower.endswith('colo') or palabra_lower.endswith('como')):
            await send_station_response(update, context, "stesicoro", return_to_main=True)
            return

    ALIASES = {
        "misterbianco": "montepo",
        "humanitas": "nesima",
        "centro sicilia": "nesima",
        "centrosicilia": "nesima",
        "mister bianco": "montepo",
        "mr bianco": "montepo",
        "mr. bianco": "montepo",
        "giovanni": "giovanni",
        "giovanni xxiii": "giovanni",
        "stesicoro": "stesicoro",
        "monte po": "montepo",
        "san nullo": "sannullo",
        "nullo": "sannullo",
    }
    alias_norm = {}
    for alias, clave in ALIASES.items():
        alias_clean = unicodedata.normalize('NFKD', alias.lower()).encode('ASCII', 'ignore').decode('ASCII')
        alias_norm[alias_clean] = clave

    matches = []
    for alias, clave in alias_norm.items():
        if alias in texto_limpio:
            matches.append((texto_limpio.find(alias), clave))

    if not matches:
        giovanni_x_prefix = "giovanni x"
        if texto_limpio.startswith(giovanni_x_prefix):
            matches.append((0, "giovanni"))

    if not matches:
        palabras = texto_limpio.split()
        for alias, clave in alias_norm.items():
            max_dist = 1 if clave == "borgo" else 2
            for i, palabra in enumerate(palabras):
                if len(palabra) <= 3:
                    continue
                dist = levenshtein_distance(palabra, alias)
                if dist <= max_dist:
                    pos = sum(len(p) + 1 for p in palabras[:i])
                    matches.append((pos, clave))
                    break
            if matches:
                break

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

    if not matches:
        palabras = texto_limpio.split()
        for clave, nombre in estaciones:
            nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
            max_dist = 1 if clave == "borgo" else 2
            for i, palabra in enumerate(palabras):
                if len(palabra) <= 3:
                    continue
                dist = levenshtein_distance(palabra, nombre_norm)
                if dist <= max_dist:
                    pos = sum(len(p) + 1 for p in palabras[:i])
                    matches.append((pos, clave))
                    break
            if matches:
                break

    if not matches:
        for clave, nombre in estaciones:
            nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
            if nombre_norm.startswith(texto_limpio) and len(texto_limpio) >= 3:
                matches.append((0, clave))
                break
            if texto_limpio.startswith(nombre_norm) and len(nombre_norm) >= 3:
                matches.append((0, clave))
                break

    if not matches:
        if texto_limpio.startswith("gal"):
            matches.append((0, "galatea"))
        elif "galaxia" in texto_limpio:
            matches.append((0, "galatea"))

    if not matches and texto_limpio == "monte":
        matches.append((0, "montepo"))

    if matches:
        matches.sort(key=lambda x: x[0])
        mejor_clave = matches[0][1]

        INTERMEDIATE = {"fontana","nesima","sannullo","cibali","milo","borgo","giuffrida","italia","galatea","giovanni"}
        if mejor_clave in INTERMEDIATE and hora_schedule is not None:
            hora_int = hora_schedule
            now = get_simulated_now(context)
            nombre_est = NOMBRE_MOSTRAR[mejor_clave]
            seg_mp = get_total_seconds_from_montepo(mejor_clave, now)
            seg_st = get_total_seconds_from_stesicoro(mejor_clave, now)
            target_date = now.date()
            giorno_str = "oggi"
            hora_fine = CATANIA_TZ.localize(datetime.combine(now.date(), time(hora_int, 59)))
            if hora_fine < now:
                target_date = now.date() + timedelta(days=1)
                giorno_str = "domani"
                schedule_mp = get_schedule_list("Montepo", CATANIA_TZ.localize(datetime.combine(target_date, time(12, 0))))
                schedule_st = get_schedule_list("Stesicoro", CATANIA_TZ.localize(datetime.combine(target_date, time(12, 0))))
            else:
                schedule_mp = get_schedule_list("Montepo", now)
                schedule_st = get_schedule_list("Stesicoro", now)
            pasos = []
            for salida in schedule_mp:
                paso_dt = datetime.combine(target_date, salida) + timedelta(seconds=seg_mp)
                paso_dt = CATANIA_TZ.localize(paso_dt)
                if paso_dt.hour == hora_int:
                    pasos.append((paso_dt, "➡️ Stesicoro"))
            for salida in schedule_st:
                paso_dt = datetime.combine(target_date, salida) + timedelta(seconds=seg_st)
                paso_dt = CATANIA_TZ.localize(paso_dt)
                if paso_dt.hour == hora_int:
                    pasos.append((paso_dt, "➡️ Monte Po"))
            if giorno_str == "oggi":
                pasos = [(p, d) for p, d in pasos if p > now]
            pasos.sort(key=lambda x: x[0])
            img_url = get_station_image(mejor_clave, now)
            caption1 = f"🕐 **Passaggi a {nombre_est} {giorno_str} alle {hora_int:02d}:00**\n1️⃣ Marciapiede 1 → Monte Po  |  2️⃣ Marciapiede 2 → Stesicoro"
            if img_url:
                msg1 = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_url, caption=caption1, parse_mode="Markdown")
            else:
                msg1 = await update.message.reply_text(caption1, parse_mode="Markdown")
            await store_id(context, msg1)
            if pasos:
                lineas = []
                for paso_dt, direction in pasos:
                    to_montepo = "Monte Po" in direction
                    num = "1️⃣" if to_montepo else "2️⃣"
                    arrow = "🔺" if to_montepo else "🔻"
                    dest = "Monte Po" if to_montepo else "Stesicoro"
                    lineas.append(f"{num} {paso_dt.strftime('%H:%M')} {arrow} {dest}")
                msg2_text = "\n".join(lineas)
            else:
                msg2_text = f"Nessun treno programmato a {nombre_est} alle {hora_int:02d}:00."
            nombre_boton = nombre_est if mejor_clave != "giovanni" else "Giovanni XXIII"
            keyboard_ritorna = InlineKeyboardMarkup([[
                InlineKeyboardButton(f"🔄 Ritornare a {nombre_boton}", callback_data=f"ritornare_{mejor_clave}")
            ]])
            msg2 = await update.message.reply_text(msg2_text, parse_mode="Markdown", reply_markup=keyboard_ritorna)
            await store_id(context, msg2)
            return

        await send_station_response(update, context, mejor_clave, return_to_main=True)
        return

    msg = await update.message.reply_text(
        "Stazione non riconosciuta. Le stazioni disponibili sono: " +
        ", ".join(NOMBRE_MOSTRAR.values()) + ".\nPuoi anche usare alias come 'Misterbianco' (Monte Po) o 'Humanitas' (Nesima).",
        reply_markup=keyboard_main
    )
    await store_id(context, msg)
