import os
import logging
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
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

    app = Application.builder().token(TOKEN).build()

    # Registrar comandos
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
        ("refrescar", cmd_refrescar_wrapper)
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    # Manejador para el botón inline de refrescar
    app.add_handler(CallbackQueryHandler(callback_refrescar, pattern="^refresh_"))

    # Capturar todos los mensajes de texto que no sean comandos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_wrapper))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
