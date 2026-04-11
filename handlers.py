import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from horarios_logic import *

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
# CONSTRUCCIÓN DE MENSAJES TEMPORALES
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str):
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    closing_msg = get_closing_message(estacion_key, now)

    # Mensaje 2 (Monte Po)
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
        estaciones_localizacion_montepo = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "fontana"]
        if estacion_key in estaciones_localizacion_montepo and 2 <= mins <= 10:
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

    # Mensaje 3 (Stesicoro)
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
        estaciones_localizacion_stesicoro = ["nesima", "sannullo", "cibali", "milo", "borgo", "giuffrida", "italia", "galatea", "giovanni"]
        if estacion_key in estaciones_localizacion_stesicoro and 2 <= mins <= 10:
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
# FUNCIÓN DE IMAGEN POR DEFECTO (con prioridad a tiempo <= 90)
# ============================================================================
async def send_with_default_image(update: Update, msg: str, current_station_key: str, tiempo_restante: int, direction: str, send_image: bool = True):
    """
    Envía un mensaje con imagen si send_image es True, según reglas:
    - Si tiempo_restante <= 90 -> ruta_trenoarriva.png
    - Si current_station_key is None -> ruta_default.png
    - Si no -> solo texto
    Si send_image es False, envía solo texto.
    """
    if not send_image:
        return await update.message.reply_text(msg, parse_mode='Markdown')
    
    if tiempo_restante is not None and tiempo_restante <= 90:
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_trenoarriva.png"
        cache_buster = int(time_module.time())
        img_url = f"{img_url}?v={cache_buster}"
        try:
            print(f"DEBUG: Enviando imagen 'treno in arrivo' para {direction} (tiempo={tiempo_restante}s): {img_url}")
            return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Error enviando imagen trenoarriva: {e}")
            return await update.message.reply_text(msg, parse_mode='Markdown')
    elif current_station_key is None:
        img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_default.png"
        cache_buster = int(time_module.time())
        img_url = f"{img_url}?v={cache_buster}"
        try:
            print(f"DEBUG: Enviando imagen 'default' para {direction} (sin localización): {img_url}")
            return await update.message.reply_photo(photo=img_url, caption=msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Error enviando imagen default: {e}")
            return await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        return await update.message.reply_text(msg, parse_mode='Markdown')

# ============================================================================
# FUNCIONES DE ENVÍO PARA MILO (GIF animado para Monte Po, PNG estático para Stesicoro)
# ============================================================================
async def send_msg2_milo(update: Update, msg2: str, current_station_key_mp: str, tiempo_restante_mp: int):
    """Para Milo: intenta enviar GIF animado (Monte Po) si cumple condiciones, sino imagen por defecto."""
    if current_station_key_mp and tiempo_restante_mp is not None and tiempo_restante_mp > 90:
        cache_buster = int(time_module.time())
        gif_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key_mp}.gif?v={cache_buster}"
        try:
            print(f"DEBUG: Enviando GIF animado para Milo (Monte Po) hacia {current_station_key_mp}: {gif_url}")
            return await update.message.reply_animation(animation=gif_url, caption=msg2, parse_mode='Markdown')
        except Exception as e:
            print(f"Error enviando GIF Milo Monte Po: {e}")
            # Si falla el GIF, se usa imagen por defecto (con send_image=True)
            return await send_with_default_image(update, msg2, current_station_key_mp, tiempo_restante_mp, "Monte Po", send_image=True)
    else:
        # Si no cumple condiciones para GIF, se usa imagen por defecto
        return await send_with_default_image(update, msg2, current_station_key_mp, tiempo_restante_mp, "Monte Po", send_image=True)

async def send_msg3_milo(update: Update, msg3: str, current_station_key_st: str, tiempo_restante_st: int):
    """Para Milo: intenta enviar PNG estático (Stesicoro) si cumple condiciones, sino imagen por defecto."""
    if current_station_key_st and tiempo_restante_st is not None and tiempo_restante_st > 90:
        cache_buster = int(time_module.time())
        png_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_{current_station_key_st}_statico.png?v={cache_buster}"
        try:
            print(f"DEBUG: Enviando PNG estático para Milo (Stesicoro) desde {current_station_key_st}: {png_url}")
            return await update.message.reply_photo(photo=png_url, caption=msg3, parse_mode='Markdown')
        except Exception as e:
            print(f"Error enviando PNG Milo Stesicoro: {e}")
            return await send_with_default_image(update, msg3, current_station_key_st, tiempo_restante_st, "Stesicoro", send_image=True)
    else:
        return await send_with_default_image(update, msg3, current_station_key_st, tiempo_restante_st, "Stesicoro", send_image=True)

# ============================================================================
# FUNCIONES DE ENVÍO PARA OTRAS ESTACIONES (solo imágenes por defecto)
# ============================================================================
async def send_msg2_other(update: Update, msg2: str, current_station_key_mp: str, tiempo_restante_mp: int, send_image: bool = True):
    return await send_with_default_image(update, msg2, current_station_key_mp, tiempo_restante_mp, "Monte Po", send_image)

async def send_msg3_other(update: Update, msg3: str, current_station_key_st: str, tiempo_restante_st: int, send_image: bool = True):
    return await send_with_default_image(update, msg3, current_station_key_st, tiempo_restante_st, "Stesicoro", send_image)

# ============================================================================
# TAREA DE ACTUALIZACIÓN AUTOMÁTICA (35, 45, 55 segundos)
# ============================================================================
async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    print(f"DEBUG: auto_refresh_loop iniciada para {estacion_key}")
    tiempos_espera = [35, 45, 55]
    try:
        for idx, espera in enumerate(tiempos_espera):
            await asyncio.sleep(espera)
            if context.chat_data.get('cancel_refresh', False):
                break
            # Borrar mensajes anteriores
            msg_ids = context.chat_data.get('refresh_msg_ids')
            if msg_ids:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_ids[0])
                except:
                    pass
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_ids[1])
                except:
                    pass
            now = simulated_now if (use_simulated and simulated_now) else datetime.now()
            msg2, msg3, key_mp, time_mp, key_st, time_st = build_temporary_messages(now, estacion_key)
            
            if estacion_key == "milo":
                # Para Milo, las funciones ya deciden internamente si enviar imagen o GIF
                msg2_obj = await send_msg2_milo(update, msg2, key_mp, time_mp)
                await asyncio.sleep(0.5)
                msg3_obj = await send_msg3_milo(update, msg3, key_st, time_st)
            else:
                # Para otras estaciones, determinar si ambas usarían la misma imagen default
                # Calcular si msg2 y msg3 usarían ruta_default (sin localización y tiempo>90)
                use_default_mp = (time_mp is not None and time_mp > 90 and key_mp is None)
                use_default_st = (time_st is not None and time_st > 90 and key_st is None)
                # También considerar trenoarriva (tiempo <=90) -> entonces no es default
                if time_mp is not None and time_mp <= 90:
                    use_default_mp = False
                if time_st is not None and time_st <= 90:
                    use_default_st = False
                
                # Si ambos usarían la imagen default, solo enviamos imagen en el mensaje 2, y mensaje 3 sin imagen
                if use_default_mp and use_default_st:
                    msg2_obj = await send_msg2_other(update, msg2, key_mp, time_mp, send_image=True)
                    await asyncio.sleep(0.5)
                    msg3_obj = await send_msg3_other(update, msg3, key_st, time_st, send_image=False)
                else:
                    msg2_obj = await send_msg2_other(update, msg2, key_mp, time_mp, send_image=True)
                    await asyncio.sleep(0.5)
                    msg3_obj = await send_msg3_other(update, msg3, key_st, time_st, send_image=True)
            
            context.chat_data['refresh_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id)
    except asyncio.CancelledError:
        print("DEBUG: auto_refresh_loop cancelada")
        pass
    finally:
        context.chat_data['refresh_active'] = False
        context.chat_data.pop('refresh_task', None)
        context.chat_data.pop('cancel_refresh', None)
        print("DEBUG: auto_refresh_loop finalizada")

# ============================================================================
# RESPUESTA PRINCIPAL
# ============================================================================
async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, return_to_main: bool = True):
    print(f"DEBUG: send_station_response llamada para {estacion_key}")
    
    # Cancelar tarea anterior
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    context.chat_data['cancel_refresh'] = False
    
    simulated = context.chat_data.get('test_time') if context.chat_data else None
    if simulated:
        now = simulated
    else:
        now = datetime.now()
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

    # Cabeceras Monte Po y Stesicoro
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
            if "01:00" in last_msg:
                last_msg = last_msg.replace("📌", "🕐")
            elif "22:30" in last_msg:
                last_msg = last_msg.replace("📌", "🕙")
            msg += f"\n\n{last_msg}"
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

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    img_station = get_station_image(estacion_key, now)

    # Caption de la foto: título + mensaje de cierre
    last_msg = get_last_train_message(now)
    last_msg_text = ""
    if last_msg and not is_sant_agata(now):
        if "01:00" in last_msg:
            last_msg = last_msg.replace("📌", "🕐")
        elif "22:30" in last_msg:
            last_msg = last_msg.replace("📌", "🕙")
        last_msg_text = f"\n\n{last_msg}"
    permanent_caption = f"{test_indicator}🚇 Prossimi treni a {nombre}{last_msg_text}"
    
    if img_station:
        await update.message.reply_photo(photo=img_station, caption=permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    else:
        await update.message.reply_text(permanent_caption, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    print("DEBUG: Foto de estación enviada")

    # Obtener mensajes temporales
    msg2, msg3, key_mp, time_mp, key_st, time_st = build_temporary_messages(now, estacion_key)
    print(f"DEBUG: msg2 = {msg2[:50]}... | tiempo_mp={time_mp}, key_mp={key_mp}")
    print(f"DEBUG: msg3 = {msg3[:50]}... | tiempo_st={time_st}, key_st={key_st}")
    
    # Enviar según estación
    if estacion_key == "milo":
        msg2_obj = await send_msg2_milo(update, msg2, key_mp, time_mp)
        await asyncio.sleep(0.5)
        msg3_obj = await send_msg3_milo(update, msg3, key_st, time_st)
    else:
        # Determinar si ambas usarían la misma imagen default
        use_default_mp = (time_mp is not None and time_mp > 90 and key_mp is None)
        use_default_st = (time_st is not None and time_st > 90 and key_st is None)
        if time_mp is not None and time_mp <= 90:
            use_default_mp = False
        if time_st is not None and time_st <= 90:
            use_default_st = False
        
        if use_default_mp and use_default_st:
            # Solo enviamos imagen en el mensaje 2, el mensaje 3 sin imagen
            msg2_obj = await send_msg2_other(update, msg2, key_mp, time_mp, send_image=True)
            await asyncio.sleep(0.5)
            msg3_obj = await send_msg3_other(update, msg3, key_st, time_st, send_image=False)
        else:
            msg2_obj = await send_msg2_other(update, msg2, key_mp, time_mp, send_image=True)
            await asyncio.sleep(0.5)
            msg3_obj = await send_msg3_other(update, msg3, key_st, time_st, send_image=True)
    
    context.chat_data['refresh_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id)
    print(f"DEBUG: Mensajes 2 y 3 enviados. IDs: {msg2_obj.message_id}, {msg3_obj.message_id}")

    # Iniciar bucle de actualización
    context.chat_data['refresh_active'] = True
    task = asyncio.create_task(auto_refresh_loop(update, context, estacion_key, update.effective_chat.id, nombre, use_simulated=(simulated is not None), simulated_now=now if simulated else None))
    context.chat_data['refresh_task'] = task
    print(f"DEBUG: Tarea de refresco creada: {task}")

# ============================================================================
# MANEJADORES DE COMANDOS (sin cambios)
# ============================================================================
async def cancel_refresh_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE, coro, *args, **kwargs):
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    await coro(update, context, *args, **kwargs)

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

# Funciones originales
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
    now = datetime.now()
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
        "/test DDMMYYYY HHMM - Attiva modalità test\n"
        "/test DDMMYYYY HHMM X - Test con 3 cicli (M, S, ML)\n"
        "/testfin - Disattiva modalità test\n"
        "/testgif - Invia GIF di prova e lo cancella dopo 1 minuto\n\n"
        "Oppure premi i pulsanti.",
        reply_markup=keyboard_main
    )
async def handle_button(update, context):
    text = update.message.text
    print(f"DEBUG: Botón pulsado: '{text}'")
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
    gif_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/ruta_montepo_fontana.gif"
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

# ============================================================================
# COMANDOS TEST (2 y 3 argumentos)
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
            simulated = datetime(year, month, day, hour, minute)
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
            simulated = datetime(year, month, day, hour, minute)
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
