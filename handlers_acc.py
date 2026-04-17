import asyncio
import time as time_module
import unicodedata
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

logger = logging.getLogger(__name__)

# ============================================================================
# TECLADO PARA MODO NORMAL (sin emojis) - se usará al salir del modo acces
# ============================================================================
keyboard_main_acc = ReplyKeyboardMarkup(
    [["Monte Po", "Altri", "Stesicoro"]],
    resize_keyboard=True, one_time_keyboard=False
)

# ============================================================================
# INFORMACIÓN DETALLADA DE CADA ESTACIÓN (para el mensaje1)
# ============================================================================
INFO_ESTACIONES = {
    "stesicoro": (
        "Informazioni sulla stazione Stesicoro.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, arrivano i treni da Monte Po, e termina la corsa. Alla testa del treno si trovano le uscite per: Corso Sicilia, Piazza Stesicoro e Via Etnea. Sul marciapiede 2, si fermano i treni e iniziano il viaggio di ritorno in direzione Monte Po. Alla coda del treno si trovano le uscite per: Corso Italia e Piazza della Repubblica. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono diretto alla strada, senza passare per Biglietteria."
    ),
    "giovanni": (
        "Informazioni sulla stazione Giovanni XXIII.\n\n"
        "La stazione è dotata di Percorso tattile, Iscrizione in Braille sul corrimano delle scale, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Piazza Papa Giovanni XXIII e Viale Africa. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Archimede, Viale della Libertà e Stazione di Trenitalia \"Catania Centrale\". Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "galatea": (
        "Informazioni sulla stazione Galatea.\n\n"
        "La stazione è dotata di Percorso tattile e scale mobili.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Jonio, Via Pasubio e via Palmanova. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Piazza Galatea, Viale Africa e Via Messina."
    ),
    "italia": (
        "Informazioni sulla stazione Italia.\n\n"
        "La stazione è dotata di Percorso tattile e scale mobili.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Firenze, Via Ramondetta e Via Oliveto Scammacca. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Viale Vittorio Veneto e Corso Italia."
    ),
    "giuffrida": (
        "Informazioni sulla stazione Giuffrida.\n\n"
        "La stazione è dotata di Percorso tattile e scale mobili.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Guardia della Carvana e Piazza Abraham Lincoln. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Caronda e Via Vincenzo Giuffrida."
    ),
    "borgo": (
        "Informazioni sulla stazione Borgo.\n\n"
        "La stazione è dotata di Percorso tattile e scale mobili.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Empedocle e Via Etnea. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: I treni della FCE, Via Signorelli e Via Caronda."
    ),
    "milo": (
        "Informazioni sulla stazione Milo.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bronte e Viale Fleming. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bronte e Viale Fleming. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "cibali": (
        "Informazioni sulla stazione Cibali.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio, Angelo Massimino. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "sannullo": (
        "Informazioni sulla stazione San Nullo.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "nesima": (
        "Informazioni sulla stazione Nesima.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Lorenzo Bolano e Via Filippo Eredia. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trova l'uscita per: Viale Lorenzo Bolano. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "fontana": (
        "Informazioni sulla stazione Fontana.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili e Ascensore.\n\n"
        "Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Via Felice Fontana. Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Felice Fontana e l'Ospedale Garibaldi-Nesima. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
    ),
    "montepo": (
        "Informazioni sulla stazione Monte Po.\n\n"
        "La stazione è dotata di Percorso tattile, scale mobili, Ascensore e Mappa della stazione in Braille accanto ai tornelli d'accesso.\n\n"
        "Sul marciapiede 1, si fermano i treni e iniziano il viaggio di ritorno in direzione Stesicoro. Alla testa e alla coda del treno si trovano le uscite per: Corso Carlo Marx-Misterbianco. Il marciapiede 2 è inoperativo al momento. Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono l'uscita dei tornelli e verso un nuovo ascensore verso Piazza Carlo Marx."
    ),
}

# ============================================================================
# PALABRAS CLAVE (calles cercanas) para cada estación
# ============================================================================
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

# ============================================================================
# FUNCIÓN PARA ELIMINAR "[]" Y EMojis
# ============================================================================
def clean_text_for_display(text: str) -> str:
    if not text:
        return None
    text = text.replace("[]", "").replace("[ ]", "")
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA70-\U0001FAFF"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    text = ' '.join(text.split())
    if not text or text == "":
        return None
    return text

def remove_emojis(text: str) -> str:
    if not text:
        return text
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA70-\U0001FAFF"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

# ============================================================================
# BUS NESIMA → HUMANITAS (sin emojis)
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
            return f"Prossimo autobus per Humanitas alle {hora_str}"
    return ""

# ============================================================================
# BUS GRATUITO MONTE PO → MISTERBIANCO (sin emojis)
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
            return f"Autobus gratuito per Misterbianco alle {hora_str}"
    return ""

# ============================================================================
# CONSTRUCCIÓN DE MENSAJES TEMPORALES (msg2 y msg3) sin emojis
# ============================================================================
def build_temporary_messages(now: datetime, estacion_key: str):
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    closing_msg = get_closing_message(estacion_key, now)
    closing_msg = remove_emojis(closing_msg)

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
            line = f"Per Monte Po: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"Per Monte Po: Passa tra {time_str}, alle {paso_st.strftime('%H:%M')}.\n"
            else:
                line = f"Per Monte Po: Passa tra {time_str}.\n"
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
        msg2 += f"Per Monte Po: nessun treno in arrivo al momento.\n"

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
            line = f"Per Stesicoro: treno in arrivo.\n"
        else:
            if mins > SHORT_TIME_THRESHOLD:
                line = f"Per Stesicoro: Passa tra {time_str}, alle {paso_mp.strftime('%H:%M')}.\n"
            else:
                line = f"Per Stesicoro: Passa tra {time_str}.\n"
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
        msg3 = f"Per Stesicoro: nessun treno in arrivo al momento.\n"
        tiempo_restante_st = 9999

    msg2 = remove_emojis(msg2)
    msg3 = remove_emojis(msg3)
    return msg2, msg3, current_station_key_mp, tiempo_restante_mp, current_station_key_st, tiempo_restante_st, mins_mp, mins_st

# ============================================================================
# FUNCIONES DE ENVÍO (solo texto, sin botones)
# ============================================================================
async def send_text_only(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str):
    msg = clean_text_for_display(msg)
    if msg is None:
        return None
    result = await update.message.reply_text(msg, parse_mode='Markdown')
    if result:
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(result.message_id)
    return result

async def send_message_2(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str):
    return await send_text_only(update, context, msg)

async def send_message_3(update: Update, context: ContextTypes.DEFAULT_TYPE, msg: str, current_station_key: str, tiempo_restante: int, mins: int, estacion_key: str, reply_markup=None):
    if "nessun treno in arrivo al momento" in msg:
        msg = msg.replace("nessun treno in arrivo al momento", "Il servizio è terminato")
    return await send_text_only(update, context, msg)

# ============================================================================
# FUNCIÓN PARA ENVIAR msg2, msg3 y también msg4 (el mensaje fijo)
# ============================================================================
async def send_messages_2_3_and_4(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, now: datetime, simulated: bool = False):
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    msg2_obj = await send_message_2(update, context, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.1)
    
    msg3_obj = await send_message_3(update, context, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=None)
    
    msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
    msg4_obj = await send_text_only(update, context, msg4_text)
    
    ids = []
    if msg2_obj:
        ids.append(msg2_obj.message_id)
    if msg3_obj:
        ids.append(msg3_obj.message_id)
    if msg4_obj:
        ids.append(msg4_obj.message_id)
    
    if ids:
        if 'refresh_msg_ids' not in context.chat_data:
            context.chat_data['refresh_msg_ids'] = []
        context.chat_data['refresh_msg_ids'].extend(ids)
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].extend(ids)
    
    return tuple(ids) if ids else None

# ============================================================================
# FUNCIÓN DE LIMPIEZA Y REINICIO AUTOMÁTICO
# ============================================================================
async def auto_clean_and_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(20 * 60)
    chat_id = update.effective_chat.id
    
    all_ids = context.chat_data.get('all_msg_ids', [])
    welcome_id = context.chat_data.get('welcome_msg_id')
    
    for mid in all_ids:
        if mid == welcome_id:
            continue
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    
    acces_mode = context.chat_data.get('acces_mode', False)
    context.chat_data.clear()
    if acces_mode:
        context.chat_data['acces_mode'] = True
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
# REFRESCAR SOLO MENSAJES (borra los antiguos y envía nuevos, sin botón)
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
    
    new_ids = await send_messages_2_3_and_4(update, context, estacion_key, now, simulated is not None)
    if new_ids:
        context.chat_data['refresh_msg_ids'] = list(new_ids)
    schedule_cleanup(update, context)

# ============================================================================
# CALLBACKS (vacíos porque no hay botones)
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def aggiornare_cabecera_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

# ============================================================================
# FUNCIÓN AUXILIAR PARA ENVIAR RESPUESTA DE CABECERA (sin botón)
# ============================================================================
async def send_header_response(chat_id, context, estacion_key, is_update=False):
    try:
        simulated = context.chat_data.get('test_time')
        if simulated:
            if simulated.tzinfo is None:
                simulated = CATANIA_TZ.localize(simulated)
            now = simulated
        else:
            now = datetime.now(CATANIA_TZ)
        
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open, special_closing_msg = is_metro_closed(now, station)
        special_closing_msg = remove_emojis(special_closing_msg)
        
        if not is_update:
            base_url = STATION_IMAGE.get(estacion_key)
            if base_url:
                img_url = base_url.replace("st_", "st_a").replace(".jpg", ".png")
            else:
                img_url = None
            info_text = INFO_ESTACIONES.get(estacion_key, f"Informazioni sulla stazione {NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())}.")
            if img_url:
                cache_buster = int(time_module.time())
                img_url = f"{img_url}?v={cache_buster}"
                msg1 = await context.bot.send_photo(chat_id=chat_id, photo=img_url, caption=info_text, parse_mode='Markdown')
            else:
                msg1 = await context.bot.send_message(chat_id=chat_id, text=info_text, parse_mode='Markdown')
            context.chat_data['main_msg_id'] = msg1.message_id
            if 'all_msg_ids' not in context.chat_data:
                context.chat_data['all_msg_ids'] = []
            context.chat_data['all_msg_ids'].append(msg1.message_id)
        
        if closed:
            if next_open.date() > now.date():
                msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento. Riaprirà domani alle {next_open.strftime('%H:%M')}."
            else:
                mins_to_open = int((next_open - now).total_seconds() // 60)
                if mins_to_open <= 60:
                    first_train, _, _, has_first = get_next_departure(station, now)
                    if not has_first:
                        first_train, _, _, _ = get_next_departure(station, now + timedelta(days=1))
                    station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
                    msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
                else:
                    msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento.\nRiaprirà alle {next_open.strftime('%H:%M')}."
            msg = remove_emojis(msg)
            msg2 = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            if 'all_msg_ids' not in context.chat_data:
                context.chat_data['all_msg_ids'] = []
            context.chat_data['all_msg_ids'].append(msg2.message_id)
            msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
            msg4 = await context.bot.send_message(chat_id=chat_id, text=msg4_text, parse_mode='Markdown')
            if 'all_msg_ids' not in context.chat_data:
                context.chat_data['all_msg_ids'] = []
            context.chat_data['all_msg_ids'].append(msg4.message_id)
            return
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            close_h, close_m = get_closing_time(now, station)
            msg = f"Non ci sono più treni oggi. Il servizio termina alle {close_h:02d}:{close_m:02d}."
            msg = remove_emojis(msg)
            msg2 = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            if 'all_msg_ids' not in context.chat_data:
                context.chat_data['all_msg_ids'] = []
            context.chat_data['all_msg_ids'].append(msg2.message_id)
            msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
            msg4 = await context.bot.send_message(chat_id=chat_id, text=msg4_text, parse_mode='Markdown')
            if 'all_msg_ids' not in context.chat_data:
                context.chat_data['all_msg_ids'] = []
            context.chat_data['all_msg_ids'].append(msg4.message_id)
            return
        
        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        remaining = next_dep - now
        mins_rest = int(remaining.total_seconds() // 60)
        secs_rest = int(remaining.total_seconds() % 60)
        total_seconds_rest = int(remaining.total_seconds())
        time_str_rest = format_time(mins_rest, secs_rest)
        
        if mins_rest <= 4:
            msg = f"Il treno è in binario. Partirà tra {time_str_rest}."
        else:
            time_str = format_time(minutes, seconds)
            if minutes < SHORT_TIME_THRESHOLD:
                msg = f"Prossimo treno per {dest} parte tra {time_str}."
            else:
                msg = f"Prossimo treno per {dest} parte tra {time_str}, alle {next_dep.strftime('%H:%M')}."
        
        if mins_rest <= 1:
            next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
            if has2:
                msg += f"\n\nIl prossimo treno successivo partirà tra {format_time(min2, sec2)}, alle {next2.strftime('%H:%M')}."
            else:
                msg += f"\n\nQuesto è l'ultimo treno della giornata."
        
        last_msg = get_last_train_message(now)
        if last_msg and not is_sant_agata(now):
            if "01:00" in last_msg:
                last_msg = last_msg.replace("📌", "")
            elif "22:30" in last_msg:
                last_msg = last_msg.replace("📌", "")
            last_msg = remove_emojis(last_msg)
            msg += f"\n\n{last_msg}"
        
        if estacion_key == "montepo":
            bus_text = get_bus_message_montepo_advanced(now)
            if bus_text:
                bus_text = remove_emojis(bus_text)
                msg += f"\n\n{bus_text}"
        
        msg = remove_emojis(msg)
        msg2 = await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg2.message_id)
        
        msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
        msg4 = await context.bot.send_message(chat_id=chat_id, text=msg4_text, parse_mode='Markdown')
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg4.message_id)
    
    except Exception as e:
        logger.error(f"Error en send_header_response: {e}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"Errore nel recupero informazioni: {str(e)}")
        except:
            pass

# ============================================================================
# RESPUESTA PRINCIPAL (foto st_a...png + msg2/msg3 + msg4, sin botón)
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
    test_indicator = "[TEST MODE] " if simulated else ""

    if estacion_key in ["montepo", "stesicoro"]:
        await send_header_response(update.message.chat_id, context, estacion_key, is_update=False)
        schedule_cleanup(update, context)
        return

    closed, next_open, special_closing_msg = is_metro_closed(now, "Montepo")
    special_closing_msg = remove_emojis(special_closing_msg)
    if closed:
        if next_open.date() > now.date():
            msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento. Riaprirà domani alle {next_open.strftime('%H:%M')}."
        else:
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure("Montepo", now)
                if not has_first:
                    first_train, _, _, _ = get_next_departure("Montepo", now + timedelta(days=1))
                msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento. Il primo treno da Monte Po partirà alle {first_train.strftime('%H:%M')}."
            else:
                msg = f"{special_closing_msg}\nLa metropolitana è chiusa in questo momento.\nRiaprirà alle {next_open.strftime('%H:%M')}."
        msg = remove_emojis(msg)
        base_url = STATION_IMAGE.get(estacion_key)
        if base_url:
            img_url = base_url.replace("st_", "st_a").replace(".jpg", ".png")
            cache_buster = int(time_module.time())
            img_url = f"{img_url}?v={cache_buster}"
            msg1 = await update.message.reply_photo(photo=img_url, caption=msg)
        else:
            msg1 = await update.message.reply_text(msg)
        context.chat_data['main_msg_id'] = msg1.message_id
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg1.message_id)
        
        msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
        msg4 = await update.message.reply_text(msg4_text)
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg4.message_id)
        
        schedule_cleanup(update, context)
        return

    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    
    # Obtener la información detallada de la estación (sin mensaje de último tren)
    info_text = INFO_ESTACIONES.get(estacion_key, f"Informazioni sulla stazione {nombre}.")
    if test_indicator:
        info_text = f"{test_indicator}{info_text}"
    
    base_url = STATION_IMAGE.get(estacion_key)
    img_station = base_url.replace("st_", "st_a").replace(".jpg", ".png") if base_url else None
    
    if img_station:
        cache_buster = int(time_module.time())
        img_station = f"{img_station}?v={cache_buster}"
        msg1 = await update.message.reply_photo(photo=img_station, caption=info_text)
    else:
        msg1 = await update.message.reply_text(info_text)
    context.chat_data['main_msg_id'] = msg1.message_id
    if 'all_msg_ids' not in context.chat_data:
        context.chat_data['all_msg_ids'] = []
    context.chat_data['all_msg_ids'].append(msg1.message_id)

    ids = await send_messages_2_3_and_4(update, context, estacion_key, now, simulated is not None)
    if ids:
        context.chat_data['refresh_msg_ids'] = list(ids)
    schedule_cleanup(update, context)

# ============================================================================
# FUNCIÓN PARA ACTIVAR EL MODO ACCES (se llama desde metro_bot.py)
# ============================================================================
async def activate_acces_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo accesibilidad, oculta el teclado y muestra el mensaje4."""
    context.chat_data['acces_mode'] = True
    msg4_text = ("Scegli la stazione che vuoi controllare o scrive la stessa stazione per aggiornarla: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro. Per uscire dalla modalità accessibilità scrivi USCIRE")
    # Enviar mensaje con eliminación del teclado
    await update.message.reply_text(msg4_text, reply_markup=ReplyKeyboardRemove())
    # Enviar un segundo mensaje vacío con remove para asegurar (opcional)
    # await update.message.reply_text("", reply_markup=ReplyKeyboardRemove())

# ============================================================================
# MANEJADOR PRINCIPAL DE TEXTO PARA EL MODO ACCES
# ============================================================================
async def normal_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    
    if texto.lower() == "uscire":
        context.chat_data['acces_mode'] = False
        # Restaurar teclado principal (sin emojis)
        await update.message.reply_text("Uscito dalla modalità accessibilità. Per riattivarla, scrivi 'acces'.", reply_markup=keyboard_main_acc)
        return
    
    await process_station_request(update, context, texto)

# ============================================================================
# PROCESAMIENTO DE SOLICITUD DE ESTACIÓN (modo nonna simplificado)
# ============================================================================
async def process_station_request(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    texto_norm = unicodedata.normalize('NFKD', texto.lower()).encode('ASCII', 'ignore').decode('ASCII')
    texto_limpio = ' '.join(texto_norm.split())
    palabras = texto_limpio.split()
    
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
    
    mejor_clave = None
    for kw_norm, station in KEYWORDS_NORM.items():
        if kw_norm in texto_limpio:
            mejor_clave = station
            break
    if not mejor_clave:
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
                        mejor_clave = station
                        break
                else:
                    if dist <= 1:
                        mejor_clave = station
                        break
            if mejor_clave:
                break
    
    if mejor_clave:
        await send_station_response(update, context, mejor_clave, return_to_main=True)
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
    
    if not matches:
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
        await send_station_response(update, context, mejor_clave, return_to_main=True)
        return
    
    await update.message.reply_text(
        "Stazione non riconosciuta. Le stazioni disponibili sono: " +
        ", ".join(NOMBRE_MOSTRAR.values()) + ".\nPuoi anche usare alias come 'Misterbianco' (Monte Po) o 'Humanitas' (Nesima).\n\n"
        "Per uscire dalla modalità accessibilità, scrivi USCIRE."
    )
