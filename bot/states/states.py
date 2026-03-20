from aiogram.fsm.state import State, StatesGroup


class AddAssetStates(StatesGroup):
    waiting_for_coin_search = State()
    waiting_for_coin_select = State()
    waiting_for_amount = State()
    waiting_for_price = State()
    waiting_for_confirm = State()


class SellAssetStates(StatesGroup):
    waiting_for_asset_select = State()
    waiting_for_amount = State()
    waiting_for_price = State()
    waiting_for_confirm = State()


class AlertStates(StatesGroup):
    waiting_for_coin_search = State()
    waiting_for_coin_select = State()
    waiting_for_price = State()
    waiting_for_direction = State()


class DCAStates(StatesGroup):
    waiting_for_coin_search = State()
    waiting_for_coin_select = State()
    waiting_for_amount = State()
    waiting_for_interval = State()
    waiting_for_period = State()


class PriceCheckStates(StatesGroup):
    waiting_for_coin = State()


class WatchlistStates(StatesGroup):
    waiting_for_coin_search = State()
    waiting_for_coin_select = State()
