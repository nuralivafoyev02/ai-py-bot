import os
import logging
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes
)
from google import genai
from google.genai.errors import APIError

# 1. KONFIGURATSIYA
# O'zingizning kalitlaringizni bu yerga kiriting
# Yoki ularni muhit o'zgaruvchilari (Environment Variables) sifatida belgilang.

# Telegram botingizning Tokeni (BotFather dan olasiz)
TELEGRAM_BOT_TOKEN = "8142445503:AAEd5ToX34JS9Q9zP7uMXsljNWJH0l2O0j4" 

# Google Gemini API Kaliti
# os.environ.get('GEMINI_API_KEY') orqali olinishi tavsiya etiladi
GEMINI_API_KEY = "AIzaSyAs3WE0NyNn_uuNQG2KVUA_deQbYGEOG-8" 

# Loglarni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Gemini AI mijozi (Client)
try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY bo'sh. Iltimos, kalitni kiriting.")
        
    # Gemini mijozini yaratish
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Ishlatiladigan model
    GEMINI_MODEL = "gemini-2.5-flash"
    
    # Dastlabki Suhbat Konteksti (Sizning botingiz xarakteri)
    SYSTEM_PROMPT = (
        "Siz foydalanuvchiga har tomonlama yordam beruvchi, xushmuomala va bilimdon "
        "sun'iy intellekt yordamchisiz. Barcha savollarga o'zbek tilida javob bering."
        "Foydalanuvchilar bilan do'stona va professional ohangda muloqot qiling."
    )
    
    # Generatsiya konfiguratsiyasi
    GENERATION_CONFIG = {
        "system_instruction": SYSTEM_PROMPT,
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }

    logger.info("Gemini AI Mijozi muvaffaqiyatli yuklandi.")
    
except ValueError as e:
    logger.error(f"Konfiguratsiya xatosi: {e}")
except Exception as e:
    logger.error(f"Gemini mijozini yuklashda kutilmagan xato: {e}")
    client = None

# --- 2. Buyruq Yordamchilari (Handlers) ---

# /start buyrug'i uchun
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi /start buyrug'ini yuborganda ishga tushadi."""
    welcome_message = (
        f"Assalomu alaykum, **{update.effective_user.first_name}**👋!\n\n"
        "Men sun'iy intellekt yordamchisiman. "
        "Menga istalgan savolingizni berishingiz mumkin🤓\n\n"
        "Xo'sh, sizga qanday yordam bera olaman?"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    logger.info(f"Yangi foydalanuvchi: {update.effective_user.id} - {update.effective_user.username}")


# Foydalanuvchi matn yuborganda ishga tushadi
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi matn xabariga Gemini AI yordamida javob beradi."""
    
    if not client:
        await update.message.reply_text("Kechirasiz, AI xizmati hozirda mavjud emas.")
        return

    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    logger.info(f"Chat {chat_id} dan kelgan xabar: {user_message[:50]}...")
    
    # Foydalanuvchiga javob tayyorlanayotgani haqida xabar berish
    typing_action = context.application.bot.send_chat_action(
        chat_id=chat_id, 
        action='typing'
    )
    await typing_action
    
    try:
        # Gemini AI ga so'rov yuborish
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=GENERATION_CONFIG,
        )

        # Javobni Telegramga yuborish
        await update.message.reply_text(response.text)
        logger.info(f"Chat {chat_id} ga javob yuborildi.")

    except APIError as e:
        error_message = f"AI dan javob olishda xato yuz berdi: {e}"
        await update.message.reply_text(
            "Kechirasiz, AI bilan bog'lanishda xato yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )
        logger.error(error_message)
        
    except Exception as e:
        error_message = f"Kutilmagan xato: {e}"
        await update.message.reply_text(
            "Kechirasiz, kutilmagan ichki xato yuz berdi."
        )
        logger.error(error_message)


# Xatolarni qayta ishlash
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatcher tomonidan kiritilgan barcha xatolarni yozadi."""
    logger.error(f"Update: {update} - Xato: {context.error}", exc_info=context.error)
    
    # Foydalanuvchiga xato haqida xabar yuborish (agar update mavjud bo'lsa)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Kechirasiz, xatolik yuz berdi. Iltimos, urinishni takrorlang."
        )


# --- 3. Asosiy Funktsiya ---

def main() -> None:
    """Botni ishga tushiradi."""
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "O'ZINGIZNING_TELEGRAM_BOT_TOKENINGIZNI_KIRITING":
        logger.error("TELEGRAM_BOT_TOKEN o'rnatilmagan.")
        print("Iltimos, bot tokeningizni 'bot.py' faylida kiriting.")
        return
        
    # Application ni yaratish va token bilan ishlash
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Buyruq yordamchilarini qo'shish
    application.add_handler(CommandHandler("start", start))
    
    # Matn xabarlari yordamchisi (barcha matn xabarlarini qayta ishlaydi)
    # Rasm yoki video kabi boshqa turdagi xabarlar e'tiborga olinmaydi
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Xatolarni qayta ishlash yordamchisi
    application.add_error_handler(error_handler)

    # Botni so'rov rejimida (Polling mode) ishga tushirish
    print("Bot ishga tushirildi. Xabarlarni kutmoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()