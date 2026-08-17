from aiogram.fsm.state import State, StatesGroup


class RequestStates(StatesGroup):
    choosing_type = State()
    choosing_region = State()
    choosing_project = State()
    choosing_dates = State()
    confirming = State()
