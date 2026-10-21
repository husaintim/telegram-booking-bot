"""Расчёт свободных слотов записи с учётом длительности услуги.
Фрагмент: не запускается отдельно."""
from datetime import datetime, date, time, timedelta

def is_slot_available(slot_start: datetime, service_duration: int, bookings: list) -> bool:

    slot_start = slot_start.replace(second=0, microsecond=0)
    slot_end = slot_start + timedelta(minutes=service_duration)

    for b in bookings:
        b_start = b["start_time"].replace(second=0, microsecond=0)
        b_end = b_start + timedelta(minutes=int(b["duration"]))

        if slot_start < b_end and slot_end > b_start:
            return False

    return True


async def handle_choose_date(query, update, context, user_id: int, chosen_date: str, service_id: int | None):
    """Показывает свободные слоты времени на дату chosen_date с учётом занятости из schedule."""
    from datetime import datetime, timedelta

    state = user_states.setdefault(user_id, {})
    try:
        date_obj = datetime.strptime(chosen_date, "%Y-%m-%d").date()
    except Exception:
        await update.effective_chat.send_message("⚠️ Неверная дата.")
        await show_main_menu(update, context)
        return

    async with db.acquire() as conn:
        master_id = state.get("master_id")
        if not master_id:
            rows = await conn.fetch(
                "SELECT master_id FROM client_masters WHERE client_id=$1;",
                int(user_id)
            )
            if not rows:
                await update.effective_chat.send_message("⚠️ У вас пока нет выбранного мастера.")
                await show_main_menu(update, context)
                return
            if len(rows) > 1:
                kb = [
                    [InlineKeyboardButton(f"👨‍🎨 Мастер #{r['master_id']}", callback_data=f"choose_master_{r['master_id']}")]
                    for r in rows
                ]
                kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
                await query.edit_message_text("У вас несколько мастеров. Выберите, к кому записаться:", reply_markup=InlineKeyboardMarkup(kb))
                return
            master_id = int(rows[0]["master_id"])
            state["master_id"] = master_id
            
        m = await conn.fetchrow(
            "SELECT work_days, work_time, step FROM masters WHERE master_id=$1;",
            master_id
        )
        if not m:
            await update.effective_chat.send_message("⚠️ Мастер не найден.")
            await show_main_menu(update, context)
            return

        work_time = (m["work_time"] or "").strip()  
        step = int(m["step"] or 0)
        if not work_time or step <= 0:
            await update.effective_chat.send_message("⚠️ У мастера пока не настроено расписание.")
            await show_main_menu(update, context)
            return

        service_duration = None
        if service_id:
            row = await conn.fetchrow("SELECT duration FROM services WHERE service_id=$1;", int(service_id))
            if row and row["duration"]:
                service_duration = int(row["duration"])
        if not service_duration:
            service_duration = step  

        try:
            start_s, end_s = work_time.split("-")
            start_dt = datetime.combine(date_obj, datetime.strptime(start_s, "%H:%M").time())
            end_dt   = datetime.combine(date_obj, datetime.strptime(end_s, "%H:%M").time())
            if end_dt <= start_dt:
                await update.effective_chat.send_message("⚠️ Некорректный интервал рабочего времени у мастера.")
                await show_main_menu(update, context)
                return
        except Exception:
            await update.effective_chat.send_message("⚠️ Некорректный формат рабочего времени у мастера.")
            await show_main_menu(update, context)
            return

        busy_rows = await conn.fetch(
            "SELECT time, duration FROM schedule WHERE master_id=$1 AND date=$2;",
            master_id, date_obj
        )
        busy_intervals = []
        for r in busy_rows:
            b_start = datetime.combine(
                date_obj,
                r["time"] if not isinstance(r["time"], str)
                else datetime.strptime(r["time"], "%H:%M").time()
            )
            b_end = b_start + timedelta(minutes=int(r["duration"] or 0))
            busy_intervals.append((b_start, b_end))

        slots = []
        cur = start_dt
        while cur + timedelta(minutes=service_duration) <= end_dt:
            slots.append(cur)
            cur += timedelta(minutes=step)

        now = datetime.now()
        filtered = []
        for s in slots:
            if s.date() == now.date() and s <= now:
                continue
            e = s + timedelta(minutes=service_duration)
            if any(s < b_e and e > b_s for (b_s, b_e) in busy_intervals):
                continue
            filtered.append(s)

        if not filtered:
            kb = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_dates")]]
            await update.effective_chat.send_message("На выбранную дату нет свободных окошек.", reply_markup=InlineKeyboardMarkup(kb))
            await show_main_menu(update, context)
            return

        kb = [[InlineKeyboardButton(s.strftime("%H:%M"), callback_data=f"choose_time_{s.strftime('%H:%M')}")] for s in filtered]
        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_dates")])
        await query.edit_message_text("🕑 Выберите время:", reply_markup=InlineKeyboardMarkup(kb))


