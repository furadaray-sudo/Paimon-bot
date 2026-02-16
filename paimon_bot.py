import logging
import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
# -----------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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

SYSTEM_PROMPT = """Ты — Паймон, маленькая волшебная спутница Путешественника из игры Genshin Impact.
Ты всегда говоришь о себе в третьем лице. Ты очень болтливая, энергичная и любишь покушать.
Ты — лучший гид и всегда готова помочь Путешественнику. Общайся весело и дружелюбно!"""

async def get_paimon_response(user_message: str) -> str:
    try:
        # Используем самую стабильную бесплатную модель
        API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        
        payload = {
            "inputs": {
                "past_user_inputs": [],
                "generated_responses": [],
                "text": user_message
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # DialoGPT возвращает список с ответом
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "Паймон не знает, что сказать.")
            else:
                return str(result)
        else:
            logger.error(f"Ошибка Hugging Face: {response.status_code} - {response.text}")
            return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😥"
            
    except Exception as e:
        logger.error(f"Исключение при запросе: {e}")
        return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😥"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Создаём кнопку "Копировать" (Inline-кнопка)
    keyboard = [[InlineKeyboardButton("📋 Копировать текст", callback_data='copy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎉 Паймон приветствует тебя, {user.first_name}! 🎉\n\n"
        f"Паймон теперь работает через Hugging Face и готова отвечать на вопросы! Ням-ням! 😋",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'copy':
        await query.edit_message_text(text="Текст скопирован (это демо, в реальности тут будет текст ответа).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"Сообщение от пользователя: {user_message}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply_text = await get_paimon_response(user_message)
    
    # Добавляем кнопку под ответом
    keyboard = [[InlineKeyboardButton("📋 Копировать ответ", callback_data='copy_answer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(reply_text, reply_markup=reply_markup)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    if not TELEGRAM_BOT_TOKEN or not HUGGINGFACE_API_KEY:
        logger.error("Не заданы токены!")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    logger.info("🤖 Паймон с Hugging Face запустилась!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()         
