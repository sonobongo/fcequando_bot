async def send_station_response(update: Update, context: ContextTypes.DEFAULT_TYPE, estacion_key: str, simulated_now: datetime = None, return_to_main: bool = True):
    now = simulated_now if simulated_now is not None else datetime.now(CATANIA_TZ)
    
    warning = get_closing_warning(now)
    if warning:
        await update.message.reply_text(warning, reply_markup=keyboard_main if return_to_main else keyboard_altri)
    
    special_msg = SANT_AGATA.get("message", "") + "\n\n" if is_sant_agata(now) else ""
    
    if is_closed_all_day(now):
        msg = f"{special_msg}🚇 Oggi la metropolitana è chiusa tutto il giorno.\n🕒 Riaprirà domani mattina."
        await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    # Caso especial para Monte Po y Stesicoro (salida desde la estación)
    if estacion_key in ["montepo", "stesicoro"]:
        station = "Montepo" if estacion_key == "montepo" else "Stesicoro"
        closed, next_open = is_metro_closed(now, station)
        if closed:
            mins_to_open = int((next_open - now).total_seconds() // 60)
            if mins_to_open <= 60:
                first_train, _, _, has_first = get_next_departure(station, now)
                if not has_first:
                    first_train, _, _, _ = get_next_departure(station, now + timedelta(days=1))
                station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
                msg = f"{special_msg}🚇 La metropolitana è chiusa in questo momento. Il primo treno da {station_display} partirà alle {first_train.strftime('%H:%M')}."
            else:
                msg = f"{special_msg}🚇 La metropolitana è chiusa in questo momento.\n🕒 Riaprirà alle {next_open.strftime('%H:%M')}."
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        next_dep, minutes, seconds, has_trains = get_next_departure(station, now)
        if not has_trains:
            msg = f"{special_msg}🚇 Non ci sono più treni oggi. Il servizio riprenderà domani mattina."
            await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
            return
        
        station_display = "Monte Po" if station == "Montepo" else "Stesicoro"
        dest = "Stesicoro" if station == "Montepo" else "Monte Po"
        
        # --- NUEVA LÓGICA PARA MENSAJE DE ANDÉN ---
        if minutes == 0:
            # El tren está en el andén (sale en menos de 60 segundos)
            if seconds == 0:
                msg = f"{special_msg}🚇 Il treno è in binario. Partirà subito."
            else:
                msg = f"{special_msg}🚇 Il treno è in binario. Partirà tra meno di un minuto."
            # Mostrar el siguiente tren si existe
            next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
            if has2:
                time_str2 = format_time(min2, sec2)
                msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
            else:
                msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        elif minutes == 0 and seconds < 30:
            # Caso residual: treno appena partito (no debería ocurrir porque minutes==0 ya cubre todo, pero lo dejamos)
            next2, min2, sec2, has2 = get_next_departure(station, now + timedelta(seconds=30))
            if has2:
                msg = f"{special_msg}🚇 Il treno è appena partito da {station_display}. Il prossimo per {dest} sarà alle {next2.strftime('%H:%M')}."
            else:
                msg = f"{special_msg}🚇 Il treno è appena partito da {station_display}. Non ci sono altri treni oggi."
        else:
            time_str = format_time(minutes, seconds)
            # Mostrar mensaje principal
            if minutes < NEXT_TRAIN_THRESHOLD:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}."
            elif minutes < SHORT_TIME_THRESHOLD:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}."
            else:
                msg = f"{special_msg}🚇 Prossimo treno PER {dest} parte tra {time_str}, alle {next_dep.strftime('%H:%M')}."
            # Mostrar siguiente tren si existe y faltan menos de NEXT_TRAIN_THRESHOLD minutos
            if minutes < NEXT_TRAIN_THRESHOLD:
                next2, min2, sec2, has2 = get_next_departure_after(station, now, next_dep.time())
                if has2:
                    time_str2 = format_time(min2, sec2)
                    msg += f"\n\n🚆 Il prossimo treno successivo partirà tra {time_str2}, alle {next2.strftime('%H:%M')}."
                else:
                    msg += f"\n\n🚆 Questo è l'ultimo treno della giornata."
        
        last_msg = get_last_train_message(now)
        if last_msg and not is_sant_agata(now):
            msg += f"\n\n{last_msg}"
        await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri)
        return
    
    # Para estaciones intermedias (incluye Milo)
    info_mp, info_st = get_next_train_at_station(now, estacion_key)
    nombre = NOMBRE_MOSTRAR.get(estacion_key, estacion_key.capitalize())
    
    msg = f"{special_msg}🚆 **Prossimi treni a {nombre}**\n\n"
    
    # Dirección hacia Stesicoro (tren que viene de Monte Po)
    if info_mp:
        paso_mp, mins, secs, next_info = info_mp
        time_str = format_time(mins, secs)
        if mins == 0:
            msg += f"🚇 **Per Stesicoro**: treno in arrivo.\n"
        else:
            msg += f"🚇 **Per Stesicoro**: prossimo treno passa tra {time_str}, alle {paso_mp.strftime('%H:%M')}.\n"
        # Mostrar siguiente tren si faltan menos de NEXT_TRAIN_THRESHOLD minutos
        if mins < NEXT_TRAIN_THRESHOLD and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🚫 **Per Stesicoro**: nessun treno in arrivo al momento.\n"
    
    # Dirección hacia Monte Po (tren que viene de Stesicoro)
    if info_st:
        paso_st, mins, secs, next_info = info_st
        time_str = format_time(mins, secs)
        if mins == 0:
            msg += f"🚇 **Per Monte Po**: treno in arrivo.\n"
        else:
            msg += f"🚇 **Per Monte Po**: prossimo treno passa tra {time_str}, alle {paso_st.strftime('%H:%M')}.\n"
        if mins < NEXT_TRAIN_THRESHOLD and next_info:
            paso2, mins2, secs2 = next_info
            time_str2 = format_time(mins2, secs2)
            msg += f"   Il successivo passerà tra {time_str2}, alle {paso2.strftime('%H:%M')}.\n"
    else:
        msg += f"🚫 **Per Monte Po**: nessun treno in arrivo al momento.\n"
    
    last_msg = get_last_train_message(now)
    if last_msg and not is_sant_agata(now):
        msg += f"\n{last_msg}"
    
    await update.message.reply_text(msg, reply_markup=keyboard_main if return_to_main else keyboard_altri, parse_mode='Markdown')
