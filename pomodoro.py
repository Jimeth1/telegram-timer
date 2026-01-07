import asyncio
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = "8505282584:AAG6NZmyCntQXNeqoskSSS3Q4CyjnxJYK1I"

active_timers = {}
draft_settings = {}


# ---------- MAIN KEYBOARD ----------
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Start", callback_data="open_form")],
        [InlineKeyboardButton("🔄 Update", callback_data="open_form")],
        [InlineKeyboardButton("⛔ Stop", callback_data="stop_timer")],
    ])


# ---------- FORM ----------
def timer_form(chat_id: int):
    d = draft_settings[chat_id]

    text = (
        "⏱ *Настрой таймер*\n\n"
        f"🛠 Работа: `{d['work']} мин`\n"
        f"☕ Перерыв: `{d['break']} мин`\n"
        f"⌛ Всего: `{d['hours']} ч`\n"
        f"🕒 Старт: `{d['start']}`"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="work_minus"),
            InlineKeyboardButton("Работа", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="work_plus"),
        ],
        [
            InlineKeyboardButton("➖", callback_data="break_minus"),
            InlineKeyboardButton("Перерыв", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="break_plus"),
        ],
        [
            InlineKeyboardButton("➖", callback_data="hours_minus"),
            InlineKeyboardButton("Часы", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="hours_plus"),
        ],
        [
            InlineKeyboardButton("➖", callback_data="start_minus"),
            InlineKeyboardButton("Старт", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="start_plus"),
        ],
        [
            InlineKeyboardButton("✅ Запустить", callback_data="confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ])

    return text, keyboard


# ---------- TIMER ----------
async def timer_logic(chat_id, context, work, break_, hours, start_time):
    try:
        end_time = start_time + timedelta(hours=hours)

        await asyncio.sleep((start_time - datetime.now()).total_seconds())
        await context.bot.send_message(chat_id, "🟢 Работа началась!")

        while datetime.now() < end_time:
            await asyncio.sleep(work * 60)
            await context.bot.send_message(
                chat_id, f"🔔 Перерыв ({break_} минут)"
            )

            await asyncio.sleep(break_ * 60)

            if datetime.now() >= end_time:
                break

            await context.bot.send_message(
                chat_id, "🔔 Перерыв закончился, работаем дальше"
            )

        await context.bot.send_message(chat_id, "✅ Рабочее время закончено!")

    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, "❌ Таймер остановлен")
        raise


# ---------- COMMAND ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n\n"
        "Это таймер работы с перерывами.",
        reply_markup=main_keyboard(),
    )


# ---------- CALLBACK HANDLER ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data
    await query.answer()

    # INIT FORM
    if data == "open_form":
        draft_settings[chat_id] = {
            "work": 25,
            "break": 5,
            "hours": 5,
            "start": datetime.now().strftime("%H:%M"),
        }

        text, keyboard = timer_form(chat_id)
        await query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )

    # STOP
    elif data == "stop_timer":
        if chat_id in active_timers:
            active_timers[chat_id].cancel()
            del active_timers[chat_id]
            await query.message.reply_text("⛔ Таймер остановлен")
        else:
            await query.message.reply_text("ℹ️ Нет активного таймера")

    # CANCEL FORM
    elif data == "cancel":
        await query.message.edit_text(
            "❌ Настройка отменена",
            reply_markup=main_keyboard(),
        )

    # CONFIRM
    elif data == "confirm":
        d = draft_settings[chat_id]

        now = datetime.now()
        hour, minute = map(int, d["start"].split(":"))
        start_time = now.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

        if start_time < now:
            start_time = now

        if chat_id in active_timers:
            active_timers[chat_id].cancel()

        task = asyncio.create_task(
            timer_logic(
                chat_id,
                context,
                d["work"],
                d["break"],
                d["hours"],
                start_time,
            )
        )

        active_timers[chat_id] = task

        await query.message.edit_text(
            "✅ Таймер запущен!",
            reply_markup=main_keyboard(),
        )

    # VALUE CHANGES
    else:
        d = draft_settings.get(chat_id)
        if not d:
            return

        if data == "work_plus":
            d["work"] += 5
        elif data == "work_minus" and d["work"] > 5:
            d["work"] -= 5

        elif data == "break_plus":
            d["break"] += 5
        elif data == "break_minus" and d["break"] > 5:
            d["break"] -= 5

        elif data == "hours_plus":
            d["hours"] += 1
        elif data == "hours_minus" and d["hours"] > 1:
            d["hours"] -= 1

        elif data == "start_plus":
            h, m = map(int, d["start"].split(":"))
            m += 5
            if m >= 60:
                h = (h + 1) % 24
                m = 0
            d["start"] = f"{h:02d}:{m:02d}"

        elif data == "start_minus":
            h, m = map(int, d["start"].split(":"))
            m -= 5
            if m < 0:
                h = (h - 1) % 24
                m = 55
            d["start"] = f"{h:02d}:{m:02d}"

        text, keyboard = timer_form(chat_id)
        await query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )


# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("🤖 Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
