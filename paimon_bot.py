import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import g4f

# --- НАСТРОЙКИ ---
# Токен мы будем хранить в переменной окружения (это безопасно)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# -----------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для истории разговоров
conversation_history = {}

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
    
    try:
        # Пробуем одного провайдера
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=conversation_history[user_id],
            provider=g4f.Provider.GeekGpt,
            timeout=120,
        )
        reply = response
    except Exception as e:
        logger.error(f"Ошибка с GeekGpt: {e}")
        try:
            # Если не сработал, пробуем Bing
            response = await g4f.ChatCompletion.create_async(
                model=g4f.models.default,
                messages=conversation_history[user_id],
                provider=g4f.Provider.Bing,
                timeout=120,
            )
            reply = response
        except Exception as e2:
            logger.error(f"Ошибка с Bing: {e2}")
            return "Ой-ой! Паймон запуталась в облаках. Попробуй ещё раз через минуточку! 😥"
    
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎉 Паймон приветствует тебя, {user.first_name}! 🎉\n\n"
        f"Паймон теперь твой личный бесплатный гид! Можешь спрашивать о чём угодно. Ням-ням! 😋"
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
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await get_paimon_response(user_message, user_id)
    await update.message.reply_text(reply)

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
    print("🤖 Паймон запустилась и готов к приключениям!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
