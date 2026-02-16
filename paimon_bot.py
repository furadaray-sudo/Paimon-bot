import logging
import os
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler  # можно оставить, но не используем
import threading  # можно удалить, если не используешь больше

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# === НОВОЕ ДЛЯ RENDER + WEBHOOK ===
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_PATH = "/webhook"
# RENDER_EXTERNAL_HOSTNAME — автоматически даёт Render (например paimon-bot-1.onrender.com)
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}{WEBHOOK_PATH}"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# === ТВОИ ФУНКЦИИ (оставляем как есть) ===
async def get_paimon_response(user_message: str) -> str:
    try:
        API_URL = "https://router.huggingface.co/hf-inference/models/gpt2"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        payload = {"inputs": user_message}
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "Паймон не знает, что сказать.")
            else:
                return str(result)
        else:
            logger.error(f"Ошибка Hugging Face: {response.status_code} - {response.text}")
            return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😅"
    except Exception as e:
        logger.error(f"Исключение: {e}")
        return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😅"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я простой бот. Напиши мне что-нибудь.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"Сообщение: {user_message}")
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    reply_text = await get_paimon_response(user_message)
    await update.message.reply_text(reply_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

# === ГЛАВНАЯ ФУНКЦИЯ (полностью новая) ===
def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram не найден!")
        return

    if not HUGGINGFACE_API_KEY:
        logger.warning("HUGGINGFACE_API_KEY не найден! Ответы от HF не будут работать.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("🤖 Бот запускается в режиме WEBHOOK на Render...")

    # Запускаем webhook (автоматически установит set_webhook + запустит сервер)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,   # очистит старые сообщения
    )

if __name__ == "__main__":
    main()
