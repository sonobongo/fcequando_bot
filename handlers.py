import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
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
# FUNCIONES AUXILIARES DE LOCALIZACIÓN (sin cambios)
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
# CONSTRUCCIÓN DE MENSAJES TEMPORALES (sin cambios)
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str):
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    closing_msg = get_closing_message(estacion_key, now)
    last_msg = get_last_train_message(now)
    last_msg_text = f"\n{last_msg}" if last_msg and not is_sant_agata(now) else ""

    # Mensaje 2 (Monte Po)
    msg2 = ""
    if closing_msg:
        msg2 += f"{closing_msg}\n"
    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        if mins == 0 and secs < 30:
            line = f"🔺 **Per Monte Po**: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**, alle {paso_st.strftime('%H:%M')}.\n"
            else:
                line = f"🔺 **Per Monte Po**: Passa tra **{time_str}**.\n"
        estaciones_localizacion_montepo = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "fontana"]
        if estacion_key in estaciones_localizacion_montepo and 2 <= mins <= 10:
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
    if last_msg_text:
        msg2 += last_msg_text

    # Mensaje 3 (Stesicoro) y clave para foto de ruta
    msg3 = ""
    current_station_key = None
    tiempo_restante = None
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        time_str = format_time(mins, secs)
        tiempo_restante = mins*60 + secs
        if mins == 0 and secs < 30:
            line = f"🔻 **Per Stesicoro**: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**, alle {paso_mp.strftime('%H:%M')}.\n"
            else:
                line = f"🔻 **Per Stesicoro**: Passa tra **{time_str}**.\n"
        rest_seconds = tiempo_restante
        total_seconds = get_total_seconds_from_montepo(estacion_key, now)
        if rest_seconds < total_seconds:
            seconds_passed = total_seconds - rest_seconds
            if seconds_passed < 0:
                seconds_passed = 0
            current_station = get_current_station_from_montepo(now, seconds_passed)
            if current_station not in ["non ancora partito da Monte Po", "Il treno è appena partito da Monte Po"]:
                for key, name in NOMBRE_MOSTRAR.items():
                    if name == current_station:
                        current_station_key = key
                        break
            elif current_station == "Il treno è appena partito da Monte Po":
                current_station_key = "montepo"
        # Mostrar texto de localización solo si 2-10 min
        estaciones_localizacion_stesicoro = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni"]
        if estacion_key in estaciones_localizacion_stesicoro and 2 <= mins <= 10:
            if rest_seconds < total_seconds:
                if "appena partito" in current_station:
                    line += f"   ({current_station})\n"
                elif "non ancora partito" not in current_station:
                    line += f"   (il treno si trova attualmente a {current_station})\n"
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
        tiempo_restante = 9999
    if last_msg_text:
        msg3 += last_msg_text

    return msg2, msg3, current_station_key, tiempo_restante

# ============================================================================
# FUNCIÓN PARA BORRAR MENSAJES ANTERIORES DEL BOT
# ============================================================================
async def clear_previous_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra todos los mensajes que el bot ha enviado anteriormente en este chat."""
    if 'bot_messages' in context.chat_data:
        for msg_id in context.chat_data['bot_messages']:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            except Exception:
                pass  # Si no se puede borrar (por ejemplo, mensaje muy antiguo), ignoramos
        context.chat_data['bot_messages'] = []
    else:
        context.chat_data['bot_messages'] = []
    
    # Opcional: borrar también el mensaje del usuario que activó la consulta (si es posible)
    try:
        await update.message.delete()
    except Exception:
        pass  # En grupos sin permisos o en canales puede fallar, no pasa nada

# ============================================================================
# TAREA DE ACTUALIZACIÓN AUTOMÁTICA (3 ciclos de 45 segundos)
# ============================================================================
async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    # Guardar datos para posible refresco
    context.chat_data['refresh_station_key'] = estacion_key
    context.chat_data['refresh_station_name'] = station_display_name
    if use_simulated and simulated_now:
        context.chat_data['refresh_simulated'] = simulated_now
    else:
        context.chat_data.pop('refresh_simulated', None)

    # Enviar primera tanda de mensajes (ciclo 0)
    now = simulated_now if (use_simulated and simulated_now) else datetime.now(CATANIA_TZ)
    msg2, msg3, current_station_key, tiempo_restante = build_temporary_messages(now, estacion_key)
    msg2_obj = await update.message.reply_text(msg2, parse_mode='Markdown')
    # Guardar ID
    context.chat_data['bot_messages'].append(msg2_obj.message_id)
    
    if current_station_key and tiempo_restante is not None and tiempo_restante > 90:
        ruta_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.png"
        try:
            msg3_obj = await update.message.reply_photo(photo=ruta_url, caption=msg3, parse_mode='Markdown')
        except:
            msg3_obj = await update.message.reply_text(msg3, parse_mode='Markdown')
    else:
        msg3_obj = await update.message.reply_text(msg3, parse_mode='Markdown')
    context.chat_data['bot_messages'].append(msg3_obj.message_id)
    
    context.chat_data['refresh_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id)

    # Ciclos restantes (1 y 2) con espera de 45s y borrado previo
    for ciclo in range(1, 3):
        if context.chat_data.get('cancel_refresh', False):
            break
        await asyncio.sleep(45)
        if context.chat_data.get('cancel_refresh', False):
            break
        # Borrar mensajes anteriores
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg2_obj.message_id)
        except:
            pass
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg3_obj.message_id)
        except:
            pass
        # Eliminar IDs de la lista
        if msg2_obj.message_id in context.chat_data['bot_messages']:
            context.chat_data['bot_messages'].remove(msg2_obj.message_id)
        if msg3_obj.message_id in context.chat_data['bot_messages']:
            context.chat_data['bot_messages'].remove(msg3_obj.message_id)
        
        # Calcular nuevos mensajes
        now = simulated_now if (use_simulated and simulated_now) else datetime.now(CATANIA_TZ)
        msg2, msg3, current_station_key, tiempo_restante = build_temporary_messages(now, estacion_key)
        msg2_obj = await update.message.reply_text(msg2, parse_mode='Markdown')
        context.chat_data['bot_messages'].append(msg2_obj.message_id)
        if current_station_key and tiempo_restante is not None and tiempo_restante > 90:
            ruta_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key}.png"
            try:
                msg3_obj = await update.message.reply_photo(photo=ruta_url, caption=msg3, parse_mode='Markdown')
            except:
                msg3_obj = await update.message.reply_text(msg3, parse_mode='Markdown')
        else:
            msg3_obj = await update.message.reply_text(msg3, parse_mode='Markdown')
        context.chat_data['bot_messages'].append(msg3_obj.message_id)
        context.chat_data['refresh_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id)

    # Después del tercer ciclo, enviar botón de refrescar (si no se canceló)
    if not context.chat_data.get('cancel_refresh', False):
        refresh_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refrescar", callback_data=f"refresh_{estacion_key}")]])
        button_msg = await update.message.reply_text("", reply_markup=refresh_keyboard)
        context.chat_data['bot_messages'].append(button_msg.message_id)

    # Limpiar flags al finalizar
    context.chat_data['refresh_active'] = False
    context.chat_data.pop('cancel_refresh', None)

# ============================================================================
# RESPUESTA PRINCIPAL (para comandos normales y test)
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    # Borrar todos los mensajes anteriores del bot en este chat
    await clear_previous_bot_messages(update, context)

    simulated = context.chat_data.get('test_time') if context.chat_data else None
    now = simulated if simulated else datetime.now(CATANIA_TZ)
    test_indicator = "🧪 [TEST MODE] " if simulated else ""

    warning = get_closing_warning(now)
    if warning:
        warn_msg = await update.message.reply_text(warning, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        context.chat_data['bot_messages'].append(warn_msg.message_id)

    special_msg = SANT_AGATA.get("message", "") + "\n\n" if is_sant_agata(now) else ""

    if is_closed_all_day(now):
        msg = f"{special_msg}{test_indicator}🚇 Oggi la metropolitana è chiusa tutto il giorno.\n🕒 Riaprirà domani mattina."
        img = get_station_image(estacion_key, now)
        if img:
            photo_msg = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            context.chat_data['bot_messages'].append(photo_msg.message_id)
        else:
            text_msg = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            context.chat_data['bot_messages'].append(text_msg.message_id)
        return

    # Cabeceras Monte Po y Stesicoro (sin refrescos)
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
                photo_msg = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
                context.chat_data['bot_messages'].append(photo_msg.message_id)
            else:
                text_msg = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
                context.chat_data['bot_messages'].append(text_msg.message_id)
            return

        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            msg = f"{special_msg}{test_indicator}🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            img = get_station_image(estacion_key, now)
            if img:
                photo_msg = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
                context.chat_data['bot_messages'].append(photo_msg.message_id)
            else:
                text_msg = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
                context.chat_data['bot_messages'].append(text_msg.message_id)
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
            photo_msg = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
            context.chat_data['bot_messages'].append(photo_msg.message_id)
        else:
            text_msg = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
            context.chat_data['bot_messages'].append(text_msg.message_id)
        return

    # ========================================================================
    # ESTACIONES INTERMEDIAS
    # ========================================================================
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
            photo_msg = await update.message.reply_photo(photo=img, caption=msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            context.chat_data['bot_messages'].append(photo_msg.message_id)
        else:
            text_msg = await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            context.chat_data['bot_messages'].append(text_msg.message_id)
        return

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    img_station = get_station_image(estacion_key, now)

    # 1. Enviar la foto de la estación con título corto
    permanent_caption = f"{test_indicator}🚆 Prossimi treni a {nombre}"
    if img_station:
        photo_msg = await update.message.reply_photo(photo=img_station, caption=permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        context.chat_data['bot_messages'].append(photo_msg.message_id)
    else:
        text_msg = await update.message.reply_text(permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        context.chat_data['bot_messages'].append(text_msg.message_id)

    # 2. Iniciar el ciclo de actualización automática
    if context.chat_data.get('refresh_active', False):
        context.chat_data['cancel_refresh'] = True
        await asyncio.sleep(0.5)
    context.chat_data['refresh_active'] = True
    context.chat_data['cancel_refresh'] = False

    station_display_name = nombre
    if simulated is None:
        asyncio.create_task(auto_refresh_loop(update, context, estacion_key, update.effective_chat.id, station_display_name, use_simulated=False))
    else:
        asyncio.create_task(auto_refresh_loop(update, context, estacion_key, update.effective_chat.id, station_display_name, use_simulated=True, simulated_now=now))

# ============================================================================
# CALLBACK DEL BOTÓN DE REFRESCAR
# ============================================================================
async def callback_refrescar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("refresh_"):
        return
    estacion_key = data.split("_")[1]
    
    if context.chat_data.get('refresh_active', False):
        context.chat_data['cancel_refresh'] = True
        await asyncio.sleep(0.5)
    
    class FakeUpdate:
        def __init__(self, message):
            self.message = message
            self.effective_chat = message.chat
            self.effective_user = message.from_user
    fake_update = FakeUpdate(query.message)
    await send_station_response(fake_update, context, estacion_key, return_to_main=False)

# ============================================================================
# COMANDO REFRESCAR (por si se usa como comando de texto)
# ============================================================================
async def cmd_refrescar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estacion_key = context.chat_data.get('refresh_station_key')
    if not estacion_key:
        await update.message.reply_text("⚠️ Nessuna sessione attiva. Premi prima una stazione.")
        return
    await callback_refrescar(update, context)

# ============================================================================
# MANEJADORES DE COMANDOS (con cancelación de refrescos)
# ============================================================================
async def cancel_refresh_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE, coro, *args, **kwargs):
    if context.chat_data and context.chat_data.get('refresh_active', False):
        context.chat_data['cancel_refresh'] = True
        await asyncio.sleep(0.5)
    await coro(update, context, *args, **kwargs)

# Wrappers (sin cambios)
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
async def start_wrapper(update, context): await cancel_refresh_and_run(update, context, start)
async def help_command_wrapper(update, context): await cancel_refresh_and_run(update, context, help_command)
async def handle_button_wrapper(update, context): await cancel_refresh_and_run(update, context, handle_button)
async def cmd_testgif_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_testgif)
async def test_command_wrapper(update, context): await cancel_refresh_and_run(update, context, test_command)
async def testfin_command_wrapper(update, context): await cancel_refresh_and_run(update, context, testfin_command)
async def cmd_refrescar_wrapper(update, context): await cancel_refresh_and_run(update, context, cmd_refrescar)

# Funciones originales (sin wrapper)
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
async def cmd_altri(update, context): await update.message.reply_text("⬇️ Altre stazioni:", reply_markup=keyboard_altri)
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
        "/test DDMMYYYY HHMM X - Test con 3 cicli (M, S, ML)\n"
        "/testfin - Disattiva modalità test\n"
        "/testgif - Invia GIF di prova e lo cancella dopo 1 minuto\n"
        "/refrescar - Aggiorna i messaggi temporanei (solo dopo il ciclo)\n\n"
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
# COMANDO TEST GIF
# ============================================================================
async def cmd_testgif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/montepo-fontana.gif"
    text_msg = (
        "🚆 Prossimi treni a Nesima\n\n"
        "🔺 Per Monte Po: Passa tra 3 minuti.\n"
        "   (il treno si trova attualmente a Monte Po)"
    )
    # Borrar mensajes anteriores del bot antes de enviar el nuevo GIF
    await clear_previous_bot_messages(update, context)
    text_msg_obj = await update.message.reply_text(text_msg)
    context.chat_data['bot_messages'].append(text_msg_obj.message_id)
    gif_message = await update.message.reply_animation(animation=gif_url)
    context.chat_data['bot_messages'].append(gif_message.message_id)
    await asyncio.sleep(60)
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=gif_message.message_id)
        # También lo quitamos de la lista
        if gif_message.message_id in context.chat_data['bot_messages']:
            context.chat_data['bot_messages'].remove(gif_message.message_id)
    except Exception as e:
        print(f"Error al borrar el GIF: {e}")

# ============================================================================
# COMANDOS TEST (2 y 3 argumentos) - sin cambios, pero añadimos limpieza al inicio de send_station_response ya lo hace
# ============================================================================
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
            simulated = CATANIA_TZ.localize(datetime(year, month, day, hour, minute))
        except Exception as e:
            await update.message.reply_text(f"Data non valida: {e}")
            return
        context.chat_data['test_time'] = simulated
        await send_station_response(update, context, station, return_to_main=False)
        return
    await update.message.reply_text("Comando non riconosciuto. Usa /test DDMMYYYY HHMM o /test DDMMYYYY HHMM X")

async def testfin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data and 'test_time' in context.chat_data:
        del context.chat_data['test_time']
        await update.message.reply_text("✅ Modalità test disattivata. Ora reale ripristinata.")
    else:
        await update.message.reply_text("⚠️ Nessuna modalità test attiva.")
