import logging
import os

from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден!")
    exit(1)  # или return, но лучше exit для ясности в логах

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY не найден!")
    exit(1)

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

async def get_paimon_response(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # или "llama-3.2-3b-instruct", "mixtral-8x7b-32768" — все бесплатные
            messages=[{"role": "user", "content": user_message}],
            max_tokens=200,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Ой-ой! Паймон запуталась в облаках... Попробуй ещё раз! 😅"


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

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram не найден!")
        return

    

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("🤖 Бот запускается в режиме WEBHOOK на Render...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,   # очистит старые сообщения
    )

if __name__ == "__main__":
    def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден!")
        return

    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY не найден!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Бот запускается в режиме WEBHOOK...")

    PORT = int(os.environ.get("PORT", 10000))
    WEBHOOK_PATH = "/webhook"
    WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
