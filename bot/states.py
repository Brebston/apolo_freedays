from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    first_name = State()
    last_name = State()
    email = State()
    phone = State()
    password = State()


class LoginStates(StatesGroup):
    email = State()
    password = State()


class RequestStates(StatesGroup):
    choosing_type = State()
    choosing_region = State()
    choosing_project = State()
    choosing_dates = State()
    confirming = State()
