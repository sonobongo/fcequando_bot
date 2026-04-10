import asyncio
from telegram import Update
from telegram.ext import ContextTypes

async def cmd_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envía dos veces el GIF prueba6.gif desde GitHub.
    """
    gif_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/prueba6.gif"
    
    # Enviar primera vez
    await update.message.reply_animation(animation=gif_url)
    # Pequeña pausa para que no se solapen (opcional)
    await asyncio.sleep(0.5)
    # Enviar segunda vez
    await update.message.reply_animation(animation=gif_url)
