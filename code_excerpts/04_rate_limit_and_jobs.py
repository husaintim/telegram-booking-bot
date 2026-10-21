"""Ограничение частоты запросов (декоратор) и фоновые напоминания.
Фрагмент: не запускается отдельно."""
import time, functools
from collections import defaultdict, deque

CALLBACK_RPM_PER_USER = 40

def limit_user_rpm(max_per_min=CALLBACK_RPM_PER_USER):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(update, context, *args, **kwargs):
                uid = getattr(getattr(update, "effective_user", None), "id", None)
                if uid:
                    q = _user_calls[uid]
                    now = time.time()
                    while q and now - q[0] > 60:
                        q.popleft()
                    if len(q) >= max_per_min:
                        try:
                            if getattr(update, "callback_query", None):
                                await update.effective_chat.send_message("⏳ Слишком часто. Попробуйте позже.", show_alert=False)
                                await show_main_menu(update, context)
                        except:
                            pass
                        return
                    q.append(now)
                return await func(update, context, *args, **kwargs)
            return wrapper
        return func
    return decorator


async def send_reminders(application):
    remind_before = timedelta(minutes=60)
    while True:
        now = datetime.now()

        query = """
            SELECT appointment_id, client_id, date, time, status
            FROM appointments
            WHERE lower(status) = 'запланировано';
        """
        appointments = await db.fetch(query)
        for appt in appointments:
            try:
                client_id = int(appt["client_id"])
                appt_id = int(appt["appointment_id"])
                appt_date = appt["date"]
                appt_time = appt["time"]

                if isinstance(appt_date, str):
                    appt_date = datetime.strptime(appt_date, "%Y-%m-%d").date()
                if isinstance(appt_time, str):
                    appt_time = datetime.strptime(appt_time, "%H:%M").time()

                appt_datetime = datetime.combine(appt_date, appt_time)
                diff = appt_datetime - now

                if timedelta(0) <= diff <= remind_before:
                    keyboard = [
                        [InlineKeyboardButton("🏠 Главное меню", callback_data="reminder_main_menu")]
                    ]
                    await application.bot.send_message(
                        chat_id=client_id,
                        text=f"⏰ Напоминание! У вас запись сегодня в {appt_time.strftime('%H:%M')}.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    update_query = """
                        UPDATE appointments
                        SET status = 'отправлено'
                        WHERE appointment_id = $1;
                    """
                    await db.execute(update_query, appt_id)

            except Exception as e:
                print(f"⚠️ Ошибка при отправке напоминания: {e}")

        await asyncio.sleep(60) 


