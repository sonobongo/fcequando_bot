import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from horarios_logic import *
from handlers import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("Token mancante. Imposta TELEGRAM_TOKEN.")
        return

    app = Application.builder().token(TOKEN).build()

    commands = [
        ("start", start), ("help", help_command), ("montepo", cmd_montepo), ("stesicoro", cmd_stesicoro),
        ("milo", cmd_milo), ("altri", cmd_altri), ("fontana", cmd_fontana), ("nesima", cmd_nesima),
        ("sannullo", cmd_sannullo), ("cibali", cmd_cibali), ("borgo", cmd_borgo), ("giuffrida", cmd_giuffrida),
        ("italia", cmd_italia), ("galatea", cmd_galatea), ("giovanni", cmd_giovanni), ("test", test_command),
        ("testfin", testfin_command), ("testgif", cmd_testgif)
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    button_texts = ["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, signal_handlers=False)

if __name__ == '__main__':
    main()
