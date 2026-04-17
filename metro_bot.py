import os
import logging
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, Defaults, CallbackQueryHandler
from horarios_logic import *
import handlers_dev as dev_handlers
import handlers_acc as acc_handlers

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

    # Wrappers para comandos (delegan a dev_handlers)
    async def start_wrapper(update, context):
        await dev_handlers.start_wrapper(update, context)
    async def help_command_wrapper(update, context):
        await dev_handlers.help_command_wrapper(update, context)
    async def cmd_montepo_wrapper(update, context):
        await dev_handlers.cmd_montepo_wrapper(update, context)
    async def cmd_stesicoro_wrapper(update, context):
        await dev_handlers.cmd_stesicoro_wrapper(update, context)
    async def cmd_milo_wrapper(update, context):
        await dev_handlers.cmd_milo_wrapper(update, context)
    async def cmd_fontana_wrapper(update, context):
        await dev_handlers.cmd_fontana_wrapper(update, context)
    async def cmd_nesima_wrapper(update, context):
        await dev_handlers.cmd_nesima_wrapper(update, context)
    async def cmd_sannullo_wrapper(update, context):
        await dev_handlers.cmd_sannullo_wrapper(update, context)
    async def cmd_cibali_wrapper(update, context):
        await dev_handlers.cmd_cibali_wrapper(update, context)
    async def cmd_borgo_wrapper(update, context):
        await dev_handlers.cmd_borgo_wrapper(update, context)
    async def cmd_giuffrida_wrapper(update, context):
        await dev_handlers.cmd_giuffrida_wrapper(update, context)
    async def cmd_italia_wrapper(update, context):
        await dev_handlers.cmd_italia_wrapper(update, context)
    async def cmd_galatea_wrapper(update, context):
        await dev_handlers.cmd_galatea_wrapper(update, context)
    async def cmd_giovanni_wrapper(update, context):
        await dev_handlers.cmd_giovanni_wrapper(update, context)
    async def cmd_altri_wrapper(update, context):
        await dev_handlers.cmd_altri_wrapper(update, context)
    async def cmd_testgif_wrapper(update, context):
        await dev_handlers.cmd_testgif_wrapper(update, context)
    async def test_command_wrapper(update, context):
        await dev_handlers.test_command_wrapper(update, context)
    async def testfin_command_wrapper(update, context):
        await dev_handlers.testfin_command_wrapper(update, context)
    async def auto_wrapper(update, context):
        await dev_handlers.auto_wrapper(update, context)
    async def stop_wrapper(update, context):
        await dev_handlers.stop_wrapper(update, context)

    # Callbacks
    async def aggiornare_callback_wrapper(update, context):
        await dev_handlers.aggiornare_callback(update, context)
    async def aggiornare_cabecera_callback_wrapper(update, context):
        await dev_handlers.aggiornare_cabecera_callback(update, context)

    # Comandos desarrollo
    async def dev_mode_wrapper(update, context):
        context.chat_data['dev_mode'] = True
        await update.message.reply_text("Modalità sviluppatore attivata. Usa /devfin per disattivare.")
    async def dev_fin_wrapper(update, context):
        context.chat_data['dev_mode'] = False
        await update.message.reply_text("Modalità sviluppatore disattivata. Tornato alla versione stabile.")

    # Comandos about/grazie
    FOTO_CREDITI_URL = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/FOTOMASTER.jpg"
    CREDITI_MSG = "Chatbot sviluppato con grande impegno da Àlex Naranjo. Se ti piace, condividilo con i tuoi amici e familiari. https://t.me/FCEQuando_bot"

    async def about_cmd(update, context):
        try:
            await update.message.reply_photo(photo=FOTO_CREDITI_URL, caption=CREDITI_MSG, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(CREDITI_MSG, parse_mode='Markdown')

    async def grazie_cmd(update, context):
        try:
            await update.message.reply_photo(photo=FOTO_CREDITI_URL, caption=CREDITI_MSG, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(CREDITI_MSG, parse_mode='Markdown')

    # Registro de comandos
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
        ("auto", auto_wrapper), ("stop", stop_wrapper),
        ("about", about_cmd), ("grazie", grazie_cmd)
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    app.add_handler(CommandHandler("dev", dev_mode_wrapper))
    app.add_handler(CommandHandler("devfin", dev_fin_wrapper))

    # ========================================================================
    # MANEJADOR DE BOTONES (ReplyKeyboardMarkup) - respeta modo acces
    # ========================================================================
    button_texts = ["Monte Po", "Stesicoro", "Altri", "Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    
    async def handle_button_wrapper(update, context):
        if context.chat_data.get('acces_mode', False):
            # Redirigir al handler de acc
            await acc_handlers.normal_handle_text(update, context)
        else:
            await dev_handlers.handle_button_wrapper(update, context)
    
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    # Callbacks
    app.add_handler(CallbackQueryHandler(aggiornare_callback_wrapper, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(aggiornare_cabecera_callback_wrapper, pattern="^agg_cabecera_"))
    app.add_handler(CallbackQueryHandler(dev_handlers.aggiornare_super_callback, pattern="^aggiornare_super$"))

    # ========================================================================
    # MANEJADOR DE TEXTO PRINCIPAL (para todo mensaje que no sea comando ni botón)
    # ========================================================================
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if context.chat_data.get('acces_mode', False):
            await acc_handlers.normal_handle_text(update, context)
        else:
            if text.lower() == "acces":
                await acc_handlers.activate_acces_mode(update, context)
            else:
                await dev_handlers.normal_handle_text(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
