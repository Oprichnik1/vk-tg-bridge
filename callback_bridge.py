import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiohttp import web
import aiohttp

# ==========================
#      КОНФИГУРАЦИЯ
# ==========================

TG_TOKEN = "8541886168:AAE__V_mWtC6l1H1dozTwXfmX3XLddtFlWY"
TG_CHAT_ID = -1003124432188

VK_GROUP_ID = 223916702
VK_CONFIRMATION_CODE = "4755cd93"
VK_SECRET_KEY = "aaQ13axAPQcczQa"

VK_GROUP_TOKEN = "vk1.a.YsC4drNa7Ph_ct22SAeMlc6ApbbYMlj1g7mfGxrw3PMWVybVO8OYpRsuOZBtmUa4R1cEcivC_DGsr9O2Wkhkv4ogl4rS7SmNx-ASf7r9GPkPUdgf_IC7mfk0z8y1xt3cvf4SQprbeKdwBdiQI7v8LZhEXMVmFP9PU8cUct9KieIkfkB72zPGxmbdG_iWtPhFrPZOXbruViYnm-kIVCpapg"
VK_PEER_ID = 2000000001

MAX_TOKEN = "заглушка"
MAX_CHAT_ID = -70642362567392

logging.basicConfig(level=logging.INFO)

# ==========================
#     ИНИЦИАЛИЗАЦИЯ
# ==========================

tg_bot = Bot(token=TG_TOKEN)
dp = Dispatcher()


class MaxBot:
    def __init__(self, token):
        self.base_url = "https://platform-api.max.ru"
        self.token = token

    async def send_message(self, chat_id, text):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {"chat_id": chat_id, "text": text}

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/messages"
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status not in [200, 201]:
                    logging.error(f"⚠️ Max Error {resp.status}: {await resp.text()}")
                    return None
                return await resp.json()


max_bot = MaxBot(MAX_TOKEN)

# ==========================
#   VK → TG: получение имени
# ==========================

async def get_vk_name(user_id: int):
    params = {
        "user_ids": user_id,
        "fields": "first_name,last_name",
        "v": "5.199"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.vk.com/method/users.get",
            params=params,
            headers={"Authorization": f"Bearer {VK_GROUP_TOKEN}"}
        ) as resp:
            data = await resp.json()
            try:
                user = data["response"][0]
                return f"{user['first_name']} {user['last_name']}"
            except:
                return f"ID {user_id}"


# ==========================
#   TELEGRAM → VK
# ==========================

async def send_to_vk(text: str):
    params = {
        "peer_id": VK_PEER_ID,
        "message": text,
        "random_id": 0,
        "v": "5.199"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.vk.com/method/messages.send",
            params=params,
            headers={"Authorization": f"Bearer {VK_GROUP_TOKEN}"},
        ) as resp:
            data = await resp.json()
            if "error" in data:
                logging.error(f"Ошибка TG→VK: {data}")
            else:
                logging.info("TG → VK отправлено")


@dp.message()
async def handle_tg_message(message: Message):
    formatted = (
        "📩 Новое сообщение из Telegram\n"
        f"👤 От: {message.from_user.full_name}\n"
        f"💬 Текст: {message.text}"
    )

    await send_to_vk(formatted)

    try:
        await max_bot.send_message(MAX_CHAT_ID, formatted)
    except:
        pass


# ==========================
#   VK CALLBACK SERVER
# ==========================

async def vk_callback(request: web.Request):
    data = await request.json()
    logging.info(f"VK EVENT: {data}")

    if data.get("secret") != VK_SECRET_KEY and data.get("type") != "confirmation":
        return web.Response(status=403, text="forbidden")

    event_type = data.get("type")

    if event_type == "confirmation":
        return web.Response(text=VK_CONFIRMATION_CODE)

    if event_type == "message_new":
        msg = data["object"]["message"]
        text = msg.get("text", "")
        from_id = msg.get("from_id")

        vk_name = await get_vk_name(from_id)

        formatted = (
            "📩 Новое сообщение из VK\n"
            f"👤 От: {vk_name}\n"
            f"💬 Текст: {text}"
        )

        try:
            await tg_bot.send_message(TG_CHAT_ID, formatted)
            logging.info("VK → TG отправлено")
        except Exception as e:
            logging.error(f"Ошибка VK→TG: {e}")

        try:
            await max_bot.send_message(MAX_CHAT_ID, formatted)
        except:
            pass

        return web.Response(text="ok")

    return web.Response(text="ok")


async def start_web_server():
    app = web.Application()
    app.router.add_post("/", vk_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logging.info("VK Callback server started on port 8080")


# ==========================
#           MAIN
# ==========================

async def main():
    logging.info("Bridge (Callback) Started 🚀")

    await tg_bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        dp.start_polling(tg_bot),
        start_web_server()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
