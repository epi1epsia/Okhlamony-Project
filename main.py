import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from gigachat import GigaChat

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GIGA_KEY = os.getenv("GIGACHAT_KEY")

bot = Bot(token=TOKEN, session=AiohttpSession())
dp = Dispatcher()
giga = GigaChat(credentials=GIGA_KEY, verify_ssl_certs=False)

DEFAULT_BOOKS = {
    "1": "А. С. Пушкин — «Капитанская дочка»",
    "2": "Н. В. Гоголь — «Ревизор»",
    "3": "М. Ю. Лермонтов — «Мцыри»",
    "4": "И. С. Тургенев — «Ася»",
    "5": "Д. И. Фонвизин — «Недоросль»",
    "6": "Неизвестен — «Слово о полку Игореве»",
    "7": "А. С. Грибоедов — «Горе от ума»",
    "8": "А. С. Пушкин — «Евгений Онегин»",
    "9": "М. Ю. Лермонтов — «Герой нашего времени»",
    "10": "Н. В. Гоголь — «Мертвые души»",
    "11": "М. А. Шолохов — «Судьба человека»",
    "12": "А. Н. Островский — «Гроза»",
    "13": "И. А. Гончаров — «Обломов»",
    "14": "И. С. Тургенев — «Отцы и дети»"
}

user_context = {}

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    for num in DEFAULT_BOOKS.keys():
        builder.button(text=num)
    builder.button(text="📥 Свой текст")
    builder.adjust(5)
    return builder.as_markup(resize_keyboard=True)

def get_book_actions_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Пересказ")
    builder.button(text="🧩 Викторина")
    builder.button(text="💡 Факт")
    builder.button(text="📜 Цитата")
    builder.button(text="🔙 Назад")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
@dp.message(F.text == "🔙 Назад")
async def start_cmd(message: types.Message):
    user_context.pop(message.from_user.id, None)
    welcome_text = (
        "👋 **Привет! Я твой Литературный помощник.**\n\n"
        "Я помогу тебе проанализировать классику или твой собственный текст. "
        "Я умею находить ответы на вопросы, приводить цитаты и делать пересказы.\n\n"
        "**Выбери номер книги из списка:**"
    )
    list_text = "\n\n"
    for num, title in DEFAULT_BOOKS.items():
        list_text += f"{num}. {title}\n"
    await message.answer(welcome_text + list_text, reply_markup=get_main_keyboard())

@dp.message(F.text == "📥 Свой текст")
async def upload_info(message: types.Message):
    await message.answer("Чтобы я проанализировал твой текст, просто **пришли мне файл в формате .txt**.")

@dp.message(F.document)
async def handle_docs(message: types.Message):
    if message.document.file_name.endswith('.txt'):
        os.makedirs("books", exist_ok=True)
        file_path = f"books/user_{message.from_user.id}.txt"
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            user_context[message.from_user.id] = {"title": message.document.file_name, "context": f.read()}
        await message.answer(f"✅ Файл `{message.document.file_name}` загружен! Что хочешь сделать?", reply_markup=get_book_actions_keyboard())
    else:
        await message.answer("❌ Пожалуйста, отправь файл в формате .txt")

@dp.message(F.text.in_(DEFAULT_BOOKS.keys()))
async def select_book(message: types.Message):
    book_id = message.text
    path = f"books/{book_id}.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_context[message.from_user.id] = {"title": DEFAULT_BOOKS[book_id], "context": f.read()}
        await message.answer(f"📖 Выбрано: {DEFAULT_BOOKS[book_id]}.\nЖду твоих вопросов!", reply_markup=get_book_actions_keyboard())
    else:
        await message.answer(f"⚠️ Текст книги {book_id} не найден на сервере.")

async def ask_giga(message, prompt_prefix):
    uid = message.from_user.id
    if uid not in user_context:
        await message.answer("Сначала выбери книгу!")
        return
    wait_msg = await message.answer("⏳ Анализирую текст...")
    try:
        book_title = user_context[uid]['title']
        full_text = user_context[uid]['context'][:25000]
        prompt = (
            f"Используя предоставленный текст: {full_text}\n\n"
            f"Задание: {prompt_prefix} книги '{book_title}'. "
            f"Важное условие: ОБЯЗАТЕЛЬНО включи в ответ 1-2 прямые цитаты из текста для подтверждения информации."
        )
        res = giga.chat(prompt)
        await message.answer(res.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Произошла ошибка ИИ: {e}")
    finally:
        await bot.delete_message(message.chat.id, wait_msg.message_id)

@dp.message(F.text == "📝 Пересказ")
async def handle_summary(message: types.Message):
    await ask_giga(message, "Сделай краткий и содержательный пересказ")

@dp.message(F.text == "🧩 Викторина")
async def handle_quiz(message: types.Message):
    await ask_giga(message, "Придумай 3 интересных вопроса по сюжету с ответами в конце")

@dp.message(F.text == "💡 Факт")
async def handle_fact(message: types.Message):
    await ask_giga(message, "Напиши один интересный факт об этой книге или авторе")

@dp.message(F.text == "📜 Цитата")
async def handle_quote(message: types.Message):
    await ask_giga(message, "Приведи одну знаковую цитату из")

@dp.message()
async def handle_question(message: types.Message):
    uid = message.from_user.id
    if uid not in user_context:
        await message.answer("Пожалуйста, сначала выбери номер книги.")
        return
    wait_msg = await message.answer("⏳ Ищу ответ в книге...")
    try:
        ctx = user_context[uid]['context'][:25000]
        prompt = (
            f"Контекст из произведения: {ctx}\n\n"
            f"Вопрос: {message.text}\n"
            f"Инструкция: Ответь на вопрос, опираясь только на этот контекст. "
            f"Обязательно приведи цитаты из текста. Если ответа в тексте нет, честно скажи об этом."
        )
        res = giga.chat(prompt)
        await message.answer(res.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Ошибка при поиске: {e}")
    finally:
        await bot.delete_message(message.chat.id, wait_msg.message_id)

async def main():
    print("--- БОТ ГОТОВ ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())