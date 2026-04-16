import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, CallbackQueryHandler
from horarios_logic import *
import handlers as normal_handlers
import handlers_dev as dev_handlers
import accesibilidad_bot as acc

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

    def is_dev_mode(context):
        return context.chat_data.get('dev_mode', False)

    # Wrappers (mantén los que ya tienes, son muchos; aquí solo pongo lo esencial para que funcione)
    # ... (tus wrappers existentes, no los cambio)

    # Comandos de accesibilidad
    app.add_handler(CommandHandler("accessibilita", acc.cmd_accesibilidad))
    app.add_handler(CommandHandler("accesibilidad", acc.cmd_accesibilidad))
    app.add_handler(CommandHandler("uscire", acc.cmd_uscire))

    # Comandos desarrollo
    app.add_handler(CommandHandler("dev", dev_mode_wrapper))
    app.add_handler(CommandHandler("devfin", dev_fin_wrapper))

    # Teclados y callbacks (igual que antes)
    button_texts = ["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    app.add_handler(CallbackQueryHandler(aggiornare_callback_wrapper, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(aggiornare_cabecera_callback_wrapper, pattern="^agg_cabecera_"))
    app.add_handler(CallbackQueryHandler(acc.acc_aggiornare_callback, pattern="^acc_aggiornare_"))

    # ========================================================================
    # MANEJADORES DE TEXTO - ORDEN CRÍTICO
    # ========================================================================
    # 1. Activación rápida de accesibilidad (opcional)
    if hasattr(acc, 'acc_try_activate'):
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acc.acc_try_activate))

    # 2. Modo normal (solo si NO estamos en modo accesibilidad, gracias al flag)
    if hasattr(dev_handlers, 'normal_handle_text'):
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dev_handlers.normal_handle_text))

    # 3. Modo accesibilidad (solo actúa si el flag está activo)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acc.acc_handle_text))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
