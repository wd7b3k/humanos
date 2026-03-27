"""FSM states (Telegram-specific; not used in domain)."""

from aiogram.fsm.state import State, StatesGroup


class FlowStates(StatesGroup):
    """User journey matching the product flow."""

    choosing_state = State()
    initial_rating = State()
    protocol_step = State()
    final_rating = State()
    feedback_message = State()
