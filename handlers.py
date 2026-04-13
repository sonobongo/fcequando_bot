# ... (todo el código anterior igual hasta la función send_messages_2_and_3)

async def send_messages_2_and_3(update: Update, estacion_key: str, now: datetime, simulated: bool = False, show_button: bool = False):
    print(f"DEBUG send_messages_2_and_3: estacion={estacion_key}, show_button={show_button}")
    msg2, msg3, key_mp, time_mp, key_st, time_st, mins_mp, mins_st = build_temporary_messages(now, estacion_key)
    
    msg2_obj = await send_message_2(update, msg2, key_mp, time_mp, mins_mp, estacion_key)
    await asyncio.sleep(0.5)
    
    # Añadir botón solo si es estación intermedia y show_button True
    if estacion_key not in ["montepo", "stesicoro"] and show_button:
        print(f"DEBUG: Añadiendo botón para {estacion_key}")
        keyboard_inline = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Aggiornare", callback_data=f"aggiornare_{estacion_key}")]
        ])
        msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=keyboard_inline)
    else:
        print(f"DEBUG: NO se añade botón para {estacion_key} (show_button={show_button})")
        msg3_obj = await send_message_3(update, msg3, key_st, time_st, mins_st, estacion_key, reply_markup=None)
    
    return (msg2_obj.message_id, msg3_obj.message_id)

# ... (resto del código)

async def auto_refresh_loop(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, chat_id: int, station_display_name: str, use_simulated: bool = False, simulated_now: datetime = None):
    print(f"DEBUG auto_refresh_loop: iniciada para {estacion_key}")
    for ciclo in range(2):
        await asyncio.sleep(30)
        print(f"DEBUG auto_refresh_loop: ciclo {ciclo+1} para {estacion_key}")
        if context.chat_data.get('cancel_refresh', False):
            break
        msg_ids = context.chat_data.get('refresh_msg_ids')
        if msg_ids:
            for mid in msg_ids:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
        if use_simulated and simulated_now:
            now = simulated_now
            if now.tzinfo is None:
                now = CATANIA_TZ.localize(now)
        else:
            now = datetime.now(CATANIA_TZ)
        new_ids = await send_messages_2_and_3(update, estacion_key, now, use_simulated, show_button=True)
        context.chat_data['refresh_msg_ids'] = new_ids
    context.chat_data['refresh_active'] = False
    context.chat_data.pop('refresh_task', None)
    context.chat_data.pop('cancel_refresh', None)
    print(f"DEBUG auto_refresh_loop: finalizada para {estacion_key}")

# ... (el resto igual)
