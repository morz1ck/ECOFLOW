from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    address_full = State()
    door_or_concierge = State()
    confirm = State()
    time = State()