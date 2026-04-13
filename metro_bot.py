import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, CallbackQueryHandler
from horarios_logic import *
from handlers import *

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

    # Comandi principales (modo normal)
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

    # Comandi del modo accesibilidad
    acc_commands = [
        ("accesibilidad", acc_wrapper), ("accesibilita", acc_wrapper),
        ("aMontepo", acc_station_wrapper), ("aStesicoro", acc_station_wrapper),
        ("aFontana", acc_station_wrapper), ("aNesima", acc_station_wrapper),
        ("aSanNullo", acc_station_wrapper), ("aCibali", acc_station_wrapper),
        ("aMilo", acc_station_wrapper), ("aBorgo", acc_station_wrapper),
        ("aGiuffrida", acc_station_wrapper), ("aItalia", acc_station_wrapper),
        ("aGalatea", acc_station_wrapper), ("aGiovanni", acc_station_wrapper)
    ]
    for cmd, handler in acc_commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Teclados personalizados (ReplyKeyboardMarkup) para modo normal
    button_texts = ["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII",
                    "USCIRE DAL MODO ACCESSIBILITÀ"]
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    # Manejadores para botones inline (modo normal y accesibilidad)
    app.add_handler(CallbackQueryHandler(aggiornare_callback, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(acc_aggiornare_callback, pattern="^acc_aggiornare_"))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
