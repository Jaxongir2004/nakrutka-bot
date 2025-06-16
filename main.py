# Nakrutka bot (Flask bilan doimiy ishlaydigan versiya)

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from keep_alive import keep_alive
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

REQUIRED_CHANNELS = [
    "@ENG_SIFATLI_VA_ARZON_REKLAMA",
    "@Obunachi_bot_guruh"
]

class OrderState(StatesGroup):
    choosing_service = State()
    waiting_for_link = State()
    waiting_for_payment = State()
    waiting_for_final_confirm = State()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📦 Telegram nakrutka"),
            KeyboardButton(text="📩 Taklif va shikoyatlar")
        ]
    ],
    resize_keyboard=True
)

def service_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Obunachi – 1 000 so‘m (1–2 kun)")],
            [KeyboardButton(text="👥 Obunachi – 10 000 so‘m (1 oy+)")],
            [KeyboardButton(text="👥 Obunachi – 20 000 so‘m (3 oy)")],
            [KeyboardButton(text="👥 Obunachi – 24 000 so‘m (4 oy)")],
            [KeyboardButton(text="👥 Obunachi – 25 000 so‘m (O‘zbek, 1 oy kafolat)")],
            [KeyboardButton(text="👥 Obunachi – 25 000 so‘m (5 oy kafolat)")],
            [KeyboardButton(text="👥 Obunachi – 32 000 so‘m (1 yil)")],
            [KeyboardButton(text="👥 Obunachi – 34 000 so‘m (Doimiy)")]
        ],
        resize_keyboard=True
    )

def admin_confirm_buttons(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user_id}")
        ]
    ])

def admin_done_button(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, nakrutka urildi", callback_data=f"done_{user_id}")]
    ])

def force_subscribe_buttons():
    buttons = [
        [InlineKeyboardButton(text="🔗 Obuna bo‘lish 1", url="https://t.me/ENG_SIFATLI_VA_ARZON_REKLAMA")],
        [InlineKeyboardButton(text="🔗 Obuna bo‘lish 2", url="https://t.me/Obunachi_bot_guruh")],
        [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def check_user_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            return False
    return True

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    is_subscribed = await check_user_subscription(message.from_user.id)
    if not is_subscribed:
        await message.answer("⛔ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=force_subscribe_buttons())
        return
    await state.clear()
    await message.answer("👋 Xush kelibsiz! Quyidagi bo‘limlardan birini tanlang:", reply_markup=main_menu)

@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    is_subscribed = await check_user_subscription(callback.from_user.id)
    if is_subscribed:
        await callback.message.delete()
        await callback.message.answer("✅ Obuna tekshiruvdan muvaffaqiyatli o‘tdi!", reply_markup=main_menu)
    else:
        await callback.answer("⛔ Hali ham obuna bo‘lmagansiz.", show_alert=True)

@dp.message(F.text == "📩 Taklif va shikoyatlar")
async def feedback_panel(message: Message):
    await message.answer("📬 Taklif yoki shikoyatlaringiz uchun admin: @Toxtasinov_Bohodirjon")

@dp.message(F.text == "📦 Telegram nakrutka")
async def show_services(message: Message, state: FSMContext):
    await state.set_state(OrderState.choosing_service)
    await message.answer("👇 Xizmat turini tanlang:", reply_markup=service_menu())

@dp.message(F.text.startswith("👥 "))
async def choose_service(message: Message, state: FSMContext):
    price_text = message.text
    data_key = price_text[:10].lower().replace(" ", "")
    await state.update_data(service=price_text)
    await state.set_state(OrderState.waiting_for_link)
    await message.answer("📎 Iltimos, nakrutka uriladigan kanal yoki guruh linkini yuboring.")

@dp.message(OrderState.waiting_for_link)
async def receive_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text)
    data = await state.get_data()
    await state.set_state(OrderState.waiting_for_payment)
    await message.answer(
        f"💳 To‘lov summasi: <b>{data['service']}</b>\nKarta raqami: <code>5614 6835 1813 5967</code>\n\n"
        f"✅ Iltimos, to‘lov chekini shu yerga yuboring. Soxta chek yubormang.")

@dp.message(OrderState.waiting_for_payment, F.photo | F.document | F.text)
async def receive_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    caption = (
        f"📥 <b>Yangi zayavka</b>\n\n👤 Foydalanuvchi: @{message.from_user.username} ({message.from_user.id})\n"
        f"🔗 Link: {data['link']}\n📦 Xizmat: {data['service']}\n\n✉️ Chek quyida.")

    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=admin_confirm_buttons(message.from_user.id))
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=admin_confirm_buttons(message.from_user.id))
    else:
        await bot.send_message(ADMIN_ID, caption + f"\n📝 Matn: {message.text}", reply_markup=admin_confirm_buttons(message.from_user.id))

    await message.reply("✅ Zayavkangiz adminga yuborildi. Tekshirilmoqda.")
    await state.set_state(OrderState.waiting_for_final_confirm)

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "✅ To‘lovingiz tasdiqlandi. Nakrutka yaqin orada amalga oshiriladi.")
    await bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=admin_done_button(user_id))

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ Chek rad etildi. Iltimos, to‘g‘ri chek yuboring.")
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)

@dp.callback_query(F.data.startswith("done_"))
async def done_service(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "🎉 Nakrutka muvaffaqiyatli bajarildi. Bizni tanlaganingiz uchun rahmat!")
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
