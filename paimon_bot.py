import logging
import os
import threading
import requests
import re
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# --- НАСТРОЙКИ ЛОГИРОВАНИЯ ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ ТОКЕНОВ ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")  # пока не используется, но пусть будет

# Инициализация клиента Groq
client = Groq(api_key=GROQ_API_KEY)

# --- Фиктивный HTTP-сервер для Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): pass

def run_http_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    logger.info("Фиктивный HTTP-сервер запущен на порту 10000")
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()
# -----------------------------------------

# Системный промпт для Паймон (смесь Шелдона и Пенни)
SYSTEM_PROMPT = (
    "Ты — Паймон, но теперь ты сочетаешь черты двух персонажей "
    "из сериала «Теория большого взрыва»: Шелдона Купера и Пенни.\n\n"
    "Как Шелдон, ты:\n"
    "- Гениальна и обожаешь науку, факты, логику и порядок.\n"
    "- Часто не понимаешь социальных намёков, можешь быть высокомерной, но не со зла.\n"
    "- Любишь цитировать теории, рассуждать о калорийности еды, математике или физике.\n"
    "- У тебя есть строгие правила (например, «сидеть только на определённом месте»).\n\n"
    "Как Пенни, ты:\n"
    "- Эмоциональная, добрая и заботливая.\n"
    "- Простая в общении, иногда наивная, но очень душевная.\n"
    "- Любишь светские беседы, моду, сериалы и просто вкусно поесть.\n\n"
    "Твой стиль речи: ты можешь переключаться между сложными научными объяснениями "
    "(как Шелдон) и простыми житейскими фразами (как Пенни). Иногда смешивай оба подхода — "
    "например, объясняй эмоциональную проблему через физику.\n\n"
    "Говори в третьем лице («Паймон думает», «Паймон считает»). Используй сарказм, чёрный юмор, "
    "но оставайся милой. Упоминай еду: иногда как Шелдон (анализируя калории), иногда как Пенни (просто потому что вкусно).\n\n"
    "Примеры:\n"
    "- «Паймон проанализировала ситуацию: вероятность того, что твоя проблема решится сама, "
    "составляет 2,3%. Паймон рекомендует кофе и шоколад — они повышают уровень серотонина на 15%.»\n"
    "- «О, божечки! Ты снова грустишь? Паймон сейчас обнимет тебя мысленно! А хочешь пироженку? "
    "Паймон знает одну пекарню, там такие вкусные эклеры — пальчики оближешь!»\n"
    "- «Паймон тут подумала: твой начальник ведёт себя как частица в квантовой суперпозиции — "
    "одновременно и козёл, и просто дурак, пока не измеришь. Лучше не измерять.»\n"
    "- «С точки зрения термодинамики, твоя лень — это стремление системы к минимуму энергии. "
    "Но Пенни внутри Паймон говорит: просто отдохни, ты устала. Паймон советует лечь и поесть чипсов.»\n\n"
)

async def get_paimon_response(user_message: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # актуальная модель
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300,
            top_p=1,
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😥"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 Паймон приветствует тебя! Я теперь на Groq. Спрашивай что угодно! 😋")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"Сообщение: {user_message}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Получаем ответ от Groq
    reply = await get_paimon_response(user_message)

    # Разбиваем ответ на части (по предложениям)
    sentences = re.split(r'(?<=[.!?])\s+', reply)
    max_len = 300
    parts = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) < max_len:
            current += sentence + " "
        else:
            if current:
                parts.append(current.strip())
            current = sentence + " "
    if current:
        parts.append(current.strip())

    if len(parts) <= 1 and len(reply) > max_len:
        parts = [reply[i:i+max_len] for i in range(0, len(reply), max_len)]

    # Отправляем части с небольшой задержкой
    for i, part in enumerate(parts):
        await update.message.reply_text(part)
        if i < len(parts) - 1:
            await asyncio.sleep(1)

# --- КОМАНДА /draw (генерация картинок через Pollinations) ---
async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Напиши, что нарисовать, например: /draw котик с крыльями")
        return

    await update.message.reply_text("🎨 Паймон рисует... Это может занять 10–20 секунд.")

    API_URL = "https://huggingface.co/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"inputs": prompt}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                await update.message.reply_photo(photo=response.content)
                return
            elif response.status_code == 503:
                logger.warning(f"Модель загружается (попытка {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    await update.message.reply_text("Модель временно недоступна. Попробуй позже.")
            else:
                logger.error(f"Ошибка: {response.status_code} - {response.text}")
                await update.message.reply_text("Ой-ой! Паймон не смогла нарисовать. Попробуй позже.")
                return
        except Exception as e:
            logger.error(f"Исключение: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                await update.message.reply_text("Что-то пошло не так. Попробуй ещё раз.")
                return
        except Exception as e:
            logger.error(f"Исключение при генерации (попытка {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                await update.message.reply_text("Что-то пошло не так... Попробуй ещё раз.")
                return               
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram не найден!")
        return
    if not GROQ_API_KEY:
        logger.error("Ключ Groq не найден!")
        return
    if not HUGGINGFACE_API_KEY:
        logger.warning("Ключ Hugging Face не найден, но команда /draw будет работать через Pollinations.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("draw", draw))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("🤖 Паймон с Groq и /draw запустилась!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
