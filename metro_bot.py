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

    # ========================================================================
    # WRAPPERS QUE DECIDEN QUÉ MÓDULO USAR SEGÚN MODO DEV
    # ========================================================================
    def is_dev_mode(context):
        return context.chat_data.get('dev_mode', False)

    # Comandos normales (modo normal / desarrollador)
    async def start_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.start_wrapper(update, context)
        else:
            await normal_handlers.start_wrapper(update, context)
    async def help_command_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.help_command_wrapper(update, context)
        else:
            await normal_handlers.help_command_wrapper(update, context)
    async def cmd_montepo_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_montepo_wrapper(update, context)
        else:
            await normal_handlers.cmd_montepo_wrapper(update, context)
    async def cmd_stesicoro_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_stesicoro_wrapper(update, context)
        else:
            await normal_handlers.cmd_stesicoro_wrapper(update, context)
    async def cmd_milo_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_milo_wrapper(update, context)
        else:
            await normal_handlers.cmd_milo_wrapper(update, context)
    async def cmd_fontana_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_fontana_wrapper(update, context)
        else:
            await normal_handlers.cmd_fontana_wrapper(update, context)
    async def cmd_nesima_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_nesima_wrapper(update, context)
        else:
            await normal_handlers.cmd_nesima_wrapper(update, context)
    async def cmd_sannullo_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_sannullo_wrapper(update, context)
        else:
            await normal_handlers.cmd_sannullo_wrapper(update, context)
    async def cmd_cibali_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_cibali_wrapper(update, context)
        else:
            await normal_handlers.cmd_cibali_wrapper(update, context)
    async def cmd_borgo_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_borgo_wrapper(update, context)
        else:
            await normal_handlers.cmd_borgo_wrapper(update, context)
    async def cmd_giuffrida_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_giuffrida_wrapper(update, context)
        else:
            await normal_handlers.cmd_giuffrida_wrapper(update, context)
    async def cmd_italia_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_italia_wrapper(update, context)
        else:
            await normal_handlers.cmd_italia_wrapper(update, context)
    async def cmd_galatea_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_galatea_wrapper(update, context)
        else:
            await normal_handlers.cmd_galatea_wrapper(update, context)
    async def cmd_giovanni_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_giovanni_wrapper(update, context)
        else:
            await normal_handlers.cmd_giovanni_wrapper(update, context)
    async def cmd_altri_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_altri_wrapper(update, context)
        else:
            await normal_handlers.cmd_altri_wrapper(update, context)
    async def handle_button_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.handle_button_wrapper(update, context)
        else:
            await normal_handlers.handle_button_wrapper(update, context)
    async def cmd_testgif_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.cmd_testgif_wrapper(update, context)
        else:
            await normal_handlers.cmd_testgif_wrapper(update, context)
    async def test_command_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.test_command_wrapper(update, context)
        else:
            await normal_handlers.test_command_wrapper(update, context)
    async def testfin_command_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.testfin_command_wrapper(update, context)
        else:
            await normal_handlers.testfin_command_wrapper(update, context)
    async def auto_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.auto_wrapper(update, context)
        else:
            await normal_handlers.auto_wrapper(update, context)
    async def stop_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.stop_wrapper(update, context)
        else:
            await normal_handlers.stop_wrapper(update, context)

    # Callbacks (los mismos para ambos módulos, pero se definen en cada uno)
    async def aggiornare_callback_wrapper(update, context):
        if is_dev_mode(context):
            await dev_handlers.aggiornare_callback(update, context)
        else:
            await normal_handlers.aggiornare_callback(update, context)

    # Wrapper para el callback de cabeceras (Monte Po y Stesicoro)
    async def aggiornare_cabecera_callback_wrapper(update, context):
        if is_dev_mode(context):
            if hasattr(dev_handlers, 'aggiornare_cabecera_callback'):
                await dev_handlers.aggiornare_cabecera_callback(update, context)
            elif hasattr(normal_handlers, 'aggiornare_cabecera_callback'):
                await normal_handlers.aggiornare_cabecera_callback(update, context)
            else:
                logger.warning("aggiornare_cabecera_callback non trovato")
        else:
            if hasattr(normal_handlers, 'aggiornare_cabecera_callback'):
                await normal_handlers.aggiornare_cabecera_callback(update, context)
            else:
                logger.warning("aggiornare_cabecera_callback non trovato")

    # Comandos desarrollo
    async def dev_mode_wrapper(update, context):
        context.chat_data['dev_mode'] = True
        await update.message.reply_text("🔧 Modalità sviluppatore attivata. Usa /devfin per disattivare.")
    async def dev_fin_wrapper(update, context):
        context.chat_data['dev_mode'] = False
        await update.message.reply_text("✅ Modalità sviluppatore disattivata. Tornato alla versione stabile.")

    # ========================================================================
    # REGISTRO DE COMANDOS
    # ========================================================================
    # Comandos normales
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

    # Comandos de accesibilidad (siempre usan el módulo accesibilidad_bot)
    app.add_handler(CommandHandler("accessibilita", acc.cmd_accesibilidad))
    app.add_handler(CommandHandler("accesibilidad", acc.cmd_accesibilidad))
    app.add_handler(CommandHandler("uscire", acc.cmd_uscire))

    # Comandos desarrollo
    app.add_handler(CommandHandler("dev", dev_mode_wrapper))
    app.add_handler(CommandHandler("devfin", dev_fin_wrapper))

    # Teclados (ReplyKeyboardMarkup) para modo normal
    button_texts = ["Monte Po", "Stesicoro", "Altri", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    # Callbacks
    app.add_handler(CallbackQueryHandler(aggiornare_callback_wrapper, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(aggiornare_cabecera_callback_wrapper, pattern="^agg_cabecera_"))

    # ========================================================================
    # MANEJADORES DE TEXTO (en orden de prioridad)
    # ========================================================================
    # 1. Activación rápida de accesibilidad (si el texto empieza con "ac")
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acc.acc_try_activate))

    # 2. Manejador de texto para modo accesibilidad (prefijos y comandos especiales)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, acc.acc_handle_text))

    # 3. Manejador de texto para modo normal (busca nombres completos de estación)
    #    Este manejador comprueba internamente si accessibility_mode está activo
    if hasattr(dev_handlers, 'normal_handle_text'):
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dev_handlers.normal_handle_text))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
