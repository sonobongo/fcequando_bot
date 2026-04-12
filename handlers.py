import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
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
# ENVÍO DE MENSAJE 2 (hacia Monte Po) y 3 (hacia Stesicoro)
# ============================================================================
async def send_message_2(update: Update, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str):
    if tiempo_restante is not None and (tiempo_restante <= 90 or mins <= 1):
        return await send_treno_arrivo(update, msg, "Monte Po")
    elif current_station_key and current_station_key != "montepo":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_stesicoro_{current_station_key}.gif"
        return await send_gif(update, msg, gif_url)
    else:
        return await send_default(update, msg)

async def send_message_3(update: Update, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str):
    if tiempo_restante is not None and (tiempo_restante <= 90 or mins <= 1):
        return await send_treno_arrivo(update, msg, "Stesicoro")
    elif current_station_key and current_station_key != "stesicoro":
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.gif"
        return await send_gif(update, msg, gif_url)
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
async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False):
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    default2 = is_default_message(key_mp, time_mp, mins_mp)
    default3 = is_default_message(key_st, time_st, mins_st)
    
    if default2 and default3:
        msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
        await asyncio.sleep(0.5)
        msg3_obj = await update.message.reply_text(msg3, parse_mode='Markdown')
        return (msg2_obj.message_id, msg3_obj.message_id)
    else:
        msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
        await asyncio.sleep(0.5)
        msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key)
        return (msg2_obj.message_id, msg3_obj.message_id)

# ============================================================================
# BUCLE AUTO (30 segundos, 20 ciclos) - para /auto
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
    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
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
        new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
        context.chat_data['auto_msg_ids'] = list(new_ids)
        context.chat_data['auto_cycles_left'] -= 1
    context.chat_data['auto_active'] = False
    context.chat_data.pop('auto_msg_ids', None)
    context.chat_data.pop('auto_cycles_left', None)
    await update.message.reply_text("🔄 Aggiornamenti automatici terminati (20 cicli completati).")

# ============================================================================
# REFRESCO NORMAL (3 ciclos: 35,45,55 segundos) - para estaciones normales y Milo
# ============================================================================
async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    tiempos_espera = [35, 45, 55]
    try:
        for espera in tiempos_espera:
            await asyncio.sleep(espera)
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
            new_ids = await send_messages_2_and_3(update, estacion_key, now, use_simulated)
            context.chat_data['refresh_msg_ids'] = new_ids
    except asyncio.CancelledError:
        pass
    finally:
        context.chat_data['refresh_active'] = False
        context.chat_data.pop('refresh_task', None)
        context.chat_data.pop('cancel_refresh', None)
        # Ya no enviamos ningún mensaje de "ciclo completado"

# ============================================================================
# FUNCIÓN PARA ENVIAR EL BOTÓN INLINE "Aggiornare" (solo para Milo)
# ============================================================================
async def send_aggiornare_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje con un botón inline 'Aggiornare' para refrescar Milo manualmente"""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_milo")]])
    await update.message.reply_text("", reply_markup=keyboard)

# ============================================================================
# CALLBACK PARA EL BOTÓN "Aggiornare"
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Responde al clic
    # Reiniciamos Milo llamando a cmd_milo_wrapper (necesitamos obtener el chat_id)
    chat_id = query.message.chat_id
    # Simular un mensaje para poder usar el wrapper
    class FakeMessage:
        def __init__(self, chat_id):
            self.chat_id = chat_id
    fake_update = type('obj', (object,), {
        'effective_chat': type('obj', (object,), {'id': chat_id})(),
        'message': type('obj', (object,), {'reply_text': lambda *args, **kwargs: None})()
    })
    # Llamar al wrapper de Milo
    await cmd_milo_wrapper(fake_update, context)

# ============================================================================
# RESPUESTA PRINCIPAL (foto de estación + msg2/msg3 + aviso de cierre)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    # Detener cualquier bucle automático
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
            msg = f"🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
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
        elif "22:30" in last_msg:
            last_msg = last_msg.replace("📌", "🕙")
        last_msg_text = f"\n\n{last_msg}"
    permanent_caption = f"{test_indicator}🚇 Prossimi treni a {nombre}{last_msg_text}"
    img_station = get_station_image(estacion_key, now)
    if img_station:
        await update.message.reply_photo(photo=img_station, caption=permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    else:
        await update.message.reply_text(permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)

    # Enviar mensajes 2 y 3
    ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None)
    context.chat_data['refresh_msg_ids'] = ids

    # Si es Milo, enviar el botón inline "Aggiornare" (sin texto adicional)
    if estacion_key == "milo":
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_milo")]])
        await update.message.reply_text("", reply_markup=keyboard)

    # Iniciar el refresco normal (3 ciclos con tiempos variables) solo para estaciones que no son Milo?
    # Para Milo también queremos refrescos automáticos? Por ahora sí, pero el botón permite reiniciar manualmente.
    context.chat_data['refresh_active'] = True
    task = asyncio.create_task(auto_refresh_loop(update, context, estacion_key, update.effective_chat.id, nombre, use_simulated=(simulated is not None), simulated_now=now if simulated else None))
    context.chat_data['refresh_task'] = task

# ============================================================================
# WRAPPERS Y COMANDOS (incluyendo /auto y /stop)
# ============================================================================
async def cancel_refresh_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE, coro, *args, **kwargs):
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
        context.chat_data.pop('auto_cycles_left', None)
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
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

# Funciones originales
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
        "/auto - Avvia aggiornamenti ogni 30 secondi (20 cicli)\n"
        "/stop - Ferma gli aggiornamenti automatici\n"
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/test DDMMYYYY HHMM X - Test con 3 cicli (M, S, ML)\n"
        "/testfin - Disattiva modalità test\n"
        "/testgif - Invia GIF di prova e lo cancella dopo 1 minuto\n\n"
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
    if not context.chat_data.get('refresh_task') and not context.chat_data.get('auto_active'):
        await update.message.reply_text("⚠️ Prima seleziona una stazione (premi un pulsante).")
        return
    if context.chat_data.get('auto_active'):
        await update.message.reply_text("🔄 Aggiornamenti automatici già in corso. Usa /stop per fermarli.")
        return
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

# Exportar la función callback para que metro_bot.py la pueda registrar
# (ya está definida arriba)
