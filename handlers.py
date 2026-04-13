import asyncio
import time as time_module
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ

# ... (todo el código anterior igual hasta la función refresh_station) ...

# ============================================================================
# FUNCIÓN PARA REFRESCAR SOLO LOS MENSAJES 2 y 3 (sin foto, con botón y reinicio del ciclo)
# ============================================================================
async def refresh_station(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str):
    chat_id = update.effective_chat.id
    # Borrar mensajes 2 y 3 actuales
    msg_ids = context.chat_data.get('refresh_msg_ids')
    if msg_ids:
        for mid in msg_ids:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.chat_data.pop('refresh_msg_ids', None)
    
    # Detener tarea de refresco actual
    if 'refresh_task' in context.chat_data:
        task = context.chat_data['refresh_task']
        if not task.done():
            task.cancel()
        context.chat_data.pop('refresh_task', None)
    context.chat_data['refresh_active'] = False
    
    # Obtener hora actual
    simulated = context.chat_data.get('test_time')
    if simulated:
        if simulated.tzinfo is None:
            simulated = CATANIA_TZ.localize(simulated)
        now = simulated
    else:
        now = datetime.now(CATANIA_TZ)
    
    # Enviar nuevos mensajes 2 y 3 CON botón (show_button=True)
    new_ids = await send_messages_2_and_3(update, estacion_key, now, simulated is not None, show_button=True)
    context.chat_data['refresh_msg_ids'] = new_ids
    
    # Reiniciar el bucle de refresco automático (2 ciclos, con botón)
    context.chat_data['refresh_active'] = True
    task = asyncio.create_task(auto_refresh_loop(update, context, estacion_key, chat_id, "", use_simulated=(simulated is not None), simulated_now=now if simulated else None))
    context.chat_data['refresh_task'] = task

# ============================================================================
# CALLBACK PARA EL BOTÓN INLINE "AGGIORNARE" (refresca sin foto, con botón)
# ============================================================================
async def aggiornare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    estacion_key = query.data.split("_")[1]
    
    # Crear un fake_update con el mensaje real para poder llamar a refresh_station
    fake_update = type('Update', (), {'message': query.message, 'effective_chat': query.message.chat, 'callback_query': query})()
    
    await refresh_station(fake_update, context, estacion_key)

# ... (resto del código igual)
