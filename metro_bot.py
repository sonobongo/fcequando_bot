import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, CallbackQueryHandler
from horarios_logic import *
import handlers as normal_handlers
import handlers_dev as dev_handlers

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

    # ========================================================================
    # MODO DEV
    # ========================================================================
    def is_dev_mode(context):
        return context.chat_data.get('dev_mode', False)

    async def dev_mode_wrapper(update, context):
        context.chat_data['dev_mode'] = True
        await update.message.reply_text("🔧 Modalità sviluppatore attivata. Usa /devfin per disattivare.")

    async def dev_fin_wrapper(update, context):
        context.chat_data['dev_mode'] = False
        await update.message.reply_text("✅ Modalità sviluppatore disattivata. Tornato alla versione stabile.")

    app.add_handler(CommandHandler("dev", dev_mode_wrapper))
    app.add_handler(CommandHandler("devfin", dev_fin_wrapper))

    # ========================================================================
    # Resto de comandos (puedes ir añadiéndolos poco a poco)
    # ========================================================================
    # Por ahora, solo añadimos /start para probar
    async def start(update, context):
        await update.message.reply_text("Bot attivo. Usa /dev per attivare la modalità sviluppatore.")

    app.add_handler(CommandHandler("start", start))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
