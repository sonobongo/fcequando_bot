# ============================================================================
# FECHAS ESPECIALES (sobrescribir día de la semana)
# ============================================================================
def get_override_weekday(now: datetime) -> Optional[int]:
    """Devuelve el día de la semana (0=lunes, 6=domingo) que debe usarse para horarios,
       o None si no hay override."""
    month, day = now.month, now.day
    # 31/12 -> viernes (4)
    if month == 12 and day == 31:
        return 4
    # 1/1 -> domingo (6)
    if month == 1 and day == 1:
        return 6
    # 3,4,5/2 -> viernes (4)
    if month == 2 and day in [3, 4, 5]:
        return 4
    # 6/2 -> sábado (5), a menos que sea domingo (6)
    if month == 2 and day == 6:
        # Si el 6 de febrero cae en domingo, usar domingo; si no, sábado
        actual_weekday = now.weekday()
        if actual_weekday == 6:
            return 6
        else:
            return 5
    return None

def get_schedule_list(station: str, now: datetime) -> List[time]:
    # Si hay override, usar el día ficticio
    override = get_override_weekday(now)
    if override is not None:
        if override == 4:
            schedule_list = SCHEDULES[station]["friday"]
        elif override == 5:
            schedule_list = SCHEDULES[station]["saturday"]
        elif override == 6:
            schedule_list = SCHEDULES[station]["sunday"]
        else:
            schedule_list = SCHEDULES[station]["weekday"]
    else:
        # Comportamiento normal
        if is_festivo_nazionale(now):
            schedule_list = SCHEDULES[station]["sunday"]
        else:
            weekday_num = now.weekday()
            if weekday_num == 4:
                schedule_list = SCHEDULES[station]["friday"]
            elif weekday_num == 5:
                schedule_list = SCHEDULES[station]["saturday"]
            elif weekday_num == 6:
                schedule_list = SCHEDULES[station]["sunday"]
            else:
                schedule_list = SCHEDULES[station]["weekday"]
    # Resto igual (primer tren, etc.)
    current_time = now.time()
    first_train = schedule_list[0] if schedule_list else None
    if first_train and current_time < first_train:
        yesterday = now - timedelta(days=1)
        y_override = get_override_weekday(yesterday)
        if y_override is not None:
            if y_override == 4:
                yesterday_list = SCHEDULES[station]["friday"]
            elif y_override == 5:
                yesterday_list = SCHEDULES[station]["saturday"]
            elif y_override == 6:
                yesterday_list = SCHEDULES[station]["sunday"]
            else:
                yesterday_list = SCHEDULES[station]["weekday"]
        else:
            y_weekday = yesterday.weekday()
            if y_weekday == 4:
                yesterday_list = SCHEDULES[station]["friday"]
            elif y_weekday == 5:
                yesterday_list = SCHEDULES[station]["saturday"]
            elif y_weekday == 6:
                yesterday_list = SCHEDULES[station]["sunday"]
            else:
                yesterday_list = SCHEDULES[station]["weekday"]
        if any(t.hour < 6 for t in yesterday_list):
            return yesterday_list
    return schedule_list

def is_metro_closed(now: datetime, station: str) -> Tuple[bool, Optional[datetime], str]:
    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    
    if is_closed_all_day(now):
        tomorrow = now + timedelta(days=1)
        open_h, open_m = get_opening_time(tomorrow, station)
        next_open = datetime.combine(tomorrow.date(), time(open_h, open_m))
        next_open = CATANIA_TZ.localize(next_open)
        return (True, next_open, "")
    
    if is_new_years_eve(now):
        if now.hour >= 23 or now.hour < 3:
            open_h, open_m = get_opening_time(now, station)
            next_open = datetime.combine(now.date(), time(open_h, open_m))
            if next_open <= now:
                next_open = datetime.combine(now.date() + timedelta(days=1), time(open_h, open_m))
            next_open = CATANIA_TZ.localize(next_open)
            special_msg = "🚇 Non ci sono informazioni disponibili. Ricorda che oggi l'ultima metropolitana è partita alle 03:00."
            return (True, next_open, special_msg)
    
    # Rangos especiales donde el metro está abierto (sin horarios reales)
    if (now.month == 1 and now.day == 1 and 1 <= now.hour < 3) or \
       (now.month == 2 and now.day in [4,5,6] and 1 <= now.hour < 2):
        # Devolvemos abierto (False) y un mensaje especial que se mostrará en el handler
        return (False, None, "special_open_until_3am")
    
    # Cierre forzado de 01:00 a 06:00 (excepto los rangos especiales de arriba)
    if 1 <= now.hour < 6:
        open_h, open_m = get_opening_time(now, station)
        next_open = datetime.combine(now.date(), time(open_h, open_m))
        if next_open <= now:
            next_open = datetime.combine(now.date() + timedelta(days=1), time(open_h, open_m))
        next_open = CATANIA_TZ.localize(next_open)
        return (True, next_open, "🚇 La metropolitana è chiusa in questo momento.")
    
    # Resto de la lógica normal
    current_time = now.time()
    open_h, open_m = get_opening_time(now, station)
    close_h, close_m = get_closing_time(now, station)
    opening_time = time(open_h, open_m)
    closing_time = time(close_h, close_m)
    
    if close_h < open_h or (close_h == open_h and close_m < open_m):
        if current_time >= opening_time or current_time < closing_time:
            return (False, None, "")
        else:
            next_open = datetime.combine(now.date(), opening_time)
            if next_open <= now:
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open, "")
    else:
        if current_time >= closing_time or current_time < opening_time:
            if current_time < opening_time:
                next_open = datetime.combine(now.date(), opening_time)
            else:
                next_open = datetime.combine(now.date() + timedelta(days=1), opening_time)
            next_open = CATANIA_TZ.localize(next_open)
            return (True, next_open, "")
        return (False, None, "")
