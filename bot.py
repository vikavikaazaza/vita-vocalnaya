
import asyncio
import html
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
APPLICATION_CHAT_ID = os.getenv("APPLICATION_CHAT_ID", "")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "studio_bot.sqlite3")

# =========================
# ТЕКСТЫ — МЕНЯЙ ИХ ЗДЕСЬ
# =========================

WELCOME_TEXT = """
Пр-р-ривет! 
Меня зовут Вита, и этот бот собрал в себя основную информацию по Вокальной ❤️

Также сюда будут публиковаться последнее новости, информация о мастер-классах и мероприятиях студии, а также свободные окошки 😍

Жми на интересующий тебя раздел ⬇️ и оставайся с нами!
"""

PRICE_TEXT = """
В нашей студии работают три замечательных преподавателя — выбери того, кто станет твоим наставником!✨️
"""

ADDRESS_TEXT = """
📍 <b>Адрес</b>

Посетить нашу студию ты можешь по адресу г. Хабаровск 
улица Серышева, 31.

Обращаем внимание, что вход со стороны улицы Джамбула, ориентир - Тихоокеанская звезда ⭐️
"""


YANDEX_MUSIC_URL = "https://music.yandex.ru/artist/21769675?utm_medium=copy_link"
MAIN_MENU_PHOTO = Path("photos/Главное меню.jpg")

RENT_TEXT = """
Ребята, 
нашу супер уютную студию вы можете снять в аренду 🌙️

Нет лучшего места для проведения вашей фотосессии, караоке девичника или мастер класса! 

А может вы просто хотите потренировать свои вокальные данные 💫️

Для этого у нас есть все:
▪️ классный свет
▪️ проектор
▪️ необходимая аппаратура 
▪️ два микрофона (проводной и беспроводной) 
▪️ высокий стол/рабочее место 
▪️ чай/кофе

Прайс аренды:
- Для самостоятельных занятий - 700₽/час
- Под фотосессию - 1.100₽/час
- Для мастер класса - 1.500₽/час
- Для караоке-девичника - 2000₽/час

*Мы не сдаем студию преподавателям для проведения уроков вокала
"""

RENT_FINISH_TEXT = """
Замур-р-рчательно✨️ Мы свяжемся с вами в течение часа❤️ Спасибо за доверие!
"""

BOOKING_FINISH_TEXT = """
Замур-р-рчательно✨️ Мы свяжемся с вами в свободное время для уточнения деталей ❤️ Благодарим за доверие!
"""

TEACHERS = {
    "vita": {
        "name": "Вита",
        "photo": "photos/Вита.jpg",
        "text": """Вокал с Витой ❤️

Индивидуальное занятие - 5000₽
*Длительность индивидуального занятия - 50 минут""",
    },
    "nastya": {
        "name": "Настя",
        "photo": "photos/Настя.jpg",
        "text": """Вокал с Настей ❤️

Индивидуальное занятие - 2000₽
Абонемент (4 занятия) - 7600₽

Длительность индивидуального занятия - 50 минут
Абонемент действителен 1 месяц""",
    },
    "evgenia": {
        "name": "Евгения",
        "photo": "photos/Евгения.jpg",
        "text": """Вокал с Евгенией ❤️

Индивидуальное занятие - 2500₽
Абонемент (4 занятия) - 9600₽

Индивидуальное занятие детское - 1300₽ 
Абонемент детский (4 занятия) - 4800₽

Длительность индивидуального занятия - 50 минут
Длительность детского занятия - 30 минут""",
    },
    "polina": {
        "name": "Полина",
        "photo": "photos/Полина.jpg",
        "text": """Вокал с Полиной ❤️

Индивидуальное занятие  - 2000 рублей
Абонемент на 4 занятия* - 7600 рублей

*Абонемент действует один месяц
*Длительность индивидуального занятия - 50 минут""",
    },
}

LEVELS = [
    "Никогда не занимался вокалом",
    "Не так давно занимаюсь вокалом",
    "Давно занимаюсь вокалом",
]


# =========================
# БАЗА
# =========================

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                activity_count INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                username TEXT,
                name TEXT,
                phone TEXT,
                teacher TEXT,
                level TEXT,
                time TEXT,
                days TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

def touch_user(user, phone=None):
    now = datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        conn.execute("""
            INSERT INTO users (
                telegram_id, username, first_name, last_name, phone,
                created_at, last_activity, activity_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                phone=COALESCE(excluded.phone, users.phone),
                last_activity=excluded.last_activity,
                activity_count=users.activity_count + 1
        """, (
            user.id, user.username or "", user.first_name or "",
            user.last_name or "", phone, now, now
        ))
        conn.commit()

def log_user_activity(user, action):
    touch_user(user)
    with db() as conn:
        conn.execute(
            "INSERT INTO activities (telegram_id, action, created_at) VALUES (?, ?, ?)",
            (user.id, action, datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()

def save_booking(data, user_id):
    with db() as conn:
        conn.execute("""
            INSERT INTO applications (
                telegram_id, username, name, phone, teacher,
                level, time, days, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("username", ""),
            data.get("name", ""),
            data.get("phone", ""),
            data.get("teacher", ""),
            data.get("level", ""),
            data.get("time", ""),
            data.get("days", ""),
            datetime.now().isoformat(timespec="seconds")
        ))
        conn.commit()

# =========================
# FSM
# =========================

class Booking(StatesGroup):
    name = State()
    username = State()
    phone = State()
    level = State()
    time = State()
    days = State()

class RentBooking(StatesGroup):
    name = State()
    username = State()
    phone = State()
    datetime_text = State()
    purpose = State()

class Broadcast(StatesGroup):
    content = State()
    buttons = State()

router = Router()


# =========================
# КЛАВИАТУРЫ
# =========================

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Прайс", callback_data="price")
    kb.button(text="Адрес", callback_data="address")
    kb.button(text="Аренда", callback_data="rent")
    kb.button(text="Записаться на занятие", callback_data="signup:any")
    kb.button(
    text="Связаться с администратором",
    url="https://t.me/VokalnayaVita"
)
    kb.button(text="Яндекс.Музыка", url=YANDEX_MUSIC_URL)
    kb.adjust(1, 2, 1, 1, 1)
    return kb.as_markup()

def teachers_menu():
    kb = InlineKeyboardBuilder()
    for key, teacher in TEACHERS.items():
        kb.button(text=teacher["name"], callback_data=f"teacher:{key}")
    kb.button(text="В главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

def teacher_menu(key):
    kb = InlineKeyboardBuilder()
    kb.button(text="Записаться на занятие", callback_data=f"signup:{key}")
    kb.button(text="Назад", callback_data="price")
    kb.adjust(1)
    return kb.as_markup()

def info_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Записаться на занятие", callback_data="signup:any")
    kb.button(text="В главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

def rent_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Хочу арендовать студию!", callback_data="rent:start")
    kb.button(text="В главное меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()

def level_menu():
    kb = InlineKeyboardBuilder()
    for i, level in enumerate(LEVELS):
        kb.button(text=level, callback_data=f"level:{i}")
    kb.adjust(1)
    return kb.as_markup()

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="📱 Отправить номер телефона",
            request_contact=True
        )]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data="adm:stats")
    kb.button(text="📢 Рассылка", callback_data="adm:broadcast")
    kb.button(text="👥 Пользователи", callback_data="adm:users")
    kb.button(text="📋 Заявки", callback_data="adm:applications")
    kb.adjust(2)
    return kb.as_markup()


# =========================
# УДАЛЕНИЕ НАВИГАЦИОННОГО СООБЩЕНИЯ
# Формы специально НЕ используют эту функцию.
# =========================

async def delete_and_send(callback: CallbackQuery, text=None, reply_markup=None, photo=None, caption=None):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if photo:
        await callback.message.answer_photo(
            FSInputFile(photo),
            caption=caption or "",
            reply_markup=reply_markup
        )
    else:
        await callback.message.answer(
            text or "",
            reply_markup=reply_markup
        )

# =========================
# /start
# =========================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    log_user_activity(message.from_user, "start")
    if MAIN_MENU_PHOTO.exists():
        await message.answer_photo(FSInputFile(MAIN_MENU_PHOTO), caption=WELCOME_TEXT, reply_markup=main_menu())
    else:
        await message.answer(WELCOME_TEXT, reply_markup=main_menu())

# =========================
# КОМАНДЫ МЕНЮ
# =========================

@router.message(Command("price"))
async def cmd_price(message: Message):
    log_user_activity(message.from_user, "command_price")
    await message.answer(PRICE_TEXT, reply_markup=teachers_menu())

@router.message(Command("address"))
async def cmd_address(message: Message):
    log_user_activity(message.from_user, "command_address")
    await message.answer(ADDRESS_TEXT, reply_markup=info_menu())

@router.message(Command("rent"))
async def cmd_rent(message: Message):
    log_user_activity(message.from_user, "command_rent")
    photo = Path("photos/Аренда.jpg")
    if photo.exists():
        await message.answer_photo(FSInputFile(photo), caption=RENT_TEXT, reply_markup=rent_menu())
    else:
        await message.answer(RENT_TEXT, reply_markup=rent_menu())

@router.message(Command("singup"))
async def cmd_signup(message: Message, state: FSMContext):
    log_user_activity(message.from_user, "command_signup")
    await start_booking(message, state, teacher=None)

@router.message(Command("link"))
async def cmd_link(message: Message):
    log_user_activity(message.from_user, "command_link")
    await message.answer(
        "🎵 Яндекс.Музыка",
        reply_markup=InlineKeyboardBuilder().button(
            text="Открыть Яндекс.Музыку", url=YANDEX_MUSIC_URL
        ).as_markup()
    )

# =========================
# ГЛАВНОЕ МЕНЮ / НАВИГАЦИЯ
# =========================

@router.callback_query(F.data == "main")
async def cb_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    log_user_activity(callback.from_user, "main_menu")
    await state.clear()
    if MAIN_MENU_PHOTO.exists():
        await delete_and_send(callback, reply_markup=main_menu(), photo=MAIN_MENU_PHOTO, caption=WELCOME_TEXT)
    else:
        await delete_and_send(callback, WELCOME_TEXT, main_menu())

@router.callback_query(F.data == "price")
async def cb_price(callback: CallbackQuery):
    await callback.answer()
    log_user_activity(callback.from_user, "price")
    await delete_and_send(callback, PRICE_TEXT, teachers_menu())

@router.callback_query(F.data == "address")
async def cb_address(callback: CallbackQuery):
    await callback.answer()
    log_user_activity(callback.from_user, "address")
    await delete_and_send(callback, ADDRESS_TEXT, info_menu())

@router.callback_query(F.data == "admin_contact")
async def cb_admin_contact(callback: CallbackQuery):
    await callback.answer()
    log_user_activity(callback.from_user, "admin_contact")
    await delete_and_send(callback, ADMIN_CONTACT_TEXT, info_menu())

@router.callback_query(F.data == "rent")
async def cb_rent(callback: CallbackQuery):
    await callback.answer()
    log_user_activity(callback.from_user, "rent")
    photo = Path("photos/Аренда.jpg")
    if photo.exists():
        await delete_and_send(callback, reply_markup=rent_menu(), photo=photo, caption=RENT_TEXT)
    else:
        await delete_and_send(callback, RENT_TEXT, rent_menu())

# =========================
# ПРАЙС -> ПРЕПОДАВАТЕЛЬ
# =========================

@router.callback_query(F.data.startswith("teacher:"))
async def cb_teacher(callback: CallbackQuery):
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    teacher = TEACHERS[key]
    log_user_activity(callback.from_user, f"teacher_{key}")

    photo = Path(teacher["photo"])
    if photo.exists():
        await delete_and_send(
            callback,
            reply_markup=teacher_menu(key),
            photo=photo,
            caption=teacher["text"]
        )
    else:
        await delete_and_send(
            callback,
            teacher["text"],
            teacher_menu(key)
        )

# =========================
# ЗАПИСЬ НА ЗАНЯТИЕ
# =========================

async def start_booking(message_or_callback, state: FSMContext, teacher=None):
    await state.clear()
    await state.update_data(
        teacher=teacher or "",
        booking_source="teacher" if teacher else "main"
    )
    await state.set_state(Booking.name)

    if isinstance(message_or_callback, CallbackQuery):
        await delete_and_send(
            message_or_callback,
            "Напиши свое имя ❤️"
        )
    else:
        await message_or_callback.answer("Напиши свое имя ❤️")

@router.callback_query(F.data.startswith("signup:"))
async def cb_signup(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    teacher = None if key == "any" else TEACHERS[key]["name"]
    log_user_activity(callback.from_user, f"signup_{key}")
    await start_booking(callback, state, teacher)

@router.message(Booking.name)
async def booking_name(message: Message, state: FSMContext):
    log_user_activity(message.from_user, "booking_name")
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, напиши свое имя ❤️")
        return
    await state.update_data(name=name)
    await message.answer(
        "Напиши свой номер телефона ❤️",
        reply_markup=phone_keyboard()
    )
    await state.set_state(Booking.phone)

@router.message(Booking.phone, F.contact)
async def booking_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    log_user_activity(message.from_user, "booking_phone")
    await state.update_data(phone=phone)
    with db() as conn:
        conn.execute("UPDATE users SET phone=? WHERE telegram_id=?", (phone, message.from_user.id))
        conn.commit()
    await message.answer(
        "Расскажи о своих отношениях с вокалом ❤️",
        reply_markup=level_menu()
    )
    await state.set_state(Booking.level)

@router.message(Booking.phone)
async def booking_phone_text(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    if len(phone) < 6:
        await message.answer("Напиши корректный номер телефона ❤️")
        return
    log_user_activity(message.from_user, "booking_phone")
    await state.update_data(phone=phone)
    with db() as conn:
        conn.execute("UPDATE users SET phone=? WHERE telegram_id=?", (phone, message.from_user.id))
        conn.commit()
    await message.answer(
        "Расскажи о своих отношениях с вокалом ❤️",
        reply_markup=level_menu()
    )
    await state.set_state(Booking.level)

@router.callback_query(Booking.level, F.data.startswith("level:"))
async def booking_level(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    idx = int(callback.data.split(":")[1])
    await state.update_data(level=LEVELS[idx])
    log_user_activity(callback.from_user, f"booking_level_{idx}")
    await callback.message.answer(
        "Напиши, в какое время тебе будет удобно посещать занятия❤️\n"
        "<i>Например: вторая половина дня, 16:00✨️</i>"
    )
    await state.set_state(Booking.time)

@router.message(Booking.time)
async def booking_time(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer(
            "Напиши, в какое время тебе будет удобно посещать занятия❤️\n"
            "<i>Например: вторая половина дня, 16:00✨️</i>"
        )
        return
    log_user_activity(message.from_user, "booking_time")
    await state.update_data(time=value)
    await message.answer(
        "Напиши дни, когда тебе будет удобно посещать занятия❤️\n"
        "<i>Например: вторник, четверг✨️</i>"
    )
    await state.set_state(Booking.days)

@router.message(Booking.days)
async def booking_days(message: Message, state: FSMContext):
    days = (message.text or "").strip()
    if len(days) < 2:
        await message.answer(
            "Напиши дни, когда тебе будет удобно посещать занятия❤️\n"
            "<i>Например: вторник, четверг✨️</i>"
        )
        return

    await state.update_data(days=days)
    data = await state.get_data()
    log_user_activity(message.from_user, "booking_completed")
    save_booking(data, message.from_user.id)

    username = data.get("username") or message.from_user.username or ""
    username_display = f"@{username}" if username and not username.startswith("@") else username
    teacher = data.get("teacher", "").strip()

    if teacher:
        header = f"❗️<b>БРОНЬ {html.escape(teacher.upper())}❗️</b>"
        footer = ""
    else:
        header = "❗️<b>БРОНЬ</b>❗️"
        footer = "\n\n<b>❗️Ученик не выбрал преподавателя, записался через главное меню ❗️</b>"

    application = f"""
{header}

◾️ТГ клиента: {html.escape(username_display or "не указан")}
◾️Имя клиента: {html.escape(data["name"])}
◾️Телефон клиента: {html.escape(data["phone"])}
◾️Уровень клиента: {html.escape(data["level"])}
◾️День: {html.escape(data["days"])}
◾️Время: {html.escape(data["time"])}
{footer}
"""

    if APPLICATION_CHAT_ID:
        try:
            await message.bot.send_message(int(APPLICATION_CHAT_ID), application)
        except Exception:
            logging.exception("Не удалось отправить заявку")
            await message.answer("Заявка сохранена, но не удалось отправить её в группу. Проверь APPLICATION_CHAT_ID.")
            await state.clear()
            return

    await state.clear()

    kb = InlineKeyboardBuilder()
    kb.button(text="В главное меню", callback_data="main")

    await message.answer(
        BOOKING_FINISH_TEXT,
        reply_markup=kb.as_markup()
    )

# =========================
# АРЕНДА
# =========================

@router.callback_query(F.data == "rent:start")
async def rent_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    log_user_activity(callback.from_user, "rent_start")
    await state.clear()
    await state.update_data(rent_source="rent")
    await state.set_state(RentBooking.name)
    # ФОРМА НЕ УДАЛЯЕТ ПРЕДЫДУЩИЕ СООБЩЕНИЯ
    await callback.message.answer("Напиши свое имя ❤️")

@router.message(RentBooking.name)
async def rent_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, напиши свое имя ❤️")
        return
    log_user_activity(message.from_user, "rent_name")
    await state.update_data(name=name)
    await message.answer("Напиши свой номер телефона ❤️", reply_markup=phone_keyboard())
    await state.set_state(RentBooking.phone)

@router.message(RentBooking.phone, F.contact)
async def rent_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    log_user_activity(message.from_user, "rent_phone")
    await state.update_data(phone=phone)
    with db() as conn:
        conn.execute("UPDATE users SET phone=? WHERE telegram_id=?", (phone, message.from_user.id))
        conn.commit()
    await message.answer("Напиши дату и время ❤️\n<i>Например: среда, с 18:00 до 20:00✨️</i>", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RentBooking.datetime_text)

@router.message(RentBooking.phone)
async def rent_phone_text(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    if len(phone) < 6:
        await message.answer("Напиши корректный номер телефона ❤️")
        return
    log_user_activity(message.from_user, "rent_phone")
    await state.update_data(phone=phone)
    with db() as conn:
        conn.execute("UPDATE users SET phone=? WHERE telegram_id=?", (phone, message.from_user.id))
        conn.commit()
    await message.answer("Напиши дату и время ❤️\n<i>Например: среда, с 18:00 до 20:00✨️</i>", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RentBooking.datetime_text)

@router.message(RentBooking.datetime_text)
async def rent_datetime(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("Напиши дату и время ❤️\n<i>Например: среда, с 18:00 до 20:00✨️</i>")
        return
    log_user_activity(message.from_user, "rent_datetime")
    await state.update_data(datetime_text=value)
    await message.answer("Напиши цель аренды ❤️\n<i>Например: караоке-девичник✨️</i>")
    await state.set_state(RentBooking.purpose)

@router.message(RentBooking.purpose)
async def rent_purpose(message: Message, state: FSMContext):
    purpose = (message.text or "").strip()
    if len(purpose) < 2:
        await message.answer("Напиши цель аренды ❤️\n<i>Например: караоке-девичник✨️</i>")
        return

    await state.update_data(purpose=purpose)
    data = await state.get_data()
    log_user_activity(message.from_user, "rent_completed")

    username = message.from_user.username or ""
    username_display = f"@{username}" if username and not username.startswith("@") else username

    application = f"""
❗️<b>БРОНЬ АРЕНДЫ</b> ❗️

🔻ТГ клиента: {html.escape(username_display or "не указан")}
🔻Имя клиента: {html.escape(data["name"])}
🔻Телефон клиента: {html.escape(data["phone"])}
🔻Цель аренды: {html.escape(data["purpose"])}
🔻Дата и время: {html.escape(data["datetime_text"])}
"""

    if APPLICATION_CHAT_ID:
        try:
            await message.bot.send_message(int(APPLICATION_CHAT_ID), application)
        except Exception:
            logging.exception("Не удалось отправить заявку аренды")
            await message.answer("Заявка сохранена, но не удалось отправить её в группу. Проверь APPLICATION_CHAT_ID.")
            await state.clear()
            return

    await state.clear()

    kb = InlineKeyboardBuilder()
    kb.button(text="В главное меню", callback_data="main")

    await message.answer(
        RENT_FINISH_TEXT,
        reply_markup=kb.as_markup()
    )

# =========================
# /админ11
# Telegram не добавляет такую команду в стандартное меню Bot API,
# поэтому обрабатываем её как обычный текст.
# =========================

@router.message(F.text == "/админ11")
async def admin_command_cyrillic(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    log_user_activity(message.from_user, "admin_panel")
    await message.answer("Введите текст, который хотите опубликовать")
    await state.set_state(Broadcast.content)

# запасной вариант латиницей
@router.message(Command("admin11"))
async def admin_command_latin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    log_user_activity(message.from_user, "admin_panel")
    await message.answer("Введите текст, который хотите опубликовать")
    await state.set_state(Broadcast.content)

def parse_buttons(raw: str):
    """
    Каждая кнопка в отдельной строке:
    Текст кнопки | https://example.com
    """
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            continue
        text, url = [x.strip() for x in line.split("|", 1)]
        if text and url.startswith(("http://", "https://", "tg://")):
            result.append((text, url))
    return result

def buttons_markup(buttons):
    if not buttons:
        return None
    kb = InlineKeyboardBuilder()
    for text, url in buttons:
        kb.button(text=text, url=url)
    kb.adjust(1)
    return kb.as_markup()

@router.message(Broadcast.content)
async def broadcast_content(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    # Копируем исходное сообщение из лички администратора позже через copy_message.
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id
    )
    await message.answer(
        "Если нужны кнопки, пришли их следующим сообщением — по одной на строку:\n\n"
        "<code>Текст кнопки | https://ссылка.ru</code>\n\n"
        "Если кнопки не нужны, напиши: <code>нет</code>"
    )
    await state.set_state(Broadcast.buttons)

@router.message(Broadcast.buttons)
async def broadcast_buttons(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    data = await state.get_data()
    raw = (message.text or "").strip()
    buttons = [] if raw.lower() in {"нет", "-", "без кнопок", "no"} else parse_buttons(raw)
    markup = buttons_markup(buttons)

    with db() as conn:
        users = conn.execute(
            "SELECT telegram_id FROM users WHERE is_blocked=0"
        ).fetchall()

    sent = 0
    failed = 0

    await message.answer(f"📢 Начинаю рассылку. Получателей: {len(users)}")

    for (user_id,) in users:
        try:
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=data["source_chat_id"],
                message_id=data["source_message_id"],
                reply_markup=markup
            )
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
            with db() as conn:
                conn.execute(
                    "UPDATE users SET is_blocked=1 WHERE telegram_id=?",
                    (user_id,)
                )
                conn.commit()

    await state.clear()
    await message.answer(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed}"
    )

# =========================
# АДМИН: СТАТИСТИКА
# =========================

def admin_only(callback: CallbackQuery):
    return callback.from_user.id in ADMIN_IDS

@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery):
    if not admin_only(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    now = datetime.now()
    d1 = (now - timedelta(days=1)).isoformat()
    d7 = (now - timedelta(days=7)).isoformat()
    d30 = (now - timedelta(days=30)).isoformat()

    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        a1 = conn.execute("SELECT COUNT(*) FROM users WHERE last_activity>=?", (d1,)).fetchone()[0]
        a7 = conn.execute("SELECT COUNT(*) FROM users WHERE last_activity>=?", (d7,)).fetchone()[0]
        a30 = conn.execute("SELECT COUNT(*) FROM users WHERE last_activity>=?", (d30,)).fetchone()[0]
        apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE created_at>=?",
            (now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),)
        ).fetchone()[0]

    await callback.message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"🟢 Активных за 24 часа: <b>{a1}</b>\n"
        f"🟢 Активных за 7 дней: <b>{a7}</b>\n"
        f"🟢 Активных за 30 дней: <b>{a30}</b>\n\n"
        f"📋 Заявок всего: <b>{apps}</b>\n"
        f"📋 Заявок сегодня: <b>{today}</b>",
        reply_markup=admin_menu()
    )

@router.callback_query(F.data == "adm:users")
async def adm_users(callback: CallbackQuery):
    if not admin_only(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    with db() as conn:
        rows = conn.execute("""
            SELECT telegram_id, username, first_name, last_activity, activity_count
            FROM users ORDER BY last_activity DESC LIMIT 30
        """).fetchall()

    text = "👥 <b>Пользователи</b>\n\n"
    for uid, username, first_name, last_activity, count in rows:
        u = f"@{username}" if username else "без @username"
        text += f"• <b>{html.escape(first_name or '')}</b> {html.escape(u)}\n"
        text += f"  ID: <code>{uid}</code> | действий: {count}\n"
        text += f"  Последняя активность: {last_activity}\n\n"

    await callback.message.answer(text[:4000], reply_markup=admin_menu())

@router.callback_query(F.data == "adm:applications")
async def adm_applications(callback: CallbackQuery):
    if not admin_only(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    with db() as conn:
        rows = conn.execute("""
            SELECT name, username, phone, teacher, level, time, days, created_at
            FROM applications ORDER BY id DESC LIMIT 15
        """).fetchall()

    text = "📋 <b>Последние заявки</b>\n\n"
    if not rows:
        text += "Заявок пока нет."
    for r in rows:
        name, username, phone, teacher, level, time, days, created = r
        text += (
            f"<b>{html.escape(name)}</b> | {html.escape(username or 'без @username')}\n"
            f"Тел: {html.escape(phone)}\n"
            f"Преподаватель: {html.escape(teacher or 'не выбран')}\n"
            f"Уровень: {html.escape(level)}\n"
            f"Дни: {html.escape(days)}\n"
            f"Время: {html.escape(time)}\n"
            f"Дата: {created}\n\n"
        )

    await callback.message.answer(text[:4000], reply_markup=admin_menu())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu())


# =========================
# FALLBACK: логируем сообщения
# =========================

@router.message()
async def fallback(message: Message):
    touch_user(message.from_user)
    with db() as conn:
        conn.execute(
            "INSERT INTO activities (telegram_id, action, created_at) VALUES (?, ?, ?)",
            (message.from_user.id, "message", datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()


async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("Не указан BOT_TOKEN в .env")

    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.set_my_commands([
        # /singup оставлен именно так, как попросила владелица бота.
        {"command": "start", "description": "Главное меню"},
        {"command": "price", "description": "Прайс"},
        {"command": "rent", "description": "Аренда студии"},
        {"command": "address", "description": "Адрес"},
        {"command": "singup", "description": "Записаться на занятие"},
        {"command": "link", "description": "Ссылка на Яндекс.Музыку"},
    ])

    print("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())