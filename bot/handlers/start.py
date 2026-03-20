from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.crud import get_or_create_user
from bot.keyboards.inline import main_menu_kb

router = Router(name="start")


WELCOME_TEXT = (
    "🪙 <b>CryptoFolio Bot</b>\n\n"
    "Твой персональный трекер криптовалютного портфеля.\n\n"
    "📦 <b>Что я умею:</b>\n"
    "├ 💼 Управление портфелем\n"
    "├ 📈 Отслеживание цен в реалтайме\n"
    "├ 📊 Аналитика и графики\n"
    "├ 🔔 Ценовые алерты\n"
    "├ 📐 DCA-калькулятор\n"
    "└ ⚙️ Гибкие настройки\n\n"
    "Выбери раздел 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = (
        "📖 <b>Команды:</b>\n\n"
        "/start — Главное меню\n"
        "/help — Помощь\n"
        "/price <code>BTC</code> — Быстрая проверка цены\n\n"
        "Используй кнопки меню для навигации."
    )
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена.\n\n" + WELCOME_TEXT,
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
