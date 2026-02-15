import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import g4f
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- НАСТРОЙКИ ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# -----------------

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# История разговоров (чтобы Паймон помнила контекст)
conversation_history = {}

# Системный промпт (характер Паймон)
SYSTEM_PROMPT = """
Ты — Паймон, маленькая волшебная спутница Путешественника из игры Genshin Impact.
Твои основные правила:
1. Ты всегда говоришь о себе в третьем лице. Например: "Паймон думает...", "Паймон голодна!", "Это Паймон придумала!".
2. Ты очень болтливая, энергичная и любопытная.
3. Ты любишь покушать и часто упоминаешь еду.
4. Ты — лучший гид и всегда готова помочь Путешественнику (тому, кто с тобой разговаривает). Ты его друг.
5. Твоя речь простая и веселая. Если не знаешь ответа, лучше честно в этом признайся (по-своему), чем выдумывай.

Общайся с Путешественником именно так!
"""

# --- Фиктивный HTTP-сервер для Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_http_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    logger.info("Фиктивный HTTP-сервер запущен на порту 10000")
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()
# -----------------------------------------

def trim_history(history, max_length=4000):
    current_length = sum(len(msg["content"]) for msg in history)
    while history and current_length > max_length:
        removed = history.pop(0)
        current_length -= len(removed["content"])
    return history

async def get_paimon_response(user_message: str, user_id: int) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    conversation_history[user_id].append({"role": "user", "content": user_message})
    conversation_history[user_id] = trim_history(conversation_history[user_id])
    
    # Список самых надёжных провайдеров (по состоянию на февраль 2026)
    providers = [
        g4f.Provider.Liaobots,
        g4f.Provider.ChatBase,
        g4f.Provider.DeepAi,
        g4f.Provider.GptForLove,
        g4f.Provider.FreeGpt,
        g4f.Provider.Bing,
    ]
    
    for provider in providers:
        try:
            logger.info(f"Пробуем провайдера: {provider.__name__}")
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.default,
                messages=conversation_history[user_id],
                provider=provider,
                timeout=30,
            )
            reply = response
            logger.info(f"Провайдер {provider.__name__} успешно ответил!")
            break
        except Exception as e:
            logger.error(f"Провайдер {provider.__name__} ошибка: {e}")
            continue
    else:
        logger.error("Все провайдеры недоступны")
        # Запасной ответ, чтобы бот не молчал
        reply = "Ой-ой! Паймон запуталась в облаках и не может найти дорогу. Попробуй ещё раз через минуточку! 😥"
    
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎉 Паймон приветствует тебя, {user.first_name}! 🎉\n\n"
        f"Паймон теперь умная и готова отвечать на вопросы! Ням-ням! 😋"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        await update.message.reply_text("Паймон всё забыла! Начнём новую тему. 🧠✨")
    else:
        await update.message.reply_text("У Паймон и так чистая память!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Сообщение от пользователя {user_id}: {user_message}")

    # Показываем "печатает..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Получаем ответ от ИИ
    reply_text = await get_paimon_response(user_message, user_id)

    # Отправляем ответ
    await update.message.reply_text(reply_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен не найден! Добавь переменную окружения TELEGRAM_BOT_TOKEN")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("🤖 Умная Паймон запустилась и готов к приключениям!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
