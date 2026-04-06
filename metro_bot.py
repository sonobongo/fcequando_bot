import os
import logging
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from horarios_logic import *
from handlers import *

# ============================================================================
# SERVIDOR WEB (Flask) PARA RESPONDER A PINGS DE UPTIMEROBOT
# ============================================================================
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============================================================================
# LOGGING Y MAIN
# ============================================================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Token mancante")
        return

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server avviato sulla porta 8080")

    app = Application.builder().token(TOKEN).build()
    for cmd, handler in [
        ("start", start), ("help", help_command), ("montepo", cmd_montepo), ("stesicoro", cmd_stesicoro),
        ("milo", cmd_milo), ("altri", cmd_altri), ("fontana", cmd_fontana), ("nesima", cmd_nesima),
        ("sannullo", cmd_sannullo), ("cibali", cmd_cibali), ("borgo", cmd_borgo), ("giuffrida", cmd_giuffrida),
        ("italia", cmd_italia), ("galatea", cmd_galatea), ("giovanni", cmd_giovanni), ("test", test_command),
        ("testfin", testfin_command), ("real", real_command), ("realfin", realfin_command)
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(MessageHandler(filters.Text(["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo", "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]), handle_button))
    
    import time
    time.sleep(2)
    
    logger.info("Bot avviato. Premi Ctrl+C per fermare.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
