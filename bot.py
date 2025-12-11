# bot.py
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8519228394:AAGh0PY3csUNpXweFCCeOIhBUnUFeut24t8"  # <- вставити свій токен

# --- FSM states ---
class CalcStates(StatesGroup):
    waiting_length = State()
    waiting_coeff = State()
    waiting_curtain_price = State()
    waiting_metraj2 = State()
    waiting_multiplier = State()
    waiting_extra = State()
    waiting_tape_metraj = State()

# --- init ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- helpers ---
def float_from_text(text: str) -> float:
    text = text.replace(",", ".").strip()
    return float(text)

def coeff_kb():
    kb = InlineKeyboardBuilder()
    for v in ["1.5", "2", "2.5", "3"]:
        kb.button(text=v, callback_data=f"coeff:{v}")
    kb.adjust(2)
    return kb.as_markup()

def multiplier_kb():
    kb = InlineKeyboardBuilder()
    for v in ["2", "3", "4", "5"]:
        kb.button(text=v, callback_data=f"mult:{v}")
    kb.adjust(2)
    return kb.as_markup()

def extra_kb():
    kb = InlineKeyboardBuilder()
    for v in ["6", "12"]:
        kb.button(text=v, callback_data=f"extra:{v}")
    kb.adjust(2)
    return kb.as_markup()

# --- Start command ---
@dp.message(lambda m: m.text and m.text.startswith("/start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="Розрахувати: Карнізи", callback_data="start_calc_cornices")
    kb.adjust(1)
    await message.answer("Що будемо рахувати?", reply_markup=kb.as_markup())

# --- Start calculation flow ---
@dp.callback_query(lambda c: c.data and c.data.startswith("start_calc_cornices"))
async def start_calc(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи довжину карнизу (метри). Приклад: 3 або 3.0")
    await state.set_state(CalcStates.waiting_length)
    await callback.answer()

# --- Length ---
@dp.message(CalcStates.waiting_length)
async def got_length(message: types.Message, state: FSMContext):
    try:
        length = float_from_text(message.text)
        await state.update_data(length=length)
        await message.answer(
            f"Довжина карнизу: {length}\n\nТепер вибери коефіцієнт зборки:",
            reply_markup=coeff_kb()
        )
        await state.set_state(CalcStates.waiting_coeff)
    except Exception:
        await message.answer("Некоректне число. Введи довжину у форматі 3 або 3.5.")

# --- Coeff callback ---
@dp.callback_query(CalcStates.waiting_coeff, lambda c: c.data.startswith("coeff:"))
async def got_coeff(callback: types.CallbackQuery, state: FSMContext):
    v = callback.data.split(":", 1)[1]
    coeff = float(v)
    await state.update_data(coeff=coeff)
    await callback.message.answer(f"Обрано коефіцієнт: {coeff}\n\nВведи ціну штори (за одиницю).")
    await state.set_state(CalcStates.waiting_curtain_price)
    await callback.answer()

# --- Curtain price ---
@dp.message(CalcStates.waiting_curtain_price)
async def got_curtain_price(message: types.Message, state: FSMContext):
    try:
        price = float_from_text(message.text)
        await state.update_data(curtain_price=price)
        await message.answer("Введи метраж ткані для другого додатку (число, яке в твоїй формулі було '6'):")
        await state.set_state(CalcStates.waiting_metraj2)
    except Exception:
        await message.answer("Некоректна ціна. Введи число (наприклад 415).")

# --- Metraj2 ---
@dp.message(CalcStates.waiting_metraj2)
async def got_metraj2(message: types.Message, state: FSMContext):
    try:
        metraj2 = float_from_text(message.text)
        await state.update_data(metraj2=metraj2)
        await message.answer("Тепер вибери множник (2, 3, 4 або 5):", reply_markup=multiplier_kb())
        await state.set_state(CalcStates.waiting_multiplier)
    except Exception:
        await message.answer("Некоректне число. Введи метраж як число (наприклад 6).")

# --- Multiplier ---
@dp.callback_query(CalcStates.waiting_multiplier, lambda c: c.data.startswith("mult:"))
async def got_multiplier(callback: types.CallbackQuery, state: FSMContext):
    v = callback.data.split(":", 1)[1]
    mult = int(v)
    await state.update_data(multiplier=mult)
    await callback.message.answer("Тепер виберіть додаткову константу (6 або 12):", reply_markup=extra_kb())
    await state.set_state(CalcStates.waiting_extra)
    await callback.answer()

# --- Extra ---
@dp.callback_query(CalcStates.waiting_extra, lambda c: c.data.startswith("extra:"))
async def got_extra(callback: types.CallbackQuery, state: FSMContext):
    v = callback.data.split(":", 1)[1]
    extra = int(v)
    await state.update_data(extra=extra)
    await callback.message.answer(
        "Введи метраж тасьми (як правило це може дорівнювати метражу ткані з першого кроку):"
    )
    await state.set_state(CalcStates.waiting_tape_metraj)
    await callback.answer()

# --- Tape metraj ---
@dp.message(CalcStates.waiting_tape_metraj)
async def got_tape_metraj(message: types.Message, state: FSMContext):
    try:
        tape_metraj = float_from_text(message.text)
        data = await state.get_data()

        length = float(data["length"])
        coeff = float(data["coeff"])
        curtain_price = float(data["curtain_price"])
        metraj2 = float(data["metraj2"])
        multiplier = int(data["multiplier"])
        extra = int(data["extra"])
        tape_price = 30.0
        stitch_price = 25.0

        fabric_metraj = length * coeff
        term1 = fabric_metraj * curtain_price
        term2 = (metraj2 * multiplier + extra) * stitch_price
        term3 = tape_metraj * tape_price
        total = term1 + term2 + term3

        txt = (
            f"Розрахунок:\n\n"
            f"1) Метраж ткані (length * coeff): {length} * {coeff} = {fabric_metraj:.3f}\n"
            f"2) Вартість штори: {fabric_metraj:.3f} * {curtain_price} = {term1:.2f}\n\n"
            f"3) Другий термін: (metraj2 * multiplier + extra) * 25 = "
            f"({metraj2} * {multiplier} + {extra}) * 25 = {term2:.2f}\n\n"
            f"4) Тасьма: {tape_metraj} * {tape_price} = {term3:.2f}\n\n"
            f"ПІДСУМОК: {term1:.2f} + {term2:.2f} + {term3:.2f} = {total:.2f} грн"
        )
        await message.answer(txt)
        await state.clear()
    except Exception:
        await message.answer("Некоректне число для тасьми. Введи число (наприклад 6 або 6.0).")

# --- Cancel ---
@dp.message(lambda m: m.text and m.text.lower() == "скасувати")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Розрахунок скасовано.")

# --- Run bot ---
async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
