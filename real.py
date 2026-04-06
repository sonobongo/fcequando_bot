import asyncio
from datetime import datetime
from horarios_logic import get_next_departure, is_metro_closed, format_time, CATANIA_TZ

# Diccionario global para almacenar tareas activas (chat_id -> task)
active_real_tasks = {}

async def real_time_updater(chat_id: int, context, estacion_key: str):
    """
    Envía actualizaciones cada minuto sobre el próximo tren desde la estación elegida.
    Se detiene cuando el tren sale (minutos == 0) o el usuario envía /realfin.
    """
    station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
    station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
    dest = "Stesicoro" if station == "Montepo" else "Monte Po"
    
    while True:
        # Verificar si la tarea fue cancelada manualmente
        if chat_id not in active_real_tasks:
            break
        
        now = datetime.now(CATANIA_TZ)
        closed, _ = is_metro_closed(now, station)
        if closed:
            await context.bot.send_message(chat_id=chat_id, text=f"🚇 La metropolitana è chiusa. Monitoraggio terminato.")
            break
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            await context.bot.send_message(chat_id=chat_id, text=f"🚇 Non ci sono più treni oggi. Monitoraggio terminato.")
            break
        
        time_str = format_time(minutes, seconds)
        
        if minutes == 0 and seconds < 30:
            await context.bot.send_message(chat_id=chat_id, text=f"🚇 Il treno per {dest} sta partendo ora! Monitoraggio terminato.")
            break
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"🚇 Prossimo treno per {dest} tra **{time_str}** (alle {next_dep.strftime('%H:%M')}).", parse_mode='Markdown')
        
        # Esperar 60 segundos hasta la siguiente actualización
        await asyncio.sleep(60)
    
    # Limpiar la tarea al terminar
    if chat_id in active_real_tasks:
        del active_real_tasks[chat_id]