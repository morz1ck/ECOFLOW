from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from forms.user import Form
from data_base.db import SessionLocal
from data_base.db import get_or_create_user
from data_base.models import Order, User

router = Router()

ADMIN_ID = [1097519866]


def get_main_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Вынести мусор сейчас", callback_data="order_now")],
            [InlineKeyboardButton(text="🕐 Заказать на время", callback_data="order_later")],
            [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")],
            [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="how_it_works")],
        ]
    )


def get_door_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="У двери", callback_data="door")],
            [InlineKeyboardButton(text="Отдам лично", callback_data="in_person")],
            [InlineKeyboardButton(text="У консьержа", callback_data="concierge")],
        ]
    )


def get_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")],
        ]
    )

def get_confirm_order_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"confirm_out_order:{order_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"cancel_out_order:{order_id}")],
        ]
    )


def cancel_key():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить", callback_data="cancel")],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 ЭкоПоток - вынесем ваш мусор за 10 минут!",
        reply_markup=get_main_inline_keyboard(),
    )


@router.callback_query(F.data.in_(["order_now", "order_later"]))
async def process_order_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(order_type=callback.data)

    if callback.data == "order_later":
        await state.set_state(Form.time)
        await callback.message.answer(
            "Укажите время, когда необходимо забрать пакет.\n"
            "Например: 14:00."
        )
    else:  # order_now
        await state.set_state(Form.address_full)
        await callback.message.answer(
            "Укажите номер дома, подъезд, этаж и номер квартиры одним сообщением через запятую.\n"
            "Например: «1, 2, 5, 34»"
        )

    await callback.answer()


@router.message(Form.time)
async def process_time(message: Message, state: FSMContext):
    await state.update_data(pickup_time=message.text)
    await state.set_state(Form.address_full)
    await message.answer(
        "Укажите номер дома, подъезд, этаж и номер квартиры одним сообщением через запятую.\n"
        "Например: «1, 2, 5, 34»"
    )


@router.callback_query(F.data == "my_orders")
async def process_my_orders(callback: CallbackQuery):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if user is None:
            await callback.message.answer("У вас пока нет заказов.")
            await callback.answer()
            return

        orders = (
            session.query(Order)
            .filter_by(user_id=user.id)
            .order_by(Order.created_at.desc())
            .limit(5)
            .all()
        )

        if not orders:
            await callback.message.answer("У вас пока нет заказов.")
        else:
            text = "📦 Ваши последние заказы:\n\n"
            for o in orders:
                status_emoji = {"new": "🆕", "in_progress": "🚚", "done": "✅", "cancelled": "❌"}.get(o.status, "")
                text += f"{status_emoji} №{o.id} — {o.created_at.strftime('%d.%m %H:%M')} — {o.status}\n"
            await callback.message.answer(text)

    await callback.answer()


@router.callback_query(F.data == "how_it_works")
async def process_how_it_works(callback: CallbackQuery):
    await callback.message.answer(
        "1. Нажимаете «Вынести мусор»\n"
        "2. Указываете адрес и куда положить пакет\n"
        "3. Оплачиваете\n"
        "4. Курьер забирает пакет и присылает фото, что мусор выброшен"
    )
    await callback.answer()


@router.message(Form.address_full)
async def process_address_full(message: Message, state: FSMContext):
    parts = [p.strip() for p in message.text.split(",")]

    if len(parts) != 4:
        await message.answer(
            "Не понял формат. Введите через запятую: «дом, подъезд, этаж, квартира», "
            "например «1, 2, 5, 34»"
        )
        return

    house_number, entrance, floor, room_number = parts
    await state.update_data(house_number=house_number, entrance=entrance, floor=floor, room_number=room_number)
    await state.set_state(Form.door_or_concierge)
    await message.answer("Где оставить пакет?", reply_markup=get_door_keyboard())


@router.callback_query(Form.door_or_concierge, F.data.in_(["door", "in_person", "concierge"]))
async def process_door_or_concierge(callback: CallbackQuery, state: FSMContext):
    await state.update_data(door_or_concierge=callback.data)
    await state.set_state(Form.confirm)

    data = await state.get_data()
    order_type_text = "сейчас" if data["order_type"] == "order_now" else "на время"

    text = (
        f"Проверьте заказ:\n"
        f"Тип: {order_type_text}\n"
    )
    if data["order_type"] == "order_later":
        text += f"Время: {data['pickup_time']}\n"
    text += (
        f"Подъезд: {data['entrance']}, этаж: {data['floor']}, кв: {data['room_number']}\n"
        f"Куда положить: {data['door_or_concierge']}\n\n"
        f"Стоимость: 150₽"
    )

    await callback.message.answer(text, reply_markup=get_confirm_keyboard())
    await callback.answer()


@router.callback_query(Form.confirm, F.data == "confirm_order")
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_type_text = "сейчас" if data["order_type"] == "order_now" else "на время"

    with SessionLocal() as session:
        user = get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
        )

        order = Order(
            user_id=user.id,
                order_type=data["order_type"],
                pickup_time=data.get("pickup_time"),
                house_number = data['house_number'],
                entrance=data["entrance"],
                floor=data["floor"],
                room_number=data["room_number"],
                door_or_concierge=data["door_or_concierge"],
                status="new",
                price=150,
                is_paid=False,
        )

        session.add(order)
        session.commit()
        order_id = order.id
    

    admin_text = (
        f"📥 Новый заказ №{order_id}\n"
        f"Клиент: @{callback.from_user.username or callback.from_user.id}\n"
        f"Тип: {order_type_text}\n"
    )
    if data["order_type"] == "order_later":
        admin_text += f"Время: {data['pickup_time']}\n"
    admin_text += (
        f"Дом: № {data['house_number']}, подъезд: {data['entrance']}, этаж: {data['floor']}, кв: {data['room_number']}\n"
        f"Куда положить: {data['door_or_concierge']}"
    )


    for id in ADMIN_ID:
        await callback.bot.send_message(id, admin_text, reply_markup=get_confirm_order_keyboard(order_id))

    await callback.message.answer("Заказ отправлен курьеру, ожидайте подтверждения ⏳")
    await state.clear()
    await callback.answer()


@router.callback_query(Form.confirm, F.data == "cancel_order")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Заказ отменён.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_out_order:"))
async def process_accept_order(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        order = session.query(Order).filter_by(id=order_id).first()
        if order is None:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        order.status = "in_progress"
        session.commit()

        client = session.query(User).filter_by(id=order.user_id).first()
        client_telegram_id = client.telegram_id

    await callback.bot.send_message(
        client_telegram_id,
        "Курьер принял ваш заказ, скоро будет у вас 🚀",
    )
    await callback.message.edit_text(callback.message.text + "\n\n✅ Принято в работу")
    await callback.answer("Заказ принят")


@router.callback_query(F.data.startswith("cancel_out_order:"))
async def process_reject_order(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])

    with SessionLocal() as session:
        order = session.query(Order).filter_by(id=order_id).first()
        if order is None:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        order.status = "cancelled"
        session.commit()

        client = session.query(User).filter_by(id=order.user_id).first()
        client_telegram_id = client.telegram_id

    await callback.bot.send_message(
        client_telegram_id,
        "К сожалению, курьер не смог принять ваш заказ. Попробуйте оформить его позже.",
    )
    await callback.message.edit_text(callback.message.text + "\n\n❌ Отклонено")
    await callback.answer("Заказ отклонён")

