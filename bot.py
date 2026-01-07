import asyncio
import logging
import re
import json
import os
from datetime import datetime
import jdatetime

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

# =========================
# تنظیمات
# =========================
TOKEN = "8067799402:AAEX_mfioxHr5i7smS34P8wogAEtpN6hexg"
LEADS_CHAT_ID = -1003453467027
START_PHOTO_PATH = "assets/start.png"
INTRO_VOICE_PATH = "assets/intro.ogg"
LEADS_FILE = "leads.json"

# حالت‌ها
SHOW_MAIN_MENU, WAIT_CONTACT, ASK_NAME, CONFIRM_PHONE, ENTER_PHONE, ASK_EDU, ASK_JOB, ASK_FIELD, WAIT_RESUME, POST_RESUME_MENU, ASK_QUESTION = range(11)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =========================
# ابزارهای کمکی
# =========================
def normalize_phone(phone: str) -> str | None:
    if not phone:
        return None
    p = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not re.fullmatch(r"\+?\d{10,15}", p):
        return None
    if p.startswith("00"):
        p = "+" + p[2:]
    if p.startswith("0") and len(p) == 11:
        p = "+98" + p[1:]
    elif p.startswith("98") and not p.startswith("+98"):
        p = "+" + p
    return p

def save_lead(row: dict):
    leads = []
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, "r", encoding="utf-8") as f:
                leads = json.load(f) or []
        except json.JSONDecodeError:
            leads = []
    if not any(x["chat_id"] == row["chat_id"] for x in leads):
        leads.append(row)
        with open(LEADS_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)

def get_datetime_info():
    now = datetime.now()
    miladi = now.strftime("%Y-%m-%d - %H:%M")
    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    shamssi = jalali.strftime("%Y/%m/%d - %H:%M")
    return miladi, shamssi

async def send_initial_lead(context: ContextTypes.DEFAULT_TYPE, data: dict):
    username = f"@{data.get('username', 'ندارد')}" if data.get('username') else "ندارد"
    miladi, shamssi = get_datetime_info()
    msg = (
        "✅ لید جدید دریافت شد\n"
        f"آیدی تلگرام: {data.get('user_id', 'نامشخص')}\n"
        f"یوزرنیم: {username}\n"
        f"نام کامل: {data.get('name', 'نامشخص')}\n"
        f"شماره تماس: {data.get('phone', 'نامشخص')}\n"
        f"تحصیلات: {data.get('edu', 'نامشخص')}\n"
        f"شغل فعلی: {data.get('job', 'نامشخص')}\n"
        f"زمینه تخصصی: {data.get('field', 'نامشخص')}\n"
        f"تاریخ میلادی: {miladi}\n"
        f"تاریخ شمسی: {shamssi}"
    )
    await context.bot.send_message(chat_id=LEADS_CHAT_ID, text=msg)

async def send_resume_lead(context: ContextTypes.DEFAULT_TYPE, data: dict, file_id: str, file_type: str):
    username = f"@{data.get('username', 'ندارد')}" if data.get('username') else "ندارد"
    miladi, shamssi = get_datetime_info()
    caption = (
        "📄 رزومه جدید دریافت شد\n"
        f"یوزرنیم: {username}\n"
        f"نام: {data.get('name', 'نامشخص')}\n"
        f"تاریخ میلادی: {miladi}\n"
        f"تاریخ شمسی: {shamssi}"
    )
    if file_type == "document":
        await context.bot.send_document(chat_id=LEADS_CHAT_ID, document=file_id, caption=caption)
    elif file_type == "photo":
        await context.bot.send_photo(chat_id=LEADS_CHAT_ID, photo=file_id, caption=caption)

async def send_question_to_leads(context: ContextTypes.DEFAULT_TYPE, data: dict, question: str):
    username = f"@{data.get('username', 'ندارد')}" if data.get('username') else "ندارد"
    miladi, shamssi = get_datetime_info()
    msg = (
        "❓ سوال جدید از کاربر\n"
        f"یوزرنیم: {username}\n"
        f"نام: {data.get('name', 'نامشخص')}\n"
        f"متن سوال:\n{question}\n\n"
        f"تاریخ میلادی: {miladi}\n"
        f"تاریخ شمسی: {shamssi}"
    )
    await context.bot.send_message(chat_id=LEADS_CHAT_ID, text=msg)

# =========================
# کیبوردهای بهینه‌شده
# =========================
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["📝 تکمیل فرم درخواست"],
        ["ℹ️ اطلاعات بیشتر"],
        ["🎖 آشنایی با ویژگی ویزاها"]
    ], resize_keyboard=True)

def get_post_resume_keyboard():
    return ReplyKeyboardMarkup([
        ["❓ پرسیدن سوال"],
        ["🔄 فرآیند کاری"],
        ["✅ گام پایانی"]
    ], resize_keyboard=True)

def get_after_question_keyboard():
    return ReplyKeyboardMarkup([
        ["🔄 فرآیند کاری"],
        ["✅ گام پایانی"]
    ], resize_keyboard=True)

def get_after_process_keyboard():
    return ReplyKeyboardMarkup([
        ["❓ پرسیدن سوال"],
        ["✅ گام پایانی"]
    ], resize_keyboard=True)

def get_final_full_keyboard():
    return ReplyKeyboardMarkup([
        ["❓ پرسیدن سوال", "📄 ارسال رزومه"],
        ["🔄 فرآیند کاری"],
        ["ℹ️ اطلاعات بیشتر", "🎖 آشنایی با ویژگی ویزاها"]
    ], resize_keyboard=True)

# =========================
# دو حالت استارت
# =========================
async def start_normal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(START_PHOTO_PATH, "rb"))
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open(INTRO_VOICE_PATH, "rb"))

    await update.message.reply_text(
        "🌟 اینجا فرصتی منحصر به فرد برای شما وجود دارد!\n"
        "شما می‌توانید از ویزای استعدادیابی جهانی انگلستان بهره‌برداری کنید و به جمع یک تیم حرفه‌ای بپیوندید. 🚀",
        reply_markup=get_main_keyboard()
    )
    return SHOW_MAIN_MENU

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # پاک کردن تمام اطلاعات قبلی برای تست

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(START_PHOTO_PATH, "rb"))
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open(INTRO_VOICE_PATH, "rb"))

    await update.message.reply_text(
        "🧪 حالت تست فعال شد!\n"
        "تمام اطلاعات قبلی پاک شد و از اول شروع می‌کنیم.\n\n"
        "🌟 اینجا فرصتی منحصر به فرد برای شما وجود دارد!\n"
        "شما می‌توانید از ویزای استعدادیابی جهانی انگلستان بهره‌برداری کنید و به جمع یک تیم حرفه‌ای بپیوندید. 🚀",
        reply_markup=get_main_keyboard()
    )
    return SHOW_MAIN_MENU

# =========================
# مدیریت منوی اصلی
# =========================
async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "📝 تکمیل فرم درخواست" or text == "✅ آماده تکمیل فرم هستم":
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await update.message.reply_text(
            "عالی! 🎉 برای شروع، لطفاً شماره تماس خود را ارسال کنید:",
            reply_markup=kb
        )
        return WAIT_CONTACT

    elif text == "ℹ️ اطلاعات بیشتر":
        await update.message.reply_text(
            "ما یک تیم حرفه‌ای و با تجربه هستیم که به دنبال جذب افراد با استعداد می‌گردیم. 🌟\n"
            "اگر شرایط مناسبی داشته باشید، با شما همکاری خواهیم کرد.\n"
            "برای شروع بررسی، لطفاً اطلاعات خود را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup([
                ["✅ آماده تکمیل فرم هستم"],
                ["🎖 آشنایی با ویژگی ویزاها"]
            ], resize_keyboard=True)
        )
        return SHOW_MAIN_MENU

    elif text == "🎖 آشنایی با ویژگی ویزاها":
        await update.message.reply_text(
            "🎖 ویزای استعدادیابی جهانی انگلستان (Global Talent Visa) فرصتی فوق‌العاده برای افراد مستعد است:\n\n"
            "✅ بدون نیاز به سرمایه‌گذاری کلان\n"
            "✅ بدون نیاز به پیشنهاد شغلی از کارفرما\n"
            "✅ مسیر سریع به اقامت دائم\n"
            "✅ امکان همراهی خانواده\n"
            "✅ آزادی کامل در انتخاب شغل یا راه‌اندازی کسب‌وکار\n"
            "✅ دسترسی به بازار کار و منابع بین‌المللی\n\n"
            "این ویزا برای متخصصان برجسته در حوزه‌های مختلف طراحی شده است.",
            reply_markup=ReplyKeyboardMarkup([
                ["✅ آماده تکمیل فرم هستم"],
                ["ℹ️ اطلاعات بیشتر"]
            ], resize_keyboard=True)
        )
        return SHOW_MAIN_MENU

    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های زیر را انتخاب کنید 👇", reply_markup=get_main_keyboard())
        return SHOW_MAIN_MENU

# =========================
# مراحل فرم
# =========================
async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.contact.phone_number)
    if not phone:
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 ارسال شماره تماس", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await update.message.reply_text(
            "❌ شماره معتبر نیست.\nلطفاً مجدداً شماره تماس خود را وارد کنید:",
            reply_markup=kb
        )
        return WAIT_CONTACT

    context.user_data["phone"] = phone
    context.user_data["user_id"] = update.effective_user.id
    context.user_data["username"] = update.effective_user.username or "ندارد"

    await update.message.reply_text("1️⃣ نام و نام خانوادگی را وارد کنید:", reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    phone = context.user_data["phone"]
    ikb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ تایید شماره", callback_data="phone_ok"),
        InlineKeyboardButton("✏️ تغییر شماره", callback_data="phone_edit"),
    ]])
    await update.message.reply_text(f"با این شماره تماس بگیریم؟\n{phone}", reply_markup=ikb)
    return CONFIRM_PHONE

async def phone_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "phone_ok":
        await query.edit_message_text("2️⃣ تحصیلات و رشته را وارد کنید:")
        return ASK_EDU
    else:
        await query.edit_message_text("شماره جدید را به صورت عددی وارد کنید:")
        return ENTER_PHONE

async def on_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text)
    if not phone:
        await update.message.reply_text("❌ شماره معتبر نیست.")
        return ENTER_PHONE
    context.user_data["phone"] = phone
    await update.message.reply_text("2️⃣ تحصیلات و رشته را وارد کنید:")
    return ASK_EDU

async def ask_edu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["edu"] = update.message.text.strip()
    await update.message.reply_text("3️⃣ شغل فعلی را وارد کنید:")
    return ASK_JOB

async def ask_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"] = update.message.text.strip()
    await update.message.reply_text("4️⃣ زمینه تخصصی خود را وارد کنید (مثلاً فناوری، هنر، مدیریت، پزشکی و ...):")
    return ASK_FIELD

async def ask_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["field"] = update.message.text.strip()
    data = context.user_data

    save_lead({
        "chat_id": update.effective_chat.id,
        "user_id": data["user_id"],
        "username": data["username"],
        "phone": data["phone"],
        "name": data["name"],
        "edu": data["edu"],
        "job": data["job"],
        "field": data["field"],
        "created_at": datetime.now().isoformat(),
    })
    await send_initial_lead(context, data)

    kb = ReplyKeyboardMarkup([
        ["📄 ارسال رزومه"],
        ["⏳ بعداً ارسال می‌کنم"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        "🙌 ممنون از ارسال اطلاعات اولیه!\n"
        "حالا برای بررسی دقیق‌تر، لطفاً رزومه خود را ارسال کنید.",
        reply_markup=kb
    )
    return WAIT_RESUME

# =========================
# مدیریت رزومه
# =========================
async def handle_resume_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "📄 ارسال رزومه":
        await update.message.reply_text(
            "لطفاً رزومه خود را به صورت فایل یا عکس ارسال کنید 📎",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAIT_RESUME

    elif text == "⏳ بعداً ارسال می‌کنم":
        await update.message.reply_text(
            "«پس از ارسال رزومه و بررسی شرایط، اگر شما مناسب تیم ما باشید، با شما تماس خواهیم گرفت تا مراحل بعدی را به‌طور دقیق‌تر توضیح دهیم.\n\n"
            "این یک مسیر سریع، معتبر و قانونی برای مهاجرت به انگلستان است. 🌍»",
            reply_markup=get_post_resume_keyboard()
        )
        return POST_RESUME_MENU

async def receive_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    file_id = None
    file_type = None

    if update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    else:
        await update.message.reply_text("لطفاً یک فایل یا عکس ارسال کنید.")
        return WAIT_RESUME

    await send_resume_lead(context, data, file_id, file_type)

    await update.message.reply_text(
        "✅ رزومه شما با موفقیت دریافت شد!\n"
        "تیم ما در اسرع وقت آن را بررسی خواهد کرد. 🙏\n\n"
        "«پس از ارسال رزومه و بررسی شرایط، اگر شما مناسب تیم ما باشید، با شما تماس خواهیم گرفت تا مراحل بعدی را به‌طور دقیق‌تر توضیح دهیم.\n"
        "این یک مسیر سریع، معتبر و قانونی برای مهاجرت به انگلستان است. 🌍»",
        reply_markup=get_post_resume_keyboard()
    )
    return POST_RESUME_MENU

# =========================
# مدیریت منوی بعد از رزومه — با تغییر اخیر
# =========================
async def handle_post_resume_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "❓ پرسیدن سوال":
        await update.message.reply_text(
            "🙌 ممنون که اطلاعات خود را ارسال کردید!\n"
            "تیم ما به‌زودی با شما تماس خواهد گرفت.\n"
            "اگر سوالی دارید، همین‌جا بپرسید 👇",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_QUESTION

    elif text == "🔄 فرآیند کاری":
        # اگر گام پایانی زده شده بود، منوی کامل، وگرنه محدود
        if context.user_data.get("final_step_done", False):
            keyboard = get_final_full_keyboard()
        else:
            keyboard = get_after_process_keyboard()

        await update.message.reply_text(
            "🔄 فرآیند همکاری ما به این صورت است:\n\n"
            "1️⃣ بررسی رزومه و اطلاعات اولیه\n"
            "2️⃣ ارزیابی مهارت و استعداد شما\n"
            "3️⃣ تماس برای مصاحبه و توضیح مدارک\n"
            "4️⃣ تهیه پرونده ویزا\n"
            "5️⃣ پیگیری تا دریافت ویزا\n\n"
            "همه مراحل با پشتیبانی کامل انجام می‌شود.",
            reply_markup=keyboard
        )
        return POST_RESUME_MENU

    elif text == "✅ گام پایانی":
        # علامت‌گذاری که گام پایانی زده شده
        context.user_data["final_step_done"] = True

        await update.message.reply_text(
            "🎉 تمام مراحل اولیه تکمیل شد!\n"
            "تیم ما به‌زودی با شما تماس می‌گیرد تا جزئیات بیشتری ارائه دهد.\n"
            "موفقیت شما اولویت ماست. 🌟\n\n"
            "ممنون که این مسیر را با ما انتخاب کردید. اگر سوالی دارید، در هر زمان بپرسید.",
            reply_markup=get_final_full_keyboard()
        )
        return POST_RESUME_MENU

    elif text == "ℹ️ اطلاعات بیشتر":
        await update.message.reply_text(
            "ما یک تیم حرفه‌ای و با تجربه هستیم که به دنبال جذب افراد با استعداد می‌گردیم. 🌟\n"
            "اگر شرایط مناسبی داشته باشید، با شما همکاری خواهیم کرد.\n"
            "برای شروع بررسی، لطفاً اطلاعات خود را ارسال کنید.",
            reply_markup=get_final_full_keyboard()
        )
        return POST_RESUME_MENU

    elif text == "🎖 آشنایی با ویژگی ویزاها":
        await update.message.reply_text(
            "🎖 ویزای استعدادیابی جهانی انگلستان (Global Talent Visa) فرصتی فوق‌العاده برای افراد مستعد است:\n\n"
            "✅ بدون نیاز به سرمایه‌گذاری کلان\n"
            "✅ بدون نیاز به پیشنهاد شغلی از کارفرما\n"
            "✅ مسیر سریع به اقامت دائم\n"
            "✅ امکان همراهی خانواده\n"
            "✅ آزادی کامل در انتخاب شغل یا راه‌اندازی کسب‌وکار\n"
            "✅ دسترسی به بازار کار و منابع بین‌المللی\n\n"
            "این ویزا برای متخصصان برجسته در حوزه‌های مختلف طراحی شده است.",
            reply_markup=get_final_full_keyboard()
        )
        return POST_RESUME_MENU

    elif text == "📄 ارسال رزومه":
        await update.message.reply_text(
            "لطفاً رزومه خود را به صورت فایل یا عکس ارسال کنید 📎",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAIT_RESUME

    else:
        # اگر گام پایانی زده شده بود، منوی کامل، وگرنه محدود
        if context.user_data.get("final_step_done", False):
            keyboard = get_final_full_keyboard()
        else:
            keyboard = get_post_resume_keyboard()

        await update.message.reply_text("لطفاً یکی از گزینه‌های زیر را انتخاب کنید 👇", reply_markup=keyboard)
        return POST_RESUME_MENU

# =========================
# دریافت سوال کاربر — با تغییر اخیر
# =========================
async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    data = context.user_data
    await send_question_to_leads(context, data, question)

    # اگر گام پایانی زده شده بود، منوی کامل، وگرنه محدود
    if context.user_data.get("final_step_done", False):
        keyboard = get_final_full_keyboard()
    else:
        keyboard = get_after_question_keyboard()

    await update.message.reply_text(
        "✅ سوال شما ثبت شد! تیم ما در اسرع وقت پاسخ می‌دهد.",
        reply_markup=keyboard
    )
    return POST_RESUME_MENU

# =========================
# main
# =========================
async def main():
    app = Application.builder().token(TOKEN).build()
    await app.initialize()
    await app.start()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_normal),
            CommandHandler("start_test", start_test),
        ],
        states={
            SHOW_MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection)],
            WAIT_CONTACT: [MessageHandler(filters.CONTACT, on_contact)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            CONFIRM_PHONE: [CallbackQueryHandler(phone_choice)],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_phone_text)],
            ASK_EDU: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_edu)],
            ASK_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_job)],
            ASK_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_field)],
            WAIT_RESUME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_resume_choice),
                MessageHandler(filters.Document.ALL | filters.PHOTO, receive_resume),
            ],
            POST_RESUME_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_resume_menu)],
            ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    print("🤖 ربات با موفقیت اجرا شد!")
    print("   /start → حالت عادی")
    print("   /start_test → حالت تستی (ریست کامل)")

    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())