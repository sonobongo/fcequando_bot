import asyncio
import time as time_module
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
# FUNCIONES AUXILIARES PARA LIMPIAR TEXTO
# ============================================================================
def clean_for_accessibility(text: str) -> str:
    """Elimina emojis, asteriscos, negritas y caracteres no deseados para TalkBack."""
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

def get_station_by_prefix(text: str) -> tuple:
    """
    Devuelve (clave_estacion, nombre_mostrar) si el texto comienza con un prefijo conocido
    o si coincide con el nombre completo. Los prefijos son secretos (no se muestran al usuario).
    """
    text = text.lower().strip()
    import unicodedata
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    
    # Prefijos (ordenados de más largo a más corto) - SECRETOS
    prefijos = [
        ("monte", "montepo"), ("mon", "montepo"),
        ("fontana", "fontana"), ("font", "fontana"), ("fon", "fontana"),
        ("nesima", "nesima"), ("nes", "nesima"),
        ("san nullo", "sannullo"), ("san", "sannullo"), ("sann", "sannullo"),
        ("cibali", "cibali"), ("cib", "cibali"),
        ("milo", "milo"), ("mil", "milo"),
        ("borgo", "borgo"), ("bor", "borgo"),
        ("giuffrida", "giuffrida"), ("giu", "giuffrida"),
        ("italia", "italia"), ("ita", "italia"),
        ("galatea", "galatea"), ("gal", "galatea"),
        ("giovanni", "giovanni"), ("gio", "giovanni"), ("giov", "giovanni"),
        ("stesicoro", "stesicoro"), ("stes", "stesicoro"), ("ste", "stesicoro")
    ]
    
    for prefijo, clave in prefijos:
        if text.startswith(prefijo):
            return clave, NOMBRE_MOSTRAR.get(clave, clave.capitalize())
    
    # Si no hay prefijo, intentar coincidencia exacta (nombre completo)
    mapping = {
        "monte po": "montepo", "montepo": "montepo",
        "stesicoro": "stesicoro",
        "fontana": "fontana",
        "nesima": "nesima",
        "san nullo": "sannullo", "sannullo": "sannullo",
        "cibali": "cibali",
        "milo": "milo",
        "borgo": "borgo",
        "giuffrida": "giuffrida",
        "italia": "italia",
        "galatea": "galatea",
        "giovanni xxiii": "giovanni", "giovanni": "giovanni"
    }
    if text in mapping:
        clave = mapping[text]
        return clave, NOMBRE_MOSTRAR.get(clave, clave.capitalize())
    
    return None, None

# ============================================================================
# FUNCIÓN PRINCIPAL PARA ENVIAR INFORMACIÓN DE ESTACIÓN (MODO ACCESIBLE)
# ============================================================================
async def acc_send_station_info(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    """Envía la información de una estación en modo accesibilidad (sin borrar mensajes anteriores)."""
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    # Obtener mensajes de horarios (msg2 y msg3) y limpiarlos
    msg2, msg3, _, _, _, _, _, _ = build_temporary_messages(now, estacion_key)
    msg2_clean = clean_for_accessibility(msg2) or "Nessun treno in arrivo verso Monte Po."
    msg3_clean = clean_for_accessibility(msg3) or "Nessun treno in arrivo verso Stesicoro."
    
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    descripcion = DESCRIPCION_ESTACION.get(estacion_key, "Stazione accessibile.")
    
    # Imagen de la estación (prefijo st_a)
    nombre_imagen = nombre.replace(" ", "").replace("XXIII", "XXIII")
    if nombre_imagen == "SanNullo":
        nombre_imagen = "SanNullo"
    elif nombre_imagen == "GiovanniXXIII":
        nombre_imagen = "GiovanniXXIII"
    img_url = f"https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_a{nombre_imagen}.png"
    cache_buster = int(time_module.time())
    img_url = f"{img_url}?v={cache_buster}"
    
    # Enviar mensajes
    await update.message.reply_photo(photo=img_url, caption=f"Stazione {nombre}", parse_mode=None)
    await update.message.reply_text(descripcion, parse_mode=None)
    await update.message.reply_text(f"Prossimi treni verso Monte Po:\n{msg2_clean}", parse_mode=None)
    await update.message.reply_text(f"Prossimi treni verso Stesicoro:\n{msg3_clean}", parse_mode=None)
    
    # Instrucciones finales (sin revelar el truco de los prefijos)
    instrucciones = (
        "Digita o detta la stazione che desideri controllare; se desideri aggiornare la stazione corrente, ripeti l'operazione.\n"
        "Scegli: Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro.\n"
        "Per uscire dalla modalità accessibilità, scrivi /uscire."
    )
    await update.message.reply_text(instrucciones, parse_mode=None)

# ============================================================================
# MANEJADOR DE TEXTO PARA MODO ACCESIBILIDAD
# ============================================================================
async def acc_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes de texto cuando el modo accesibilidad está activo."""
    if not context.chat_data.get('accessibility_mode', False):
        return
    
    text = update.message.text.strip()
    # Salir si el usuario escribe /uscire o palabras similares
    if text.lower() in ["/uscire", "uscire", "exit", "salir"]:
        await cmd_uscire(update, context)
        return
    
    # Buscar estación por prefijo o nombre
    estacion_key, nombre_estacion = get_station_by_prefix(text)
    if estacion_key:
        await update.message.reply_text(f"Hai scelto {nombre_estacion}. Ecco le informazioni:")
        await acc_send_station_info(update, context, estacion_key)
    else:
        await update.message.reply_text(
            "Stazione non riconosciuta. Le stazioni disponibili sono:\n"
            "Monte Po, Fontana, Nesima, San Nullo, Cibali, Milo, Borgo, Giuffrida, Italia, Galatea, Giovanni XXIII, Stesicoro\n\n"
            "Per uscire dalla modalità accessibilità, scrivi /uscire"
        )

# ============================================================================
# COMANDO PARA ACTIVAR MODO ACCESIBILIDAD (SIN REVELAR PREFIJOS)
# ============================================================================
async def cmd_accesibilidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa el modo accesibilidad (entrada por texto con prefijos secretos)."""
    context.chat_data['accessibility_mode'] = True
    await update.message.reply_text(
        "♿ Modalità accessibilità attivata.\n\n"
        "Puoi scrivere o dire in voce il nome della stazione che desideri consultare.\n"
        "Esempio: scrivi 'Monte Po' o 'Galatea'.\n\n"
        "Per uscire dalla modalità, scrivi /uscire.",
        parse_mode=None
    )

# ============================================================================
# COMANDO PARA SALIR DEL MODO ACCESIBILIDAD
# ============================================================================
async def cmd_uscire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactiva el modo accesibilidad y vuelve al modo normal (con teclado principal)."""
    if context.chat_data.get('accessibility_mode', False):
        context.chat_data['accessibility_mode'] = False
        await update.message.reply_text("✅ Modalità accessibilità disattivata. Sei tornato al menu principale.")
    else:
        await update.message.reply_text("⚠️ Non sei in modalità accessibilità.")

# ============================================================================
# ACTIVACIÓN RÁPIDA ESCRIBIENDO "ac..."
# ============================================================================
async def acc_try_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Si el texto empieza con 'ac' (case-insensitive) y la accesibilidad no está activa, la activa."""
    if context.chat_data.get('accessibility_mode', False):
        return
    text = update.message.text.strip().lower()
    if text.startswith("acces"):
        await cmd_accesibilidad(update, context)

# ============================================================================
# NOTA: La función build_temporary_messages y NOMBRE_MOSTRAR se importan de horarios_logic
# ============================================================================
