import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

# ---------------------------------------
# CONFIG — ВСТАВЬ СВОИ ЗНАЧЕНИЯ
# ---------------------------------------
TG_TOKEN = "8541886168:AAE__V_mWtC6l1H1dozTwXfmX3XLddtFlWY"
TG_CHAT_ID = -1003124432188

VK_GROUP_ID = 223916702
VK_CONFIRMATION_CODE = "4755cd93"
VK_SECRET_KEY = "aaQ13axAPQcczQa"

VK_GROUP_TOKEN = "vk1.a.YsC4drNa7Ph_ct22SAeMlc6ApbbYMlj1g7mfGxrw3PMWVybVO8OYpRsuOZBtmUa4R1cEcivC_DGsr9O2Wkhkv4ogl4rS7SmNx-ASf7r9GPkPUdgf_IC7mfk0z8y1xt3cvf4SQprbeKdwBdiQI7v8LZhEXMVmFP9PU8cUct9KieIkfkB72zPGxmbdG_iWtPhFrPZOXbruViYnm-kIVCpapg"
VK_PEER_ID = 2000000001

MAX_TOKEN = "заглушка"
MAX_CHAT_ID = -70642362567392
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------
# TG → VK
# ---------------------------------------

async def send_to_vk(message_text: str):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.199",
        "peer_id": VK_PEER_ID,
        "random_id": 0,
        "message": message_text
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=params) as resp:
            data = await resp.json()
            if "error" in data:
                logger.error(f"⚠️ VK Error: {data}")
            else:
                logger.info("VK ← TG отправлено")


@dp.message()
async def tg_message_handler(message: types.Message):
    text = message.text or ""
    await send_to_vk(text)
    logger.info("TG → VK отправлено")


# ---------------------------------------
# VK → TG
# ---------------------------------------

async def send_vk_to_tg(sender_name: str, message_text: str):
    formatted = f"📨 VK: *{sender_name}*\n{message_text}"
    await bot.send_message(TG_CHAT_ID, formatted, parse_mode=ParseMode.MARKDOWN)
    logger.info("TG ← VK отправлено")


async def vk_callback_handler(request):
    data = await request.json()

    # confirmation
    if data.get("type") == "confirmation":
        return web.Response(text="confirmation")

    # new message
    if data.get("type") == "message_new":
        msg = data["object"]["message"]
        sender_id = msg["from_id"]
        text = msg.get("text", "")

        # получаем имя отправителя
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.vk.com/method/users.get",
                params={
                    "access_token": VK_TOKEN,
                    "v": "5.199",
                    "user_ids": sender_id
                }
            ) as resp:
                user_data = await resp.json()
                user = user_data["response"][0]
                sender_name = f"{user['first_name']} {user['last_name']}"

        await send_vk_to_tg(sender_name, text)

    return web.Response(text="ok")


# ---------------------------------------
# SERVER
# ---------------------------------------

async def start_app():
    app = web.Application()
    app.router.add_post("/", vk_callback_handler)
    return app


if __name__ == "__main__":
    web.run_app(start_app(), port=8080)
