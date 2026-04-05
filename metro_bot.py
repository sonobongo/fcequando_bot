import os
import logging
from datetime import datetime, time, timedelta
from typing import Tuple, Optional
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================================
# HORARIOS DE STESICORO (desde Stesicoro hacia Monte Po)
# ============================================================================
STESICORO = {
    "weekday": [  # LUNEDÌ A GIOVEDÌ
        time(6,25), time(6,35), time(6,45), time(6,55),
        time(7,5), time(7,15), time(7,25), time(7,35), time(7,45), time(7,55),
        time(8,5), time(8,15), time(8,25), time(8,35), time(8,45), time(8,55),
        time(9,5), time(9,15), time(9,25), time(9,35), time(9,45), time(9,55),
        time(10,5), time(10,15), time(10,25), time(10,35), time(10,45), time(10,55),
        time(11,5), time(11,15), time(11,25), time(11,35), time(11,45), time(11,55),
        time(12,5), time(12,15), time(12,25), time(12,35), time(12,45), time(12,55),
        time(13,5), time(13,15), time(13,25), time(13,35), time(13,45), time(13,55),
        time(14,5), time(14,15), time(14,25), time(14,35), time(14,45), time(14,55),
        time(15,5), time(15,16), time(15,28), time(15,41), time(15,54),
        time(16,7), time(16,20), time(16,33), time(16,46), time(16,59),
        time(17,12), time(17,25), time(17,38), time(17,51),
        time(18,4), time(18,17), time(18,30), time(18,43), time(18,56),
        time(19,9), time(19,22), time(19,35), time(19,48),
        time(20,1), time(20,14), time(20,27), time(20,40), time(20,53),
        time(21,6), time(21,19), time(21,32), time(21,45), time(21,58),
        time(22,11), time(22,24), time(22,30), time(22,37), time(22,50),
        time(23,3), time(23,16), time(23,29), time(23,42), time(23,55),
        time(0,8), time(0,21), time(0,34), time(0,47), time(1,0)
    ],
    "friday": [  # VENERDÌ
        time(6,25), time(6,35), time(6,45), time(6,55),
        time(7,5), time(7,15), time(7,25), time(7,35), time(7,45), time(7,55),
        time(8,5), time(8,15), time(8,25), time(8,35), time(8,45), time(8,55),
        time(9,5), time(9,15), time(9,25), time(9,35), time(9,45), time(9,55),
        time(10,5), time(10,15), time(10,25), time(10,35), time(10,45), time(10,55),
        time(11,5), time(11,15), time(11,25), time(11,35), time(11,45), time(11,55),
        time(12,5), time(12,15), time(12,25), time(12,35), time(12,45), time(12,55),
        time(13,5), time(13,15), time(13,25), time(13,35), time(13,45), time(13,55),
        time(14,5), time(14,15), time(14,25), time(14,35), time(14,45), time(14,55),
        time(15,5), time(15,16), time(15,28), time(15,41), time(15,54),
        time(16,7), time(16,20), time(16,33), time(16,46), time(16,59),
        time(17,12), time(17,25), time(17,38), time(17,51),
        time(18,4), time(18,17), time(18,30), time(18,43), time(18,56),
        time(19,9), time(19,22), time(19,35), time(19,48),
        time(20,1), time(20,14), time(20,27), time(20,40), time(20,53),
        time(21,6), time(21,19), time(21,32), time(21,45), time(21,58),
        time(22,11), time(22,24), time(22,30), time(22,37), time(22,50),
        time(23,3), time(23,16), time(23,29), time(23,42), time(23,55),
        time(0,8), time(0,21), time(0,34), time(0,47), time(1,0)
    ],
    "saturday": [  # SABATO
        time(6,26), time(6,39), time(6,52), time(7,5), time(7,18),
        time(7,31), time(7,44), time(7,57), time(8,10), time(8,23),
        time(8,36), time(8,49), time(9,2), time(9,15), time(9,28),
        time(9,41), time(9,54), time(10,7), time(10,20), time(10,33),
        time(10,46), time(10,59), time(11,12), time(11,25), time(11,38),
        time(11,51), time(12,4), time(12,17), time(12,30), time(12,43),
        time(12,56), time(13,9), time(13,22), time(13,35), time(13,48),
        time(14,1), time(14,14), time(14,27), time(14,40), time(14,53),
        time(15,6), time(15,19), time(15,32), time(15,45), time(15,58),
        time(16,11), time(16,24), time(16,37), time(16,50), time(17,3),
        time(17,16), time(17,29), time(17,42), time(17,55), time(18,8),
        time(18,21), time(18,34), time(18,47), time(19,0), time(19,13),
        time(19,26), time(19,39), time(19,52), time(20,5), time(20,18),
        time(20,31), time(20,44), time(20,57), time(21,10), time(21,23),
        time(21,36), time(21,49), time(22,2), time(22,15), time(22,28),
        time(22,41), time(22,54), time(23,7), time(23,20), time(23,33),
        time(23,46), time(0,0), time(0,13), time(0,26), time(0,39),
        time(0,52), time(1,0)
    ],
    "sunday": [  # DOMENICA E FESTIVI
        time(7,26), time(7,39), time(7,52), time(8,5), time(8,18),
        time(8,31), time(8,44), time(8,57), time(9,10), time(9,23),
        time(9,36), time(9,49), time(10,2), time(10,15), time(10,28),
        time(10,41), time(10,54), time(11,7), time(11,20), time(11,33),
        time(11,46), time(11,59), time(12,12), time(12,25), time(12,38),
        time(12,51), time(13,4), time(13,17), time(13,30), time(13,43),
        time(13,56), time(14,9), time(14,22), time(14,35), time(14,48),
        time(15,1), time(15,14), time(15,27), time(15,40), time(15,53),
        time(16,6), time(16,19), time(16,32), time(16,45), time(16,58),
        time(17,11), time(17,24), time(17,37), time(17,50), time(18,3),
        time(18,16), time(18,29), time(18,42), time(18,55), time(19,8),
        time(19,21), time(19,34), time(19,47), time(20,0), time(20,13),
        time(20,26), time(20,39), time(20,52), time(21,5), time(21,18),
        time(21,31), time(21,44), time(21,57), time(22,10), time(22,30)
    ]
}

# ============================================================================
# HORARIOS DE MONTEPO (desde Monte Po hacia Stesicoro)
# ============================================================================
MONTERO = {
    "weekday": [  # LUNEDÌ A GIOVEDÌ
        time(6,0), time(6,10), time(6,20), time(6,30),
        time(6,40), time(6,50), time(7,0), time(7,10), time(7,20), time(7,30),
        time(7,40), time(7,50), time(8,0), time(8,10), time(8,20), time(8,30),
        time(8,40), time(8,50), time(9,0), time(9,10), time(9,20), time(9,30),
        time(9,40), time(9,50), time(10,0), time(10,10), time(10,20), time(10,30),
        time(10,40), time(10,50), time(11,0), time(11,10), time(11,20), time(11,30),
        time(11,40), time(11,50), time(12,0), time(12,10), time(12,20), time(12,30),
        time(12,40), time(12,50), time(13,0), time(13,10), time(13,20), time(13,30),
        time(13,40), time(13,50), time(14,0), time(14,10), time(14,20), time(14,30),
        time(14,40), time(14,50), time(15,0), time(15,10), time(15,20), time(15,33),
        time(15,46), time(15,59), time(16,12), time(16,25), time(16,38), time(16,51),
        time(17,4), time(17,17), time(17,30), time(17,43), time(17,56), time(18,9),
        time(18,22), time(18,35), time(18,48), time(19,1), time(19,14), time(19,27),
        time(19,40), time(19,53), time(20,6), time(20,19), time(20,32), time(20,45),
        time(20,58), time(21,11), time(21,24), time(21,37), time(21,50), time(22,3),
        time(22,16), time(22,30)
    ],
    "friday": [  # VENERDÌ
        time(6,0), time(6,10), time(6,20), time(6,30),
        time(6,40), time(6,50), time(7,0), time(7,10), time(7,20), time(7,30),
        time(7,40), time(7,50), time(8,0), time(8,10), time(8,20), time(8,30),
        time(8,40), time(8,50), time(9,0), time(9,10), time(9,20), time(9,30),
        time(9,40), time(9,50), time(10,0), time(10,10), time(10,20), time(10,30),
        time(10,40), time(10,50), time(11,0), time(11,10), time(11,20), time(11,30),
        time(11,40), time(11,50), time(12,0), time(12,10), time(12,20), time(12,30),
        time(12,40), time(12,50), time(13,0), time(13,10), time(13,20), time(13,30),
        time(13,40), time(13,50), time(14,0), time(14,10), time(14,20), time(14,30),
        time(14,40), time(14,50), time(15,0), time(15,10), time(15,20), time(15,33),
        time(15,46), time(15,59), time(16,12), time(16,25), time(16,38), time(16,51),
        time(17,4), time(17,17), time(17,30), time(17,43), time(17,56), time(18,9),
        time(18,22), time(18,35), time(18,48), time(19,1), time(19,14), time(19,27),
        time(19,40), time(19,53), time(20,6), time(20,19), time(20,32), time(20,45),
        time(20,58), time(21,11), time(21,24), time(21,37), time(21,50), time(22,3),
        time(22,16), time(22,30), time(22,43), time(22,56), time(23,9), time(23,22),
        time(23,35), time(23,48), time(0,1), time(0,14), time(0,27), time(0,34)
    ],
    "saturday": [  # SABATO
        time(6,0), time(6,13), time(6,26), time(6,39), time(6,52),
        time(7,5), time(7,18), time(7,31), time(7,44), time(7,57),
        time(8,10), time(8,23), time(8,36), time(8,49), time(9,2),
        time(9,15), time(9,28), time(9,41), time(9,54), time(10,7),
        time(10,20), time(10,33), time(10,46), time(10,59), time(11,12),
        time(11,25), time(11,38), time(11,51), time(12,4), time(12,17),
        time(12,30), time(12,43), time(12,56), time(13,9), time(13,22),
        time(13,35), time(13,48), time(14,1), time(14,14), time(14,27),
        time(14,40), time(14,53), time(15,6), time(15,19), time(15,32),
        time(15,45), time(15,58), time(16,11), time(16,24), time(16,37),
        time(16,50), time(17,3), time(17,16), time(17,29), time(17,42),
        time(17,55), time(18,8), time(18,21), time(18,34), time(18,47),
        time(19,0), time(19,13), time(19,26), time(19,39), time(19,52),
        time(20,5), time(20,18), time(20,31), time(20,44), time(20,57),
        time(21,10), time(21,23), time(21,36), time(21,49), time(22,2),
        time(22,15), time(22,28), time(22,41), time(22,54), time(23,7),
        time(23,20), time(23,33), time(23,46), time(23,59), time(0,12),
        time(0,25)
    ],
    "sunday": [  # DOMENICA E FESTIVI
        time(7,0), time(7,13), time(7,26), time(7,39), time(7,52),
        time(8,5), time(8,18), time(8,31), time(8,44), time(8,57),
        time(9,10), time(9,23), time(9,36), time(9,49), time(10,2),
        time(10,15), time(10,28), time(10,41), time(10,54), time(11,7),
        time(11,20), time(11,33), time(11,46), time(11,59), time(12,12),
        time(12,25), time(12,38), time(12,51), time(13,4), time(13,17),
        time(13,30), time(13,43), time(13,56), time(14,9), time(14,22),
        time(14,35), time(14,48), time(15,1), time(15,14), time(15,27),
        time(15,40), time(15,53), time(16,6), time(16,19), time(16,32),
        time(16,45), time(16,58), time(17,11), time(17,24), time(17,37),
        time(17,50), time(18,3), time(18,16), time(18,29), time(18,42),
        time(18,55), time(19,8), time(19,21), time(19,34), time(19,47),
        time(20,0), time(20,13), time(20,26), time(20,39), time(20,52),
        time(21,5), time(21,18), time(21,31), time(21,44), time(21,57)
    ]
}

SCHEDULES = {
    "Stesicoro": STESICORO,
    "Montepo": MONTERO
}

CATANIA_TZ = pytz.timezone('Europe/Rome')

# ============================================================================
# FUNCIONES PARA DETECTAR CIERRE DEL METRO
# ============================================================================

def get_opening_time(now: datetime) -> Tuple[int, int]:
    """Devuelve la hora de apertura del metro (hora, minuto) según el día."""
    weekday = now.weekday()
    if weekday == 6:  # Domingo
        return (7, 0)
    else:  # Lunes a sábado
        return (6, 0)

def get_closing_time(now: datetime) -> Tuple[int, int]:
    """Devuelve la hora de cierre del metro (hora, minuto) según el día."""
    weekday = now.weekday()
    if weekday in [4, 5]:  # Viernes y sábado
        return (1, 0)   # Cierra a la 1:00 de la madrugada
    else:  # Lunes a jueves y domingo
        return (22, 30)

def is_metro_closed(now: datetime) -> Tuple[bool, Optional[datetime]]:
    """
    Verifica si el metro está cerrado.
    Retorna: (está_cerrado, próxima_apertura_datetime)
    """
    current_time = now.time()
    weekday = now.weekday()
    
    # Obtener hora de apertura y cierre
    open_h, open_m = get_opening_time(now)
    close_h, close_m = get_closing_time(now)
    
    opening_time = time(open_h, open_m)
    closing_time = time(close_h, close_m)
    
    # Caso especial: viernes/sábado cierran a la 1:00 (pasada la medianoche)
    if weekday in [4, 5]:  # Viernes o sábado
        # Si la hora actual es después de la 1:00, está cerrado hasta las 6:00 (apertura del mismo día)
        if current_time >= closing_time and current_time < opening_time:
            # Próxima apertura: hoy a las 6:00 si aún no ha pasado
            next_open = datetime.combine(now.date(), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            if next_open <= now:
                # Si ya pasaron las 6:00 (caso raro, pero por si acaso), será mañana
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
                next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open)
        else:
            return (False, None)
    else:
        # Resto de días: cierre a las 22:30, apertura al día siguiente
        if current_time >= closing_time or current_time < opening_time:
            # Está cerrado: o después del cierre o antes de la apertura
            # Próxima apertura: hoy si aún no ha abierto, mañana si ya cerró
            if current_time < opening_time:
                next_open = datetime.combine(now.date(), opening_time)
            else:
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open)
        else:
            return (False, None)

def get_next_departure(station: str) -> Tuple[Optional[datetime], int, bool]:
    """
    Retorna (próximo_tren_datetime, minutos_restantes, hay_tren_hoy)
    Si no hay tren hoy (cerrado), retorna (None, 0, False)
    """
    now = datetime.now(CATANIA_TZ)
    current_time = now.time()
    weekday_num = now.weekday()
    
    if station not in SCHEDULES:
        raise ValueError(f"Station {station} not found")
    
    # Seleccionar lista de horarios según día
    if weekday_num == 4:  # Venerdì
        schedule_list = SCHEDULES[station]["friday"]
    elif weekday_num == 5:  # Sabato
        schedule_list = SCHEDULES[station]["saturday"]
    elif weekday_num == 6:  # Domenica
        schedule_list = SCHEDULES[station]["sunday"]
    else:  # Lunedì a Giovedì
        schedule_list = SCHEDULES[station]["weekday"]
    
    # Buscar primer horario posterior a la hora actual
    next_departure_time = None
    for departure in schedule_list:
        if departure > current_time:
            next_departure_time = departure
            break
    
    if next_departure_time is None:
        # No hay más trenes hoy -> metro cerrado
        return (None, 0, False)
    
    next_departure_datetime = datetime.combine(now.date(), next_departure_time)
    next_departure_datetime = CATANIA_TZ.localize(next_departure_datetime)
    minutes_until = int((next_departure_datetime - now).total_seconds() // 60)
    return (next_departure_datetime, minutes_until, True)

# ============================================================================
# FUNCIÓN PARA MENSAJE DE ÚLTIMA SALIDA (sin cambios)
# ============================================================================
def get_last_train_message() -> str:
    now = datetime.now(CATANIA_TZ)
    weekday = now.weekday()
    if weekday in [0, 1, 2, 3]:  # Lunedì a Giovedì
        last_time = "22:30"
    elif weekday in [4, 5]:  # Venerdì e Sabato
        last_time = "01:00"
    else:  # Domenica
        last_time = "22:30"
    return f"📌 Ricorda che oggi l'ultima metropolitana da Stesicoro parte alle {last_time}."

# ============================================================================
# CONFIGURACIÓN DEL BOT
# ============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("Monte Po"), KeyboardButton("Stesicoro")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    last_msg = get_last_train_message()
    await update.message.reply_text(
        f"Ciao {user.first_name}! 👋\n\n"
        "Posso dirti quando parte il prossimo treno della metropolitana di Catania.\n"
        "Premi uno dei pulsanti qui sotto 👇\n\n"
        f"{last_msg}",
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandi disponibili:\n"
        "/start - Messaggio di benvenuto\n"
        "/help - Questo aiuto\n\n"
        "Oppure premi direttamente i pulsanti Monte Po o Stesicoro.",
        reply_markup=keyboard
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Monte Po":
        station = "Montepo"
    elif text == "Stesicoro":
        station = "Stesicoro"
    else:
        await update.message.reply_text("Scelta non valida. Usa i pulsanti.", reply_markup=keyboard)
        return
    
    # Verificar si el metro está cerrado
    now = datetime.now(CATANIA_TZ)
    closed, next_open = is_metro_closed(now)
    if closed:
        open_time_str = next_open.strftime("%H:%M")
        msg = f"🚇 Il metrò è chiuso in questo momento.\n🕒 Riaprirà alle {open_time_str}."
        await update.message.reply_text(msg, reply_markup=keyboard)
        return
    
    # Si está abierto, buscar próximo tren
    try:
        next_dep, minutes, has_trains = get_next_departure(station)
        if not has_trains:
            # No hay más trenes hoy (aunque según is_metro_closed no debería pasar, pero por si acaso)
            msg = "🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            await update.message.reply_text(msg, reply_markup=keyboard)
            return
        
        if minutes == 0:
            msg = f"🚇 Il prossimo treno a {text} parte subito.\n\n"
        else:
            msg = f"🚇 Il prossimo treno a {text} parte tra {minutes} minuti, alle {next_dep.strftime('%H:%M')}.\n\n"
        msg += get_last_train_message()
        await update.message.reply_text(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Errore nel recupero degli orari. Riprova più tardi.", reply_markup=keyboard)

async def proximo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Esempio: /proximo Stesicoro  oppure  /proximo Montepo", reply_markup=keyboard)
        return
    station_name = " ".join(context.args).capitalize()
    if station_name not in SCHEDULES:
        await update.message.reply_text(f"Non ho dati per '{station_name}'. Stazioni disponibili: Stesicoro, Montepo.", reply_markup=keyboard)
        return
    
    # Verificar cierre
    now = datetime.now(CATANIA_TZ)
    closed, next_open = is_metro_closed(now)
    if closed:
        open_time_str = next_open.strftime("%H:%M")
        msg = f"🚇 Il metrò è chiuso in questo momento.\n🕒 Riaprirà alle {open_time_str}."
        await update.message.reply_text(msg, reply_markup=keyboard)
        return
    
    try:
        next_dep, minutes, has_trains = get_next_departure(station_name)
        if not has_trains:
            msg = "🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            await update.message.reply_text(msg, reply_markup=keyboard)
            return
        if minutes == 0:
            msg = f"🚇 Il prossimo treno a {station_name} parte subito.\n\n"
        else:
            msg = f"🚇 Il prossimo treno a {station_name} parte tra {minutes} minuti, alle {next_dep.strftime('%H:%M')}.\n\n"
        msg += get_last_train_message()
        await update.message.reply_text(msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Errore nel recupero degli orari.", reply_markup=keyboard)

def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Errore: variabile d'ambiente TELEGRAM_TOKEN non trovata.")
        print("Errore: manca il token. Imposta la variabile d'ambiente TELEGRAM_TOKEN.")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("proximo", proximo))
    app.add_handler(MessageHandler(filters.Text(["Monte Po", "Stesicoro"]), handle_button))
    logger.info("Bot avviato. Premi Ctrl+C per fermare.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
