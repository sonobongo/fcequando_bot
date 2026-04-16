import asyncio
import time as time_module
import unicodedata
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

# ============================================================================
# DESCRIPCIONES DE ESTACIONES (texto plano, sin emojis ni asteriscos)
# ============================================================================
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

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def clean_for_accessibility(text: str) -> str:
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

def get_station_by_name(text: str) -> tuple:
    """Compara el texto con el nombre de la estación (ignorando mayúsculas, tildes y espacios)."""
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    for key, nombre in NOMBRE_MOSTRAR.items():
        nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ASCII', 'ignore').decode('ASCII')
        if text == nombre_norm:
            return key, nombre
    return None, None

# ============================================================================
# FUNCIONES PARA ENVIAR HORARIOS (msg2 y msg3) CON BOTÓN
# ============================================================================
async def acc_send_message_2(update: Update, msg: str):
    """Envía el mensaje 2 (hacia Monte Po) sin botón."""
    msg_clean = clean_for_accessibility(msg) or "Nessun treno in arrivo verso Monte Po."
    await update.message.reply_text(f"Prossimi treni verso Monte Po:\n{msg_clean}", parse_mode=None)

async def acc_send_message_3(update: Update, msg: str, estacion_key: str, reply_markup=None):
    """Envía el mensaje 3 (hacia Stesicoro) con botón opcional."""
    msg_clean = clean_for_accessibility(msg) or "Nessun treno in arrivo verso Stesicoro."
    await update.message.reply_text(f"Prossimi treni verso Stesicoro:\n{msg_clean}", parse_mode=None, reply_markup=reply_markup)

async def acc_send_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    """Envía los horarios (msg2 y msg3) y guarda los IDs para actualizarlos luego."""
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    
    # Enviar msg2 (sin botón)
    await acc_send_message_2(update, msg2)
    
    # Enviar msg3 con botón inline
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"acc_aggiornare_{estacion_key}")]
    ])
    await acc_send_message_3(update, msg3, estacion_key, reply_markup=keyboard_inline)

# ============================================================================
# FUNCIÓN PRINCIPAL PARA ENVIAR INFORMACIÓN DE ESTACIÓN (MODO ACCESIBLE)
# ============================================================================
async def acc_send_station_info(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    """Envía la información completa de una estación en modo accesibilidad."""
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    descripcion = DESCRIPCION_ESTACION.get(estacion_key, "Stazione accessibile.")
    
    # 0. Mensaje de introducción (sin foto)
    intro = f"Informazioni sulla stazione {nombre}.\n\n{descripcion}"
    await update.message.reply_text(intro, parse_mode=None)
    
    # 1. Foto de la estación (mensaje 1)
    nombre_imagen = nombre.replace(" ", "").replace("XXIII", "XXIII")
    if nombre_imagen == "SanNullo":
        nombre_imagen = "SanNullo"
    elif nombre_imagen == "GiovanniXXIII":
        nombre_imagen = "GiovanniXXIII"
    img_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_a{nombre_imagen}.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    await update.message.reply_photo(photo=img_url, caption=f"Stazione {nombre}", parse_mode=None)
    
    # 2. Horarios (msg2 y msg3 con botón)
    await acc_send_horarios(update, context, estacion_key)
    
    # 3. Mensaje 4: lista de estaciones
    lista_estaciones = ", ".join(NOMBRE_MOSTRAR.values())
    mensaje4 = (
        "Scegli un'altra stazione scrivendo:\n"
        f"{lista_estaciones}\n\n"
        "Per uscire dalla modalità accessibilità, scrivi /uscire."
    )
    await update.message.reply_text(mensaje4, parse_mode=None)

# ============================================================================
# CALLBACK PARA ACTUALIZAR SOLO LOS HORARIOS (msg2 y msg3) - SIN BORRAR NADA
# ============================================================================
async def acc_aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[2]  # "acc_aggiornare_fontana"
    
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    
    # Enviar nuevos mensajes de horarios (sin borrar los anteriores)
    await query.message.reply_text(f"Prossimi treni verso Monte Po:\n{clean_for_accessibility(msg2) or 'Nessun treno in arrivo verso Monte Po.'}", parse_mode=None)
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"acc_aggiornare_{estacion_key}")]
    ])
    await query.message.reply_text(f"Prossimi treni verso Stesicoro:\n{clean_for_accessibility(msg3) or 'Nessun treno in arrivo verso Stesicoro.'}", parse_mode=None, reply_markup=keyboard_inline)

# ============================================================================
# MANEJADOR DE TEXTO PARA MODO ACCESIBILIDAD
# ============================================================================
async def acc_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto cuando el modo accesibilidad está activo."""
    if not context.chat_data.get('accessibility_mode', False):
        return
    
    texto = update.message.text.strip()
    # Salir si el usuario escribe "Uscire" o "/uscire"
    if texto.lower() in ["/uscire", "uscire", "exit", "salir"]:
        await cmd_uscire(update, context)
        return
    
    # Buscar estación por nombre exacto (ignorando mayúsculas y tildes)
    estacion_key, nombre_estacion = get_station_by_name(texto)
    if estacion_key:
        await update.message.reply_text(f"Hai scelto {nombre_estacion}. Ecco le informazioni:")
        await acc_send_station_info(update, context, estacion_key)
    else:
        lista = ", ".join(NOMBRE_MOSTRAR.values())
        await update.message.reply_text(
            f"Stazione non riconosciuta. Le stazioni disponibili sono:\n{lista}\n\nPer uscire, scrivi 'Uscire'."
        )

# ============================================================================
# COMANDO PARA ACTIVAR MODO ACCESIBILIDAD
# ============================================================================
async def cmd_accesibilidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo accesibilidad y muestra la información de Monte Po por defecto."""
    context.chat_data['accessibility_mode'] = True
    await update.message.reply_text(
        "♿ Modalità accessibilità attivata.\n\n"
        "Scrivi il nome della stazione che desideri consultare.\n"
        "Esempio: 'Monte Po' o 'Galatea'.\n\n"
        "Per uscire, scrivi 'Uscire'.",
        parse_mode=None
    )
    # Mostrar información de Monte Po por defecto
    await acc_send_station_info(update, context, "montepo")

# ============================================================================
# COMANDO PARA SALIR DEL MODO ACCESIBILIDAD
# ============================================================================
async def cmd_uscire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el modo accesibilidad y vuelve al modo normal."""
    if context.chat_data.get('accessibility_mode', False):
        context.chat_data['accessibility_mode'] = False
        await update.message.reply_text("✅ Modalità accessibilità disattivata. Sei tornato al menu principale.")
    else:
        await update.message.reply_text("⚠️ Non sei in modalità accessibilità.")

# ============================================================================
# ACTIVACIÓN RÁPIDA (opcional, puedes comentarla si no la quieres)
# ============================================================================
async def acc_try_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Si el texto empieza con 'acces' (case-insensitive) y la accesibilidad no está activa, la activa."""
    if context.chat_data.get('accessibility_mode', False):
        return
    text = update.message.text.strip().lower()
    if text.startswith("acces"):
        await cmd_accesibilidad(update, context)
