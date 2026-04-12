import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
# CONSTRUCCIÓN DE MENSAJES TEMPORALES (sin cambios)
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str):
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    closing_msg = get_closing_message(estacion_key, now)

    msg2 = ""
    current_station_key_mp = None
    tiempo_restante_mp = None
    if closing_msg:
        msg2 += f"{closing_msg}\n"
    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        tiempo_restante_mp = mins*60 + secs
        if mins == 0 and secs < 30:
            line = f"🔺 **Per Monte Po**: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**, alle {paso_st.strftime('%H:%M')}.\n"
            else:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**.\n"
        # Localización del tren (solo para estaciones intermedias)
        estaciones_localizacion = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "fontana"]
        if estacion_key in estaciones_localizacion and 2 <= mins <= 10:
            rest_seconds = mins*60 + secs
            total_seconds = get_total_seconds_from_stesicoro(estacion_key, now)
            if rest_seconds < total_seconds:
                seconds_passed = total_seconds - rest_seconds
                if seconds_passed < 0:
                    seconds_passed = 0
                current_station = get_current_station_from_stesicoro(now, seconds_passed)
                if current_station not in ["non ancora partito da Stesicoro", "Il treno è appena partito da Stesicoro"]:
                    for key, name in NOMBRE_MOSTRAR.items():
                        if name == current_station:
                            current_station_key_mp = key
                            break
                elif current_station == "Il treno è appena partito da Stesicoro":
                    current_station_key_mp = "stesicoro"
                if "appena partito" in current_station:
                    line += f"   [{current_station}]\n"
                elif "non ancora partito" not in current_station:
                    line += f"   [il treno si trova attualmente a {current_station}]\n"
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
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
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
            if current_station not in ["non ancora partito da Monte Po", "Il treno è appena partito da Monte Po"]:
                for key, name in NOMBRE_MOSTRAR.items():
                    if name == current_station:
                        current_station_key_st = key
                        break
            elif current_station == "Il treno è appena partito da Monte Po":
                current_station_key_st = "montepo"
        estaciones_localizacion2 = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni"]
        if estacion_key in estaciones_localizacion2 and 2 <= mins <= 10:
            if rest_seconds < total_seconds:
                if "appena partito" in current_station:
                    line += f"   [{current_station}]\n"
                elif "non ancora partito" not in current_station:
                    line += f"   [il treno si trova attualmente a {current_station}]\n"
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

    return msg2, msg3, current_station_key_mp, tiempo_restante_mp, current_station_key_st, tiempo_restante_st

# ============================================================================
# FUNCIONES DE ENVÍO CON IMAGEN (prioridad: llegada <=90s > GIF > default)
# ============================================================================
async def send_treno_arrivo(update: Update, msg: str, direction: str):
    """Envía la imagen de tren en llegada (ruta_trenoarriva.png)"""
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown')

async def send_gif(update: Update, msg: str, gif_url: str):
    """Envía un GIF con caption"""
    cache_buster = int(time_module.time())
    gif_url = f"{gif_url}?v={cache_buster}"
    try:
        return await update.message.reply_animation(animation=gif_url, caption=msg, parse_mode='Markdown')
    except Exception:
        # Si falla el GIF, usar imagen por defecto
        return await send_default(update, msg)

async def send_default(update: Update, msg: str):
    """Envía la imagen por defecto (ruta_default.png)"""
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    try:
        return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
    except Exception:
        return await update.message.reply_text(msg, parse_mode='Markdown')

# ============================================================================
# ENVÍO DE MENSAJE 2 (dirección Monte Po) y 3 (dirección Stesicoro)
# ============================================================================
async def send_message_2(update: Update, msg: str, current_station_key: str, tiempo_restante: int, estacion_key: str):
    """
    Envía el mensaje 2 (tren hacia Monte Po).
    Prioridad: si tiempo <= 90 -> imagen tren en llegada.
    Si no, y tenemos estación actual -> GIF ruta_stesicoro_{station}.gif.
    Si no, imagen por defecto.
    """
    if tiempo_restante is not None and tiempo_restante <= 90:
        return await send_treno_arrivo(update, msg, "Monte Po")
    elif current_station_key:
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_stesicoro_{current_station_key}.gif"
        return await send_gif(update, msg, gif_url)
    else:
        return await send_default(update, msg)

async def send_message_3(update: Update, msg: str, current_station_key: str, tiempo_restante: int, estacion_key: str):
    """
    Envía el mensaje 3 (tren hacia Stesicoro).
    Prioridad: si tiempo <= 90 -> imagen tren en llegada.
    Si no, y tenemos estación actual -> GIF ruta_montepo_{station}.gif.
    Si no, imagen por defecto.
    """
    if tiempo_restante is not None and tiempo_restante <= 90:
        return await send_treno_arrivo(update, msg, "Stesicoro")
    elif current_station_key:
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.gif"
        return await send_gif(update, msg, gif_url)
    else:
        return await send_default(update, msg)

# ============================================================================
# FUNCIÓN PRINCIPAL PARA ENVIAR AMBOS MENSAJES (reutilizable)
# ============================================================================
async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False):
    msg2, msg3, key_mp, time_mp, key_st, time_st = build_temporary_messages(now, estacion_key)
    
    # Enviar mensaje 2 (hacia Monte Po)
    msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, estacion_key)
    await asyncio.sleep(0.5)  # Pequeña pausa para evitar flood
    # Enviar mensaje 3 (hacia Stesicoro)
    msg3_obj = await send_message_3(update, msg3, key_st, time_st, estacion_key)
    
    return (msg2_obj.message_id, msg3_obj.message_id)

# ============================================================================
# BUCLE AUTO (30 segundos, 20 ciclos)
# ============================================================================
async def auto_update_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int):
    # Detener cualquier refresco anterior
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    
    # Borrar mensajes automáticos previos si existen
    if 'auto_msg_ids' in context.chat_data:
        for mid in context.chat_data['auto_msg_ids']:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('auto_msg_ids', None)
    
    # Obtener hora actual con zona horaria
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    # Enviar primera tanda
    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
    context.chat_data['auto_msg_ids'] = list(ids)
    context.chat_data['auto_active'] = True
    context.chat_data['auto_cycles_left'] = 19  # ya llevamos 1 de 20
    
    for ciclo in range(19):
        await asyncio.sleep(30)
        if not context.chat_data.get('auto_active', False):
            break
        
        # Borrar mensajes anteriores
        if 'auto_msg_ids' in context.chat_data:
            for mid in context.chat_data['auto_msg_ids']:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
        
        # Avanzar el tiempo si estamos en modo simulado
        if simulated:
            now = now + timedelta(seconds=30)
        else:
            now = datetime.now(CATANIA_TZ)
        
        # Enviar nuevos mensajes
        new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
        context.chat_data['auto_msg_ids'] = list(new_ids)
        context.chat_data['auto_cycles_left'] -= 1
    
    # Finalizar
    context.chat_data['auto_active'] = False
    context.chat_data.pop('auto_msg_ids', None)
    context.chat_data.pop('auto_cycles_left', None)
    await update.message.reply_text("🔄 Aggiornamenti automatici terminati (20 cicli completati).")

# ============================================================================
# REFRESCO NORMAL (3 ciclos con tiempos variables: 35,45,55 segundos)
# ============================================================================
async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    tiempos_espera = [35, 45, 55]
    try:
        for espera in tiempos_espera:
            await asyncio.sleep(espera)
            if context.chat_data.get('cancel_refresh', False):
                break
            # Borrar mensajes anteriores
            msg_ids = context.chat_data.get('refresh_msg_ids')
            if msg_ids:
                for mid in msg_ids:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                    except Exception:
                        pass
            # Calcular nuevos mensajes
            if use_simulated and simulated_now:
                now = simulated_now
                if now.tzinfo is None:
                    now = CATANIA_TZ.localize(now)
            else:
                now = datetime.now(CATANIA_TZ)
            
            new_ids = await send_messages_2_and_3(update, estacion_key, now, use_simulated)
            context.chat_data['refresh_msg_ids'] = new_ids
    except asyncio.CancelledError:
        pass
    finally:
        context.chat_data['refresh_active'] = False
        context.chat_data.pop('refresh_task', None)
        context.chat_data.pop('cancel_refresh', None)

# ============================================================================
# RESPUESTA PRINCIPAL (solo la parte relevante para estaciones intermedias)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    # Detener cualquier bucle automático activo
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
    
    # Detener refresco normal
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    context.chat_data['cancel_refresh'] = False
    
    # Obtener hora actual
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    test_indicator = "🧪 [TEST MODE] " if simulated else ""

    # ... (aquí va toda la lógica de cabeceras y cierres que ya tenías, no la copio entera por brevedad,
    # pero debes mantener la que ya funciona. Solo modifico el envío de mensajes 2 y 3 al final)
    # Suponiendo que ya tienes el código de cabeceras (Monte Po, Stesicoro, etc.)
    # Al final, cuando toca enviar mensajes 2 y 3 para estaciones intermedias, haces:

    # Enviar los mensajes 2 y 3 iniciales
    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
    context.chat_data['refresh_msg_ids'] = ids

    # Iniciar el refresco normal (3 ciclos con tiempos variables)
    context.chat_data['refresh_active'] = True
    task = asyncio.create_task(auto_refresh_loop(update, context, estacion_key, update.effective_chat.id, nombre, use_simulated=(simulated is not None), simulated_now=now if simulated else None))
    context.chat_data['refresh_task'] = task

# ============================================================================
# COMANDOS /auto y /stop (igual que antes)
# ============================================================================
async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.chat_data.get('refresh_task') and not context.chat_data.get('auto_active'):
        await update.message.reply_text("⚠️ Prima seleziona una stazione (premi un pulsante).")
        return
    if context.chat_data.get('auto_active'):
        await update.message.reply_text("🔄 Aggiornamenti automatici già in corso. Usa /stop per fermarli.")
        return
    
    # Detener refresco normal
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    
    estacion_key = context.chat_data.get('last_station')
    if not estacion_key:
        await update.message.reply_text("⚠️ Non riesco a determinare la stazione. Premi un pulsante prima di usare /auto.")
        return
    
    chat_id = update.effective_chat.id
    task = asyncio.create_task(auto_update_loop(update, context, estacion_key, chat_id))
    context.chat_data['auto_task'] = task
    await update.message.reply_text("🔄 Aggiornamenti automatici avviati. Ogni 30 secondi verranno mostrati nuovi dati per 20 volte. Usa /stop per fermare.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get('auto_active'):
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
        context.chat_data.pop('auto_cycles_left', None)
        await update.message.reply_text("✅ Aggiornamenti automatici fermati. Il bot torna alla modalità normale.")
    else:
        await update.message.reply_text("⚠️ Nessun aggiornamento automatico in corso.")

# ============================================================================
# WRAPPERS Y COMANDOS BÁSICOS (aquí debes incluir todos los que ya tenías)
# ============================================================================
# ... (tus wrappers existentes: start_wrapper, help_command_wrapper, etc.)
# Asegúrate de añadir auto_wrapper y stop_wrapper
