import asyncio
import time as time_module
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ, get_motta_trips, get_humanitas_trips

logger = logging.getLogger(__name__)

# ============================================================================
# FUNCIÓN AUXILIAR PARA OBTENER LA HORA SIMULADA (importada de handlers_dev)
# ============================================================================
def get_simulated_now(context: ContextTypes.DEFAULT_TYPE) -> datetime:
    # Esta función debe ser idéntica a la de handlers_dev.
    # La replicamos aquí para evitar dependencia circular.
    if 'test_time' in context.chat_data:
        sim = context.chat_data['test_time']
        if sim.tzinfo is None:
            sim = CATANIA_TZ.localize(sim)
        return sim
    if 'test_live_base' in context.chat_data:
        base = context.chat_data['test_live_base']
        base_real = context.chat_data.get('test_live_real')
        if base_real is None:
            base_real = datetime.now(CATANIA_TZ)
            context.chat_data['test_live_real'] = base_real
        if base.tzinfo is None:
            base = CATANIA_TZ.localize(base)
        delta = datetime.now(CATANIA_TZ) - base_real
        return base + delta
    return datetime.now(CATANIA_TZ)

# ============================================================================
# LÍNEA MOTTA (Misterbianco-Motta S.Anastasia) – monitor simple
# ============================================================================
def get_motta_status(now: datetime) -> str:
    trips = get_motta_trips(now)
    if not trips:
        return "🚌 Servizio Motta non disponibile (solo feriali)."

    current_time = now.time()
    stops = ['MTP', 'MSB', 'MSA', 'MSB2', 'MTP2']
    active_trip = None
    for trip in trips:
        dep_time = trip.get('MTP')
        arr_time = trip.get('MTP2')
        if dep_time is None or arr_time is None:
            continue
        if dep_time <= current_time < arr_time:
            active_trip = trip
            break
    if active_trip is None:
        for trip in trips:
            if trip.get('MTP') and trip['MTP'] > current_time:
                active_trip = trip
                break
        if active_trip is None and trips:
            active_trip = trips[-1]

    bus_pos = -1
    if active_trip['MSB2'] is not None:
        for i in range(len(stops)-1):
            t1 = active_trip[stops[i]]
            t2 = active_trip[stops[i+1]]
            if t1 is None or t2 is None:
                continue
            t1_dt = datetime.combine(now.date(), t1)
            t2_dt = datetime.combine(now.date(), t2)
            now_dt = datetime.combine(now.date(), current_time)
            if t1 <= current_time < t2:
                seg_total = (t2_dt - t1_dt).total_seconds()
                seg_transcurridos = (now_dt - t1_dt).total_seconds()
                frac = seg_transcurridos / seg_total if seg_total > 0 else 0
                bus_pos = i + frac
                break
            elif current_time == t2:
                bus_pos = i + 1
                break
        else:
            if current_time < active_trip['MTP']:
                bus_pos = -1
            elif current_time >= active_trip['MTP2']:
                bus_pos = len(stops) - 1
    else:
        segmentos = [(0, 1), (1, 2), (2, 4)]
        for idx1, idx2 in segmentos:
            t1 = active_trip[stops[idx1]]
            t2 = active_trip[stops[idx2]]
            if t1 is None or t2 is None:
                continue
            t1_dt = datetime.combine(now.date(), t1)
            t2_dt = datetime.combine(now.date(), t2)
            now_dt = datetime.combine(now.date(), current_time)
            if t1 <= current_time < t2:
                seg_total = (t2_dt - t1_dt).total_seconds()
                seg_transcurridos = (now_dt - t1_dt).total_seconds()
                frac = seg_transcurridos / seg_total if seg_total > 0 else 0
                if idx2 - idx1 == 1:
                    bus_pos = idx1 + frac
                else:
                    bus_pos = 2 + frac * 2
                break
            elif current_time == t2:
                bus_pos = idx2
                break
        else:
            if current_time < active_trip['MTP']:
                bus_pos = -1
            elif current_time >= active_trip['MTP2']:
                bus_pos = len(stops) - 1

    parts = []
    for i in range(5):
        if bus_pos != -1 and abs(bus_pos - i) < 0.01:
            parts.append("🚍")
        else:
            parts.append("⚪")
        if i < 4:
            if bus_pos != -1 and i < bus_pos < i+1:
                tercio = int((bus_pos - i) * 3)
                if tercio > 2:
                    tercio = 2
                tramo_chars = ["▫"] * 3
                tramo_chars[tercio] = "🚍"
                parts.append("".join(tramo_chars))
            else:
                parts.append("▫▫▫")
    emoji_line = "".join(parts)

    lines = [emoji_line]
    lines.append("MTP        MSB          MSA         MSB          MTP")

    t1 = active_trip['MTP'].strftime('%H:%M') if active_trip['MTP'] else '--:--'
    t2 = active_trip['MSB'].strftime('%H:%M') if active_trip['MSB'] else '--:--'
    t3 = active_trip['MSA'].strftime('%H:%M') if active_trip['MSA'] else '--:--'
    t4 = active_trip['MSB2'].strftime('%H:%M') if active_trip['MSB2'] else '--:--'
    t5 = active_trip['MTP2'].strftime('%H:%M') if active_trip['MTP2'] else '--:--'
    times_line = t1.ljust(11) + t2.ljust(14) + t3.ljust(14) + t4.ljust(14) + t5
    lines.append(times_line)

    return "\n".join(lines)


async def send_motta_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = get_simulated_now(context)
    msg = get_motta_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_motta")
    ]])
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode='Markdown')


async def aggiornare_motta_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = get_simulated_now(context)
    msg = get_motta_status(now)
    try:
        await query.edit_message_text(
            text=msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_motta")
            ]])
        )
    except Exception:
        pass


# ============================================================================
# LÍNEA HUMANITAS (Nesima - Humanitas - Centro Sicilia) – monitor simple
# ============================================================================
def get_humanitas_status(now: datetime) -> str:
    trips = get_humanitas_trips(now)
    if not trips:
        return "🚌 Servizio Humanitas non disponibile (lun-sab, no festivi)."

    current_time = now.time()
    stops = ['NES', 'HUM', 'CEN', 'NES2']
    active_trip = None
    for trip in trips:
        if trip.get('NES') and trip.get('NES') <= current_time:
            cen_time = trip.get('CEN')
            if cen_time:
                end_time = (datetime.combine(now.date(), cen_time) + timedelta(hours=1)).time()
                if current_time < end_time:
                    active_trip = trip
                    break
        elif trip.get('NES') and trip['NES'] > current_time:
            active_trip = trip
            break
    if active_trip is None and trips:
        active_trip = trips[-1]

    bus_pos = -1
    if active_trip['NES'] is not None and active_trip['CEN'] is not None:
        if current_time <= active_trip['CEN']:
            for i in range(2):
                t1 = active_trip[stops[i]]
                t2 = active_trip[stops[i+1]]
                if t1 is None or t2 is None:
                    continue
                t1_dt = datetime.combine(now.date(), t1)
                t2_dt = datetime.combine(now.date(), t2)
                now_dt = datetime.combine(now.date(), current_time)
                if t1 <= current_time < t2:
                    seg_total = (t2_dt - t1_dt).total_seconds()
                    seg_transcurridos = (now_dt - t1_dt).total_seconds()
                    frac = seg_transcurridos / seg_total if seg_total > 0 else 0
                    bus_pos = i + frac
                    break
                elif current_time == t2:
                    bus_pos = i + 1
                    break
            else:
                if current_time < active_trip['NES']:
                    bus_pos = -1
                elif current_time == active_trip['CEN']:
                    bus_pos = 2
        else:
            cen_dt = datetime.combine(now.date(), active_trip['CEN'])
            seconds_since_cen = (datetime.combine(now.date(), current_time) - cen_dt).total_seconds()
            total_return = 30 * 60
            frac = min(seconds_since_cen / total_return, 1.0)
            bus_pos = 2 + frac

    seg_lengths = [4, 4, 3]
    parts = []
    for i in range(4):
        if bus_pos != -1 and abs(bus_pos - i) < 0.01:
            parts.append("🚍")
        else:
            parts.append("⚪")
        if i < 3:
            n = seg_lengths[i]
            if bus_pos != -1 and i < bus_pos < i+1:
                tercio = int((bus_pos - i) * n)
                if tercio >= n:
                    tercio = n - 1
                tramo_chars = []
                for j in range(n):
                    if j == tercio:
                        tramo_chars.append("🚍")
                    else:
                        tramo_chars.append("▫")
                parts.append("".join(tramo_chars))
            else:
                parts.append("▫" * n)
    emoji_line = "".join(parts)

    lines = [emoji_line]
    lines.append(f"{'NES':<16}{'HUM':<18}{'CEN':<13}{'NES'}")
    t1 = active_trip['NES'].strftime('%H:%M') if active_trip['NES'] else '--:--'
    t2 = active_trip['HUM'].strftime('%H:%M') if active_trip['HUM'] else '--:--'
    t3 = active_trip['CEN'].strftime('%H:%M') if active_trip['CEN'] else '--:--'
    t4 = '--:--'
    lines.append(f"{t1:<16}{t2:<18}{t3:<13}{t4}")

    return "\n".join(lines)


async def send_humanitas_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = get_simulated_now(context)
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/PUBLI_CS.png"
    caption = "Prossime partenze autobus, Nesima - Humanitas - Centro Sicilia:"
    try:
        msg1 = await update.message.reply_photo(photo=img_url, caption=caption, parse_mode='Markdown')
    except Exception:
        msg1 = await update.message.reply_text(caption, parse_mode='Markdown')
    if msg1:
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg1.message_id)

    msg2_text = get_humanitas_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_humanitas")
    ]])
    msg2 = await update.message.reply_text(msg2_text, reply_markup=keyboard, parse_mode='Markdown')
    if msg2:
        if 'all_msg_ids' not in context.chat_data:
            context.chat_data['all_msg_ids'] = []
        context.chat_data['all_msg_ids'].append(msg2.message_id)


async def aggiornare_humanitas_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = get_simulated_now(context)
    msg = get_humanitas_status(now)
    try:
        await query.edit_message_text(
            text=msg,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_humanitas")
            ]])
        )
    except Exception:
        pass