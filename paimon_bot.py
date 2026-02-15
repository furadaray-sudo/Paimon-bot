import logging
import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
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
        API_URL = "https://router.huggingface.co/hf/microsoft/Phi-3-mini-4k-instruct"
        headers = {"Authorization": f"Bearer {
            
        }"}
        
        payload = {
            "inputs": f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{user_message}\n<|assistant|>\n",
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"].split("<|assistant|>\n")[-1].strip()
                return str(result[0])
            elif isinstance(result, dict) and "generated_text" in result:
                return result["generated_text"].split("<|assistant|>\n")[-1].strip()
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
    await update.message.reply_text(
        f"🎉 Паймон приветствует тебя, {user.first_name}! 🎉\n\n"
        f"Паймон теперь работает через Hugging Face и готова отвечать на вопросы! Ням-ням! 😋"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"Сообщение от пользователя: {user_message}")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply_text = await get_paimon_response(user_message)
    await update.message.reply_text(reply_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    if not TELEGRAM_BOT_TOKEN or not HUGGINGFACE_API_KEY:
        logger.error("Не заданы токены!")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("🤖 Паймон с Hugging Face запустилась!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
