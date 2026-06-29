import asyncio
import time as time_module
import logging
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from horarios_logic import *
from horarios_logic import CATANIA_TZ, get_motta_trips, get_humanitas_trips

logger = logging.getLogger(__name__)

async def store_id(context, message):
    if not hasattr(message, 'message_id'):
        return
    ids = context.chat_data.get('last_message_ids', [])
    ids.append(message.message_id)
    context.chat_data['last_message_ids'] = ids[-10:]

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
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_busmotta.png"
    try:
        msg1 = await update.message.reply_photo(photo=img_url, caption="🚌 Linea Motta")
    except Exception:
        msg1 = await update.message.reply_text("🚌 Linea Motta")
    await store_id(context, msg1)
    msg = get_motta_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_motta")
    ]])
    msg2 = await update.message.reply_text(msg, reply_markup=keyboard, parse_mode='Markdown')
    await store_id(context, msg2)


async def aggiornare_motta_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = get_simulated_now(context)
    msg = get_motta_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_motta")
    ]])
    try:
        await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=keyboard)
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
    # 1. Viaggio attualmente in corso: NES <= now < NES2
    for trip in trips:
        nes_time = trip.get('NES')
        nes2_time = trip.get('NES2')
        if nes_time is None or nes2_time is None:
            continue
        if nes_time <= current_time < nes2_time:
            active_trip = trip
            break
    # 2. Prossimo viaggio
    if active_trip is None:
        for trip in trips:
            if trip.get('NES') and trip['NES'] > current_time:
                active_trip = trip
                break
    # 3. Fallback
    if active_trip is None and trips:
        active_trip = trips[-1]

    # Determinar posición del bus (fracción entre 0 y 3)
    bus_pos = -1
    now_dt = datetime.combine(now.date(), current_time)
    segments = [('NES', 'HUM'), ('HUM', 'CEN'), ('CEN', 'NES2')]
    for idx, (s1, s2) in enumerate(segments):
        t1 = active_trip.get(s1)
        t2 = active_trip.get(s2)
        if t1 is None or t2 is None:
            continue
        t1_dt = datetime.combine(now.date(), t1)
        t2_dt = datetime.combine(now.date(), t2)
        if t1_dt <= now_dt < t2_dt:
            seg_total = (t2_dt - t1_dt).total_seconds()
            seg_transcurridos = (now_dt - t1_dt).total_seconds()
            frac = seg_transcurridos / seg_total if seg_total > 0 else 0
            bus_pos = idx + frac
            break
    # Se non in nessun segmento, controllare se prima o dopo il viaggio
    if bus_pos == -1:
        nes_dt = datetime.combine(now.date(), active_trip['NES']) if active_trip.get('NES') else None
        nes2_dt = datetime.combine(now.date(), active_trip['NES2']) if active_trip.get('NES2') else None
        if nes_dt and now_dt < nes_dt:
            bus_pos = -1  # non ancora partito
        elif nes2_dt and now_dt >= nes2_dt:
            bus_pos = 3   # viaggio terminato, mostrare a NES2

    # Construir línea visual (longitudes de tramos: 4, 4, 3)
    seg_lengths = [4, 4, 3]
    parts = []
    for i in range(4):
        # Parada
        if bus_pos != -1 and abs(bus_pos - i) < 0.01:
            parts.append("🚍")
        else:
            parts.append("⚪")
        # Tramo
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
    # Horarios (NES2 ya es un valor real)
    t1 = active_trip['NES'].strftime('%H:%M') if active_trip['NES'] else '--:--'
    t2 = active_trip['HUM'].strftime('%H:%M') if active_trip['HUM'] else '--:--'
    t3 = active_trip['CEN'].strftime('%H:%M') if active_trip['CEN'] else '--:--'
    t4 = active_trip['NES2'].strftime('%H:%M') if active_trip['NES2'] else '--:--'
    lines.append(f"{t1:<16}{t2:<18}{t3:<13}{t4}")

    return "\n".join(lines)


async def send_humanitas_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = get_simulated_now(context)
    # Mensaje 1: foto fija
    img_url = "https://raw.githubusercontent.com/sonobongo/fcequando_bot/main/st_bushumanitas.png"
    caption = "🚌 Linea Humanitas"
    try:
        msg1 = await update.message.reply_photo(photo=img_url, caption=caption, parse_mode='Markdown')
    except Exception:
        msg1 = await update.message.reply_text(caption, parse_mode='Markdown')
    if msg1:
        await store_id(context, msg1)

    # Mensaje 2: estado actual del autobús
    msg2_text = get_humanitas_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_humanitas")
    ]])
    msg2 = await update.message.reply_text(msg2_text, reply_markup=keyboard, parse_mode='Markdown')
    if msg2:
        await store_id(context, msg2)


async def aggiornare_humanitas_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = get_simulated_now(context)
    msg = get_humanitas_status(now)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_humanitas")
    ]])
    try:
        await query.edit_message_text(text=msg, parse_mode='Markdown', reply_markup=keyboard)
    except Exception:
        pass


# ============================================================================
# LÍNEA BRT-1 (Parcheggio Due Obelischi → Stesicoro → Parcheggio) circular
# ============================================================================
import os as _os
import json as _json

_BRT1_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'brt1_horarios.json')
_BRT1_DATA = {}

def _load_brt1():
    global _BRT1_DATA
    if not _os.path.exists(_BRT1_FILE):
        return
    with open(_BRT1_FILE, 'r', encoding='utf-8') as f:
        _BRT1_DATA = _json.load(f)

_load_brt1()

def get_brt1_status(now: datetime) -> str:
    if not _BRT1_DATA:
        return "🚌 Dati BRT-1 non disponibili."

    if now.tzinfo is None:
        now = CATANIA_TZ.localize(now)
    else:
        now = now.astimezone(CATANIA_TZ)
    current_time = now.time()

    bus_icon = "🔻" if now.second % 2 == 0 else "⬇️"

    stops = _BRT1_DATA['stops']
    offsets = _BRT1_DATA['offsets']
    departures = _BRT1_DATA['departures']

    # Trovare tutti i tratti con bus attivi (più corse simultanee)
    bus_tratti = set()
    bus_fermate = set()
    appena_passati = set()
    N = len(stops)

    for i in range(N - 1):
        s_i = stops[i]
        s_i1 = stops[i + 1]
        off_i = offsets[s_i]
        off_i1 = offsets[s_i1]
        for dep in departures:
            base = datetime.strptime(dep, "%H:%M")
            t_i = (base + timedelta(seconds=off_i)).time()
            t_i1 = (base + timedelta(seconds=off_i1)).time()
            if t_i <= current_time < t_i1:
                dt_i1 = CATANIA_TZ.localize(datetime.combine(now.date(), t_i1))
                secs = (dt_i1 - now).total_seconds()
                if secs <= 30:
                    bus_fermate.add(i + 1)
                else:
                    bus_tratti.add(i)
                break

    # Appena passato (≤30s fa) per ogni fermata
    for i, stop in enumerate(stops):
        off = offsets[stop]
        for dep in departures:
            base = datetime.strptime(dep, "%H:%M")
            t = (base + timedelta(seconds=off)).time()
            dt = CATANIA_TZ.localize(datetime.combine(now.date(), t))
            secs_ago = (now - dt).total_seconds()
            if 0 < secs_ago <= 30:
                appena_passati.add(i)
                break

    # Fallback se nessun bus trovato
    if not bus_tratti and not bus_fermate:
        bus_tratti.add(0)

    lines = ["🚌 **BRT-1 – Monitoraggio in tempo reale**\n"]
    for i, stop in enumerate(stops):
        # Prossimo orario per questa fermata
        off = offsets[stop]
        next_t = None
        for dep in departures:
            base = datetime.strptime(dep, "%H:%M")
            t = (base + timedelta(seconds=off)).time()
            if t > current_time:
                next_t = t
                break

        if i in bus_fermate:
            s = int((CATANIA_TZ.localize(datetime.combine(now.date(), next_t)) - now).total_seconds()) if next_t else 0
            lines.append(f"⚪️ **{stop}**  {bus_icon} {max(0,s)//60:02d}:{max(0,s)%60:02d}")
        elif i in appena_passati:
            lines.append(f"⚪️ **{stop}**  _Appena passato_")
        elif next_t:
            lines.append(f"⚪️ {stop}  {next_t.strftime('%H:%M')}")
        else:
            lines.append(f"⚪️ {stop}  —")

        if i < N - 1:
            lines.append(f"▫️  {bus_icon}" if i in bus_tratti else "▫️")

    return "\n".join(lines)


async def auto_update_brt1(context, chat_id, message_id, cycles=40, interval=3):
    last_sent_msg = None
    for _ in range(cycles):
        for _ in range(interval):
            await asyncio.sleep(1)
            if not context.chat_data.get('brt1_active', False):
                return
        if not context.chat_data.get('brt1_active', False):
            return
        now = get_simulated_now(context)
        new_msg = get_brt1_status(now)
        if new_msg != last_sent_msg:
            try:
                await context.bot.edit_message_text(
                    text=new_msg, chat_id=chat_id,
                    message_id=message_id, parse_mode='Markdown'
                )
                last_sent_msg = new_msg
            except Exception as e:
                logger.error(f"Errore aggiornamento BRT-1: {e}")
                break
    if context.chat_data.get('brt1_active', False):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Aggiornare", callback_data="aggiornare_brt1")
        ]])
        try:
            await context.bot.edit_message_text(
                text=new_msg, chat_id=chat_id,
                message_id=message_id, parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception:
            pass
        context.chat_data['brt1_active'] = False
        context.chat_data.pop('brt1_task', None)


async def send_brt1_response(update, context):
    if 'brt1_task' in context.chat_data:
        context.chat_data['brt1_active'] = False
        try:
            context.chat_data['brt1_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('brt1_task', None)
    now = get_simulated_now(context)
    msg = get_brt1_status(now)
    result = await update.message.reply_text(msg, parse_mode='Markdown')
    message_id = result.message_id
    chat_id = update.effective_chat.id
    context.chat_data['brt1_active'] = True
    task = asyncio.create_task(auto_update_brt1(context, chat_id, message_id))
    context.chat_data['brt1_task'] = task


async def aggiornare_brt1_callback(update, context):
    query = update.callback_query
    await query.answer()
    if 'brt1_task' in context.chat_data:
        context.chat_data['brt1_active'] = False
        try:
            context.chat_data['brt1_task'].cancel()
        except Exception:
            pass
        context.chat_data.pop('brt1_task', None)
    now = get_simulated_now(context)
    msg = get_brt1_status(now)
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    context.chat_data['brt1_active'] = True
    task = asyncio.create_task(auto_update_brt1(context, chat_id, message_id))
    context.chat_data['brt1_task'] = task
    try:
        await context.bot.edit_message_text(
            text=msg, chat_id=chat_id,
            message_id=message_id, parse_mode='Markdown'
        )
    except Exception:
        pass
