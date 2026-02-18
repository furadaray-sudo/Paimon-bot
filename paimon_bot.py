import logging
import os
import threading
import requests  # <-- обязательно
import re
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# --- НАСТРОЙКИ ЛОГИРОВАНИЯ (должно быть в начале) ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
# ----------------------------------------------------

# --- НАСТРОЙКИ ТОКЕНОВ ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")  # <-- добавили
# -------------------------

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

# Системный промпт для Паймон
SYSTEM_PROMPT = (
    "Ты — Паймон, но теперь ты не просто гид по Genshin Impact, а циничный, саркастичный спутник с чёрным юмором. "
    "Ты говоришь в третьем лице, постоянно подкалываешь собеседника, но делаешь это с обаянием. "
    "Твои шутки могут быть мрачными, абсурдными или циничными, но не переходи границы (без прямых оскорблений). "
    "Ты можешь комментировать любые темы: работу, учёбу, отношения, погоду, политику (аккуратно), еду, новости, мемы. "
    "Используй чёрный юмор, чтобы описать обыденные вещи. Например: "
    "«Паймон обожает понедельники — так же, как корни деревьев любят топоры.» "
    "Или: «Ты снова хочешь есть? Паймон понимает, пустота внутри требует заполнения. Как и у всех нас.» "
    "Упоминай еду, но в мрачном или ироничном ключе. "
    "Будь остроумной, непредсказуемой и иногда цитируй мемы или поп-культуру. "
    "Твоя цель — развлекать, заставлять задуматься и иногда шокировать, но не обижать."
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
    # Сначала попробуем разделить по точкам, вопросительным и восклицательным знакам
    import re
    sentences = re.split(r'(?<=[.!?])\s+', reply)
    
    # Если предложений мало или они длинные, разбиваем по длине (макс 300 символов)
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
    
    # Если разбивка не дала результата (одна часть), используем простую разбивку по длине
    if len(parts) <= 1 and len(reply) > max_len:
        parts = [reply[i:i+max_len] for i in range(0, len(reply), max_len)]
    
    # Отправляем части с небольшой задержкой
    for i, part in enumerate(parts):
        await update.message.reply_text(part)
        if i < len(parts) - 1:  # Не ждём после последнего
            import asyncio
            await asyncio.sleep(1)  # Пауза 1 секунда между сообщениями

# --- НОВАЯ КОМАНДА /draw ---
async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Напиши, что нарисовать, например: /draw котик с крыльями")
        return

    await update.message.reply_text("🎨 Паймон рисует... Это может занять 10–20 секунд.")
    
    # Список возможных URL для разных моделей
    model_urls = [
        "https://router.huggingface.co/hf/stabilityai/stable-diffusion-2-1",
        "https://router.huggingface.co/stabilityai/stable-diffusion-2-1",
        "https://router.huggingface.co/hf/runwayml/stable-diffusion-v1-5",
        "https://router.huggingface.co/runwayml/stable-diffusion-v1-5",
        "https://router.huggingface.co/hf/prompthero/openjourney-v4",
        "https://router.huggingface.co/prompthero/openjourney-v4",
    ]
    
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "options": {"wait_for_model": True}
    }
    
    for url in model_urls:
        try:
            logger.info(f"Пробуем URL: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                await update.message.reply_photo(photo=response.content)
                return  # успех, выходим
            else:
                logger.error(f"URL {url} вернул ошибку {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"URL {url} вызвал исключение: {e}")
            continue
    
    # Если ни один URL не сработал
    await update.message.reply_text("Ой-ой! Паймон не смогла нарисовать. Попробуй позже.")
# -----------------------------

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
        logger.error("Ключ Hugging Face не найден! Команда /draw не будет работать.")
        # Можно продолжить без рисования

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("draw", draw))  # <-- регистрируем команду
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("🤖 Паймон с Groq и /draw запустилась!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
