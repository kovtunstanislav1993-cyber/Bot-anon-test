from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    gender = State()
    age = State()
