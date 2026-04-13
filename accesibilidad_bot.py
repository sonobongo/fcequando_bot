import os
import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from horarios_logic import *  # Asegúrate de que horarios_logic.py esté accesible
from horarios_logic import CATANIA_TZ

# ============================================================================
# TECLADOS
# ============================================================================
keyboard_exit = ReplyKeyboardMarkup(
    [[KeyboardButton("USCIRE DAL MODO ACCESSIBILITÀ")]],
    resize_keyboard=True, one_time_keyboard=False
)

# Diccionario de nombres de estaciones para mostrar
NOMBRE_MOSTRAR = {
    "montepo": "Monte Po",
    "stesicoro": "Stesicoro",
    "fontana": "Fontana",
    "nesima": "Nesima",
    "sannullo": "San Nullo",
    "cibali": "Cibali",
    "milo": "Milo",
    "borgo": "Borgo",
    "giuffrida": "Giuffrida",
    "italia": "Italia",
    "galatea": "Galatea",
    "giovanni": "Giovanni XXIII"
}

# Descripciones de estaciones (texto plano, con puntos)
DESCRIPCION_ESTACION = {
    "montepo": "· Stazione capolinea con ascensore e servizi igienici.",
    "stesicoro": "· Stazione centrale con ascensore e collegamento autobus.",
    "fontana": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Via Felice Fontana.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Felice Fontana e l'Ospedale Garibaldi-Nesima.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "nesima": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Lorenzo Bolano e Via Filippo Eredia.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trova l'uscita per: Viale Lorenzo Bolano.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "sannullo": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Viale Antoniotto Usodimare e Via Sebastiano Catania.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "cibali": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio, Angelo Massimino.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bergamo, Via Galermo e lo stadio di Calcio.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "milo": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Bronte e Viale Fleming.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano anche le uscite per: Via Bronte e Viale Fleming.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada.",
    "borgo": "· La stazione è dotata di pavimento podotattile e scale mobili.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Empedocle e Via Etnea.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: I treni della FCE, Via Signorelli e Via Caronda.",
    "giuffrida": "· La stazione è dotata di pavimento podotattile e scale mobili.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Guardia della Carvana e Piazza Abraham Lincoln.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Caronda e Via Vincenzo Giuffrida.",
    "italia": "· La stazione è dotata di pavimento podotattile e scale mobili.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Via Firenze, Via Ramondetta e Via Oliveto Scammacca.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Viale Vittorio Veneto e Corso Italia.",
    "galatea": "· La stazione è dotata di pavimento podotattile e scale mobili.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trovano le uscite per: Viale Jonio, Via Pasubio e via Palmanova.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro.\n· Alla testa del treno si trovano le uscite per: Piazza Galatea, Viale Africa e Via Messina.",
    "giovanni": "· La stazione è dotata di pavimento podotattile, scale mobili e Ascensore.\n· Sul marciapiede 1, partono i treni in direzione Monte Po. Alla testa del treno si trova l'uscita per: Piazza Giovanni XXIII e Viale Africa.\n· Sul marciapiede 2 partono i treni in direzione Stesicoro. Alla testa del treno si trovano le uscite per: Via Archimede, Viale della Libertà e Stazione di Trenitalia Catania Centrale.\n· Al centro della piattaforma si trovano gli ascensori con tastiere Braille, che raggiungono la strada."
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def clean_text(text: str) -> str:
    """Reemplaza emojis por · y elimina formato Markdown."""
    replacements = {
        "🔺": "·", "🔻": "·", "🚇": "·", "🕐": "·", "🕙": "·", "📌": "·",
        "**": "", "*": "", "__": "", "`": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
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
    
    # Obtener mensajes 2 y 3 (sin emojis ni formato)
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    # Construir msg2 y msg3 usando las funciones existentes de horarios_logic
    # (Reutilizamos build_temporary_messages, pero necesitamos tenerla disponible)
    # Para no duplicar código, asumimos que build_temporary_messages está en horarios_logic.
    # Si no, tendrías que copiarla. En tu proyecto ya existe.
    from horarios_logic import build_temporary_messages
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_text(msg2)
    msg3_clean = clean_text(msg3)
    
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    descripcion = DESCRIPCION_ESTACION.get(estacion_key, "· Stazione accessibile.")
    
    # Enviar mensaje 1: descripción
    await update.message.reply_text(descripcion, parse_mode=None)
    
    # Enviar mensaje 2
    msg2_obj = await update.message.reply_text(msg2_clean, parse_mode=None)
    
    # Enviar mensaje 3 con botón inline
    keyboard_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("· Aggiornare", callback_data=f"acc_aggiornare_{estacion_key}")]
    ])
    msg3_obj = await update.message.reply_text(msg3_clean, parse_mode=None, reply_markup=keyboard_inline)
    
    # Enviar mensaje 4: lista de comandos
    lista_comandos = (
        "Scegli la stazione che desideri consultare:\n"
        "/aMontepo, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, "
        "/aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni, /aStesicoro"
    )
    msg4_obj = await update.message.reply_text(lista_comandos, parse_mode=None)
    
    # Guardar IDs de los mensajes 2,3,4 para poder borrarlos al actualizar
    context.chat_data['acc_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id, msg4_obj.message_id)
    context.chat_data['acc_last_station'] = estacion_key

async def acc_aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback del botón '· Aggiornare' (refresca mensajes 2,3,4)."""
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[2]  # formato "acc_aggiornare_fontana"
    
    # Borrar mensajes anteriores
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
    
    from horarios_logic import build_temporary_messages
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_text(msg2)
    msg3_clean = clean_text(msg3)
    
    # Enviar nuevos mensajes
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
    
    context.chat_data['acc_msg_ids'] = (msg2_obj.message_id, msg3_obj.message_id, msg4_obj.message_id)

# ============================================================================
# MANEJADORES DE COMANDOS
# ============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Questo è il bot in **modalità accessibilità**.\n"
        "Usa /accessibilita per attivare la modalità.\n\n"
        "I comandi disponibili sono:\n"
        "/accessibilita - Attiva la modalità accessibile\n"
        "/aMontepo, /aStesicoro, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, /aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni",
        parse_mode='Markdown'
    )

async def cmd_accesibilidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo accesibilidad."""
    context.chat_data['accessibility_mode'] = True
    await update.message.reply_text(
        "♿ Modalità accessibilità attivata.\n\n"
        "Scegli la stazione che desideri consultare:\n"
        "/aMontepo, /aFontana, /aNesima, /aSanNullo, /aCibali, /aMilo, /aBorgo, /aGiuffrida, /aItalia, /aGalatea, /aGiovanni, /aStesicoro\n\n"
        "Per uscire, premi il pulsante qui sotto.",
        reply_markup=keyboard_exit
    )

async def cmd_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el modo accesibilidad."""
    context.chat_data['accessibility_mode'] = False
    context.chat_data.pop('acc_msg_ids', None)
    context.chat_data.pop('acc_last_station', None)
    await update.message.reply_text(
        "✅ Modalità accessibilità disattivata. Puoi tornare a usare il bot normale.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("/start")]],
            resize_keyboard=True
        )
    )

async def acc_station_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los comandos /aEstacion."""
    if not context.chat_data.get('accessibility_mode', False):
        await update.message.reply_text("⚠️ Per prima cosa attiva la modalità accessibilità con /accessibilita.")
        return
    
    full_command = update.message.text.split()[0]
    command = full_command.split('@')[0]  # elimina mención de bot
    if not command.startswith('/a'):
        await update.message.reply_text("Comando non valido. Usa /aMontepo, /aFontana, ecc.")
        return
    estacion_nombre = command[2:].lower()
    
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

# ============================================================================
# MAIN
# ============================================================================
def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        print("Errore: Imposta la variabile d'ambiente TELEGRAM_TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("accessibilita", cmd_accesibilidad))
    app.add_handler(CommandHandler("accesibilidad", cmd_accesibilidad))
    # Comandos /a...
    acc_commands = ["aMontepo", "aStesicoro", "aFontana", "aNesima", "aSanNullo",
                    "aCibali", "aMilo", "aBorgo", "aGiuffrida", "aItalia", "aGalatea", "aGiovanni"]
    for cmd in acc_commands:
        app.add_handler(CommandHandler(cmd, acc_station_command))
    
    # Manejador para el botón de salida (ReplyKeyboardMarkup)
    app.add_handler(MessageHandler(filters.Text("USCIRE DAL MODO ACCESSIBILITÀ"), cmd_exit))
    
    # Callback para el botón inline
    app.add_handler(CallbackQueryHandler(acc_aggiornare_callback, pattern="^acc_aggiornare_"))
    
    print("Bot accessibilità avviato. In attesa di messaggi...")
    app.run_polling(allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY])

if __name__ == '__main__':
    main()