import asyncio
import time as time_module
import unicodedata
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
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
# LIMPIAR TEXTO
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
# ALMACENAR IDS
# ============================================================================
async def store_id(context, message):
    if message and hasattr(message, 'message_id'):
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        if message.message_id not in context.chat_data['all_msg_ids']:
            context.chat_data['all_msg_ids'].append(message.message_id)

# ============================================================================
# DETENER SUPER
# ============================================================================
def stop_super_update(context):
    if 'super_task' in context.chat_data:
        context.chat_data['super_active'] = False
        try:
            context.chat_data['super_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('super_task', None)

# ============================================================================
# COUNTDOWN PARA CABECERAS
# ============================================================================
async def update_countdown(context, chat_id, message_id, initial_remaining, station, dest, next_dep, dev_mode):
    remaining = initial_remaining
    while remaining > 10:
        await asyncio.sleep(10)
        if not context.chat_data.get('countdown_active', False):
            return
        try:
            now = get_simulated_now(context)
            remaining_calc = (next_dep - now).total_seconds()
            if remaining_calc <= 0:
                new_msg = f"🚇 Il treno per {dest} è partito."
                keyboard_inline = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{station.lower()}")]
                ])
                await context.bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=new_msg, parse_mode='Markdown', reply_markup=keyboard_inline)
                context.chat_data['countdown_active'] = False
                return
            mins_rest = int(remaining_calc // 60)
            secs_rest = int(remaining_calc % 60)
            if dev_mode:
                time_str = format_time_precise(mins_rest, secs_rest)
            else:
                time_str = format_time(mins_rest, secs_rest)
            new_msg = f"Il treno è in binario. Partirà tra **{time_str}**."
            await context.bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=new_msg, parse_mode='Markdown')
            remaining = remaining_calc
        except Exception as e:
            logger.error(f"Error en countdown: {e}")
            break
    if context.chat_data.get('countdown_active', False):
        try:
            now = get_simulated_now(context)
            station_key = "montepo" if station == "Montepo" else "stesicoro"
            next_dep_new, minutes, seconds, has_trains = get_next_departure(station, now)
            if not has_trains:
                close_h, close_m = get_closing_time(now, station)
                new_msg = f"🚇 Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
            else:
                dest = "Stesicoro" if station == "Montepo" else "Monte Po"
                remaining_new = (next_dep_new - now).total_seconds()
                mins_rest = int(remaining_new // 60)
                secs_rest = int(remaining_new % 60)
                if dev_mode:
                    time_str = format_time_precise(mins_rest, secs_rest)
                else:
                    time_str = format_time(mins_rest, secs_rest)
                if remaining_new <= 60:
                    new_msg = f"Il treno è in binario. Partirà tra **{time_str}**."
                else:
                    if mins_rest <= 4:
                        new_msg = f"Il treno è in binario. Partirà tra **{time_str}**."
                    else:
                        if minutes < SHORT_TIME_THRESHOLD:
                            new_msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**."
                        else:
                            new_msg = f"🚇 Prossimo treno per {dest} parte tra **{time_str}**, alle {next_dep_new.strftime('%H:%M')}."
            keyboard_inline = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"agg_cabecera_{station.lower()}")]
            ])
            await context.bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=new_msg, parse_mode='Markdown', reply_markup=keyboard_inline)
        except Exception as e:
            logger.error(f"Error al finalizar countdown: {e}")
        finally:
            context.chat_data['countdown_active'] = False

# ============================================================================
# BUSES
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
# CONSTRUCCIÓN DE MENSAJES DE TRENES (msg2 y msg3)
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
        # ... (código de localización, igual que antes, omito por brevedad pero está en tu archivo original)
        msg2 += line
        if mins <= 1 and next_info:
            paso2, mins2, secs2 = next_info
            # ...
    else:
        msg2 += f"🔺 **Per Monte Po**: nessun treno in arrivo al momento.\n"

    # similar para msg3...
    # Por simplicidad, mantén tu implementación original de build_temporary_messages
    # Aquí solo pongo un esqueleto, pero debes usar la versión completa que ya tienes.
    # ...

    return msg2, msg3, current_station_key_mp, tiempo_restante_mp, current_station_key_st, tiempo_restante_st, mins_mp, mins_st

# ============================================================================
# FUNCIONES DE ENVÍO (send_message_2, send_message_3, send_messages_2_and_3, etc.)
# ============================================================================
# ... (código completo que ya tienes, no lo reescribo para no duplicar)
# Asegúrate de incluir todas las funciones que ya funcionaban.

# ============================================================================
# ENVÍO DE RESPUESTA DE CABECERA
# ============================================================================
async def send_header_response(chat_id, context, estacion_key, is_update=False):
    # ... (tu código existente)
    pass

# ============================================================================
# RESPUESTA PRINCIPAL PARA ESTACIONES
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    if 'countdown_task' in context.chat_data:
        try:
            context.chat_data['countdown_task'].cancel()
        except:
            pass
        context.chat_data.pop('countdown_task', None)
        context.chat_data['countdown_active'] = False

    stop_super_update(context)
    context.chat_data['last_return_to_main'] = return_to_main
    now = get_simulated_now(context)
    demo_mode = context.chat_data.get('demo_mode', False)

    test_indicator = ""
    if (context.chat_data.get('test_time') is not None or context.chat_data.get('test_live_base') is not None) and not demo_mode:
        test_indicator = "🧪 [TEST MODE] "

    if estacion_key in ["montepo", "stesicoro"]:
        await send_header_response(update.message.chat_id, context, estacion_key, is_update=False)
        await maybe_send_home_tip(update, context)
        return

    # ... resto de la lógica para estaciones intermedias
    # Al final, llama a maybe_send_home_tip
    await maybe_send_home_tip(update, context)

# ============================================================================
# COMANDOS Y WRAPPERS (start, help, test, testlive, testfin, etc.)
# ============================================================================
# ... (todo el código de comandos que ya tienes, incluyendo test_command, testlive_command)
