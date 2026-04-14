import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

# ============================================================================
# DESCRIPCIONES DE ESTACIONES (formato exacto que pediste)
# ============================================================================
DESCRIPCION_ESTACION = {
    "montepo": "· Prossimi treni a Monte Po: Stazione capolinea con ascensore e servizi igienici.",
    "stesicoro": "· Prossimi treni a Stesicoro: Stazione centrale con ascensore e collegamento autobus.",
    "fontana": "· Prossimi treni a Fontana: Informazioni sulla stazione Fontana.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Via Felice Fontana.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Felice Fontana e l'Ospedale Garibaldi-Nesima.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "nesima": "· Prossimi treni a Nesima: Informazioni sulla stazione Nesima.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Lorenzo Bolano e Via Filippo Eredia.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trova l'uscita per: Viale Lorenzo Bolano.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "sannullo": "· Prossimi treni a San Nullo: Informazioni sulla stazione San Nullo.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "cibali": "· Prossimi treni a Cibali: Informazioni sulla stazione Cibali.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio, Angelo Massimino.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "milo": "· Prossimi treni a Milo: Informazioni sulla stazione Milo.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bronte e Viale Fleming.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bronte e Viale Fleming.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "borgo": "· Prossimi treni a Borgo: Informazioni sulla stazione Borgo.\n\nLa stazione è dotata di pavimento podotattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Empedocle e Via Etnea.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: I treni della FCE, Via Signorelli e Via Caronda.",
    "giuffrida": "· Prossimi treni a Giuffrida: Informazioni sulla stazione Giuffrida.\n\nLa stazione è dotata di pavimento podotattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Guardia della Carvana e Piazza Abraham Lincoln.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Caronda e Via Vincenzo Giuffrida.",
    "italia": "· Prossimi treni a Italia: Informazioni sulla stazione Italia.\n\nLa stazione è dotata di pavimento podotattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Firenze, Via Ramondetta e Via Oliveto Scammacca.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Viale Vittorio Veneto e Corso Italia.",
    "galatea": "· Prossimi treni a Galatea: Informazioni sulla stazione Galatea.\n\nLa stazione è dotata di pavimento podotattile e scale mobili.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Jonio, Via Pasubio e via Palmanova.\nSul marciapiede 2 partono i treni in direzione Stesicoro.\nAlla testa del treno si trovano le uscite per: Piazza Galatea, Viale Africa e Via Messina.",
    "giovanni": "· Prossimi treni a Giovanni XXIII: Informazioni sulla stazione Giovanni XXIII.\n\nLa stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\nSul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Piazza Giovanni XXIII e Viale Africa.\nSul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Archimede, Viale della Libertà e Stazione di Trenitalia Catania Centrale.\nAl centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def clean_text(text: str) -> str:
    """Sustituye emojis por · y elimina formato Markdown."""
    replacements = {
        "🔺": "·", "🔻": "·", "🚇": "·", "🕐": "·", "🕙": "·", "📌": "·",
        "**": "", "*": "", "__": "", "`": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Eliminar espacios dobles
    return ' '.join(text.split())

async def acc_send_station_info(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    """Envía la información de una estación en modo accesibilidad."""
    # Obtener hora actual (simulada si está en test)
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    # Obtener mensajes 2 y 3 originales (con emojis y Markdown)
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_text(msg2)
    msg3_clean = clean_text(msg3)
    
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    descripcion = DESCRIPCION_ESTACION.get(estacion_key, f"· Prossimi treni a {nombre}: Stazione accessibile.")
    
    # 1. Enviar foto (sin caption o con el nombre)
    nombre_imagen = nombre.replace(" ", "").replace("XXIII", "XXIII")
    if nombre_imagen == "SanNullo":
        nombre_imagen = "SanNullo"
    elif nombre_imagen == "GiovanniXXIII":
        nombre_imagen = "GiovanniXXIII"
    img_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_a{nombre_imagen}.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    await update.message.reply_photo(photo=img_url, caption=f"Stazione {nombre}", parse_mode=None)
    
    # 2. Enviar descripción
    await update.message.reply_text(descripcion, parse_mode=None)
    
    # 3. Enviar mensaje 2
    msg2_obj = await update.message.reply_text(msg2_clean, parse_mode=None)
    
    # 4. Enviar mensaje 3 con botón inline
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("· Aggiornare", callback_data=f"acc_aggiornare_{estacion_key}")]
    ])
    msg3_obj = await update.message.reply_text(msg3_clean, parse_mode=None, reply_markup=keyboard_inline)
    
    # 5. Enviar mensaje 4 (lista de comandos)
    lista_comandos = (
        "Scegli la stazione che desideri consultare:\n"
        "/aMontepo, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, "
        "/aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni, /aStesicoro"
    )
    msg4_obj = await update.message.reply_text(lista_comandos, parse_mode=None)
    
    # Guardar IDs de los mensajes 2,3,4 para poder refrescarlos
    context.chat_data['acc_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id, msg4_obj.message_id)
    context.chat_data['acc_last_station'] = estacion_key

async def acc_aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback del botón '· Aggiornare' (refresca solo mensajes 2,3,4)."""
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[2]  # formato "acc_aggiornare_fontana"
    
    # Borrar mensajes anteriores (2,3,4)
    msg_ids = context.chat_data.get('acc_msg_ids')
    if msg_ids:
        for mid in msg_ids:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('acc_msg_ids', None)
    
    # Obtener hora actual
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    # Generar nuevos mensajes 2 y 3
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_text(msg2)
    msg3_clean = clean_text(msg3)
    
    # Enviar nuevos mensajes 2,3,4
    msg2_obj = await query.message.reply_text(msg2_clean, parse_mode=None)
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("· Aggiornare", callback_data=f"acc_aggiornare_{estacion_key}")]
    ])
    msg3_obj = await query.message.reply_text(msg3_clean, parse_mode=None, reply_markup=keyboard_inline)
    
    lista_comandos = (
        "Scegli la stazione che desideri consultare:\n"
        "/aMontepo, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, "
        "/aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni, /aStesicoro"
    )
    msg4_obj = await query.message.reply_text(lista_comandos, parse_mode=None)
    
    # Guardar nuevos IDs
    context.chat_data['acc_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id, msg4_obj.message_id)

# ============================================================================
# COMANDOS DEL MODO ACCESIBILIDAD
# ============================================================================
async def cmd_accesibilidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa o desactiva el modo accesibilidad (toggle)."""
    if context.chat_data.get('accessibility_mode', False):
        # Desactivar
        context.chat_data['accessibility_mode'] = False
        context.chat_data.pop('acc_msg_ids', None)
        context.chat_data.pop('acc_last_station', None)
        await update.message.reply_text("✅ Modalità accessibilità disattivata. Puoi tornare a usare i pulsanti normali.")
    else:
        # Activar
        context.chat_data['accessibility_mode'] = True
        await update.message.reply_text(
            "♿ Modalità accessibilità attivata.\n\n"
            "Scegli la stazione che desideri consultare:\n"
            "/aMontepo, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, /aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni, /aStesicoro"
        )

async def acc_station_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los comandos /aEstacion."""
    if not context.chat_data.get('accessibility_mode', False):
        await update.message.reply_text("⚠️ Per prima cosa attiva la modalità accessibilità con /accessibilita.")
        return
    
    # Obtener el comando completo (ej: "/aFontana" o "/aFontana@miobot")
    full_command = update.message.text.split()[0]
    command = full_command.split('@')[0]
    if not command.startswith('/a'):
        await update.message.reply_text("Comando non valido. Usa /aMontepo, /aFontana, ecc.")
        return
    
    estacion_nombre = command[2:].lower()
    
    # Mapeo de nombres a claves internas
    mapeo = {
        "montepo": "montepo",
        "stesicoro": "stesicoro",
        "fontana": "fontana",
        "nesima": "nesima",
        "sannullo": "sannullo",
        "cibali": "cibali",
        "milo": "milo",
        "borgo": "borgo",
        "giuffrida": "giuffrida",
        "italia": "italia",
        "galatea": "galatea",
        "giovanni": "giovanni"
    }
    estacion_key = mapeo.get(estacion_nombre)
    if not estacion_key or estacion_key not in NOMBRE_MOSTRAR:
        await update.message.reply_text(f"Stazione '{estacion_nombre}' non valida.")
        return
    
    await acc_send_station_info(update, context, estacion_key)
