import logging
import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# -----------------

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')  # бесплатная модель

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# История для каждого пользователя (Gemini не требует, но можно хранить)
user_sessions = {}

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎉 Паймон приветствует тебя, {user.first_name}! 🎉\n\n"
        f"Паймон теперь использует Gemini и готова отвечать на вопросы! Ням-ням! 😋"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"Сообщение от {user_id}: {user_message}")

    # Показываем "печатает..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Используем Gemini для генерации ответа
        response = model.generate_content(
            f"Ты — Паймон из игры Genshin Impact. Говори как Паймон (в третьем лице, весело, иногда упоминай еду). Ответь на сообщение: {user_message}"
        )
        reply = response.text
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        reply = "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😥"

    await update.message.reply_text(reply)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("Не заданы токены!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("🤖 Паймон с Gemini запустилась!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
