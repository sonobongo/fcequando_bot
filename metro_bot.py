import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, CallbackQueryHandler
from horarios_logic import *
from handlers import *
from handlers_accesibilidad import (
    cmd_accesibilidad, acc_station_command, acc_aggiornare_callback,
    cmd_exit_accessibility, keyboard_exit_accessibility
)

flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Token mancante. Imposta TELEGRAM_TOKEN.")
        return

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server avviato sulla porta 8080")

    defaults = Defaults(disable_notification=True)
    app = Application.builder().token(TOKEN).defaults(defaults).build()

    # Comandi normali
    commands = [
        ("start", start_wrapper), ("help", help_command_wrapper),
        ("montepo", cmd_montepo_wrapper), ("stesicoro", cmd_stesicoro_wrapper),
        ("milo", cmd_milo_wrapper), ("altri", cmd_altri_wrapper),
        ("fontana", cmd_fontana_wrapper), ("nesima", cmd_nesima_wrapper),
        ("sannullo", cmd_sannullo_wrapper), ("cibali", cmd_cibali_wrapper),
        ("borgo", cmd_borgo_wrapper), ("giuffrida", cmd_giuffrida_wrapper),
        ("italia", cmd_italia_wrapper), ("galatea", cmd_galatea_wrapper),
        ("giovanni", cmd_giovanni_wrapper), ("test", test_command_wrapper),
        ("testfin", testfin_command_wrapper), ("testgif", cmd_testgif_wrapper),
        ("auto", auto_wrapper), ("stop", stop_wrapper)
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Comandi accesibilidad
    acc_commands = [
        ("accessibilita", acc_wrapper), ("accesibilidad", acc_wrapper),
        ("aMontepo", acc_station_wrapper), ("aStesicoro", acc_station_wrapper),
        ("aFontana", acc_station_wrapper), ("aNesima", acc_station_wrapper),
        ("aSanNullo", acc_station_wrapper), ("aCibali", acc_station_wrapper),
        ("aMilo", acc_station_wrapper), ("aBorgo", acc_station_wrapper),
        ("aGiuffrida", acc_station_wrapper), ("aItalia", acc_station_wrapper),
        ("aGalatea", acc_station_wrapper), ("aGiovanni", acc_station_wrapper)
    ]
    for cmd, handler in acc_commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Teclados (quitamos el botón "USCIRE DAL MODO ACCESSIBILITÀ")
    button_texts = ["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    # Callbacks
    app.add_handler(CallbackQueryHandler(aggiornare_callback, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(acc_aggiornare_callback, pattern="^acc_aggiornare_"))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

async def acc_wrapper(update, context):
    await cmd_accesibilidad(update, context)

async def acc_station_wrapper(update, context):
    await acc_station_command(update, context)

if __name__ == '__main__':
    main()
