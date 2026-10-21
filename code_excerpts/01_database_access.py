"""Подключение к PostgreSQL и проверка лимита тарифа.
Фрагмент: не запускается отдельно, зависит от остального бота."""
import os
import asyncpg

TARIFFS = {
    "free": {"name": "Старт", "limit": 3,  "price": 0},
    "pro1": {"name": "Рост",  "limit": 7, "price": 299},  
    "pro2": {"name": "Стандарт",  "limit": 15, "price": 339},
    "pro3": {"name": "Профи",  "limit": 20, "price": 449},
    "pro4": {"name": "Элитный",  "limit": 40, "price": 669},
}

async def init_db():
    global db
    if db is None:
        db = await asyncpg.create_pool(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ.get("DB_NAME","bot_db"),
            host=os.environ.get("DB_HOST","localhost")
        )
    return db


async def is_over_limit(master_id: int) -> tuple[bool, str, dict]:
    """
    Проверяет лимит по тарифу для мастера.
    Если подписка истекла, тариф сбрасывается на free.
    Возвращает (over_limit, tariff_code, tariff_info).
    """
    async with db.acquire() as conn:
        sub = await conn.fetchrow(
            "SELECT tarif, aktivedate FROM masters WHERE master_id = $1",
            master_id
        )

        tariff_code = "free"
        if sub:
            tariff_code = sub["tarif"] or "free"
            expire = sub["aktivedate"]

            if expire and expire < datetime.now():
                tariff_code = "free"
                await conn.execute(
                    "UPDATE masters SET tarif = $1, aktivedate = NULL WHERE master_id = $2",
                    "free", master_id
                )

        tariff_info = TARIFFS.get(tariff_code, TARIFFS["free"])
        max_clients = tariff_info["limit"]
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM client_masters WHERE master_id = $1",
            master_id
        )
        count = int(count or 0)

        return (count >= max_clients, tariff_code, tariff_info)


