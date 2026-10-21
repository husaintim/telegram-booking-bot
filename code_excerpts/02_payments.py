"""Оплата тарифов через Telegram Payments: инвойс, pre-checkout, успешный платёж.
Тестовый режим провайдера. Фрагмент: не запускается отдельно."""
import os

PROVIDER_TOKEN = os.environ["PAYMENT_PROVIDER_TOKEN"]
CURRENCY = "RUB"
TARIFFS = {
    "free": {"name": "Старт", "limit": 3,  "price": 0},
    "pro1": {"name": "Рост",  "limit": 7, "price": 299},
    "pro2": {"name": "Стандарт",  "limit": 15, "price": 339},
    "pro3": {"name": "Профи",  "limit": 20, "price": 449},
    "pro4": {"name": "Элитный",  "limit": 40, "price": 669},
}

def marketing_price(value: float) -> int:
    base = math.ceil(value)
    last_digit = base % 10
    if last_digit == 9:
        return base
    if last_digit == 0:
        if base % 100 == 0:
            return base - 1
        else:
            return base - 1
    else:
        return base + (9 - last_digit)


async def send_tariff_invoice(chat_id: int, tarif_code: str, months: int, context):
    t = TARIFFS[tarif_code]
    total_rub = t["price"] * months
    if months == 3:
        total_rub = marketing_price(t["price"] * 3 * 0.93)
    elif months == 12:
        total_rub = marketing_price(t["price"] * 12 * 0.8)
    else:
        total_rub = t["price"] * months

    if total_rub <= 0:
        return False

    prices = [LabeledPrice(f"{t['name']} — {months} мес", int(total_rub * 100))]  

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=f"Подписка {t['name']}",
        description=f"Доступ до {t['limit']} клиентов — {months} мес",
        provider_token=PROVIDER_TOKEN,
        currency=CURRENCY,
        prices=prices,
        start_parameter=f"tarif_{tarif_code}_{months}",
        payload=f"tarif|{tarif_code}|{months}"
    )
    return True


async def precheckout_handler(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    payment = update.message.successful_payment
    payload = payment.invoice_payload or "" 
    inv_payload = getattr(payment, "invoice_payload", "") or ""
    if not inv_payload:
        inv_payload = payload

    parts = inv_payload.split("|")
    if len(parts) >= 3 and parts[0] == "tarif":
        tarif_code = parts[1]
        months = int(parts[2])
        user_id = update.effective_user.id
        expire = datetime.now() + timedelta(days=30*months)

        await init_db()
        await db.execute(
            "UPDATE masters SET tarif = $1, aktivedate = $2 WHERE master_id = $3",
            tarif_code, expire, int(user_id)
        )

        await update.message.reply_text(
            f"✅ Оплата принята! Тариф <b>{TARIFFS[tarif_code]['name']}</b> активирован до {expire.strftime('%d.%m.%Y')}.",
            parse_mode="HTML"
        )
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Оплата получена, но не удалось обработать payload. Свяжитесь с техподдержкой.")


