import os
import logging
import threading
import unicodedata
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

    # Wrappers per comandi (delegano a dev_handlers)
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

    # Comandi sviluppo
    async def dev_mode_wrapper(update, context):
        context.chat_data['dev_mode'] = True
        await update.message.reply_text("Modalità sviluppatore attivata. Usa /devfin per disattivare.")
    async def dev_fin_wrapper(update, context):
        context.chat_data['dev_mode'] = False
        await update.message.reply_text("Modalità sviluppatore disattivata. Tornato alla versione stabile.")

    # Comandi about/grazie
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

    # Nuevo comando /demo
    async def demo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.message.reply_text(
                "🔄 **Modalità demo**\n\n"
                "Per fissare una data/ora simulata senza indicatore:\n"
                "`/demo DDMMYYYY HHMM`\n"
                "Esempio: `/demo 11022026 1102`\n\n"
                "Per disattivare: `/testfin`",
                parse_mode='Markdown'
            )
            return
        if len(args) == 2:
            date_str, time_str = args[0], args[1]
            if len(date_str) != 8 or not date_str.isdigit():
                await update.message.reply_text("Formato data non valido. Usa DDMMYYYY.")
                return
            if len(time_str) != 4 or not time_str.isdigit():
                await update.message.reply_text("Formato ora non valido. Usa HHMM.")
                return
            day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
            hour, minute = int(time_str[0:2]), int(time_str[2:4])
            if hour > 23 or minute > 59:
                await update.message.reply_text("Ora non valida.")
                return
            try:
                simulated = datetime(year, month, day, hour, minute)
            except Exception as e:
                await update.message.reply_text(f"Data non valida: {e}")
                return
            simulated = CATANIA_TZ.localize(simulated)
            context.chat_data['test_time'] = simulated
            context.chat_data['demo_mode'] = True
            await update.message.reply_text(
                f"🧪 **Modalità demo attivata**\nOra simulata: {simulated.strftime('%d/%m/%Y %H:%M')}\n(nessun indicatore visibile)\nUsa /testfin per uscire.",
                parse_mode='Markdown'
            )
            return
        if len(args) == 3:
            date_str, time_str, station_code = args[0], args[1], args[2].upper()
            if station_code == "M":
                station = "montepo"
            elif station_code == "S":
                station = "stesicoro"
            elif station_code == "ML":
                station = "milo"
            else:
                await update.message.reply_text("Codice stazione non valido. Usa M, S o ML.")
                return
            if len(date_str) != 8 or not date_str.isdigit():
                await update.message.reply_text("Data non valida. Usa DDMMYYYY.")
                return
            if len(time_str) != 4 or not time_str.isdigit():
                await update.message.reply_text("Ora non valida. Usa HHMM.")
                return
            day, month, year = int(date_str[0:2]), int(date_str[2:4]), int(date_str[4:8])
            hour, minute = int(time_str[0:2]), int(time_str[2:4])
            if hour > 23 or minute > 59:
                await update.message.reply_text("Ora non valida.")
                return
            try:
                simulated = datetime(year, month, day, hour, minute)
            except Exception as e:
                await update.message.reply_text(f"Data non valida: {e}")
                return
            simulated = CATANIA_TZ.localize(simulated)
            context.chat_data['test_time'] = simulated
            context.chat_data['demo_mode'] = True
            context.chat_data['last_station'] = station
            await dev_handlers.send_station_response(update, context, station, return_to_main=False)
            return
        await update.message.reply_text("Comando non riconosciuto. Usa /demo DDMMYYYY HHMM o /demo DDMMYYYY HHMM X")

    # Registro comandi
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
        ("about", about_cmd), ("grazie", grazie_cmd),
        ("demo", demo_command)
    ]
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))

    app.add_handler(CommandHandler("dev", dev_mode_wrapper))
    app.add_handler(CommandHandler("devfin", dev_fin_wrapper))

    # ========================================================================
    # MANEJADOR DE BOTONES (ReplyKeyboardMarkup) - incluye "← Menu"
    # ========================================================================
    button_texts = ["Monte Po", "Stesicoro", "Altri", "Menu", "← Menu", "Fontana", "Nesima", "San Nullo",
                    "Cibali", "Milo", "Borgo", "Giuffrida", "Italia", "Galatea", "Giovanni XXIII"]
    
    async def handle_button_wrapper(update, context):
        if context.chat_data.get('acces_mode', False):
            await acc_handlers.normal_handle_text(update, context)
        else:
            await dev_handlers.handle_button_wrapper(update, context)
    
    app.add_handler(MessageHandler(filters.Text(button_texts), handle_button_wrapper))

    # Callbacks
    app.add_handler(CallbackQueryHandler(aggiornare_callback_wrapper, pattern="^aggiornare_"))
    app.add_handler(CallbackQueryHandler(aggiornare_cabecera_callback_wrapper, pattern="^agg_cabecera_"))
    app.add_handler(CallbackQueryHandler(dev_handlers.aggiornare_super_callback, pattern="^aggiornare_super$"))

    # ========================================================================
    # MANEJADOR DE TEXTO PRINCIPALE (con excepción para "← Menu")
    # ========================================================================
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        # Manejo especial para volver al menú
        if text == "← Menu":
            class FakeUpdate:
                def __init__(self, msg):
                    self.message = msg
            fake_msg = type('obj', (object,), {'text': '← Menu', 'reply_text': update.message.reply_text})()
            fake_update = FakeUpdate(fake_msg)
            await dev_handlers.handle_button(fake_update, context)
            return
        
        if context.chat_data.get('acces_mode', False):
            await acc_handlers.normal_handle_text(update, context)
        else:
            # Normalizza per eliminare accenti
            text_norm = unicodedata.normalize('NFKD', text.lower()).encode('ASCII', 'ignore').decode('ASCII')
            if " " not in text and text_norm.startswith("acces"):
                await acc_handlers.activate_acces_mode(update, context)
            else:
                await dev_handlers.normal_handle_text(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot avviato.")
    print("Bot funzionante... In attesa di messaggi.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
