"""Тесты действий с заказом: покупка, отказы, повторные отмена и выдача, конверт E4."""
from pathlib import Path

from src.storage import Storage
from src.order_handlers import create_order, cancel_order, confirm_pickup
from src.read_handlers import get_coin_balance, get_order_status

SEED = Path(__file__).resolve().parents[1] / "data/seed.sql"
TABLES = ("products", "stock", "users", "orders")


def make_storage(tmp_path):
    # Каждый тест получает свою чистую базу из seed.sql.
    return Storage(tmp_path / "test.db", SEED)


def snapshot(storage):
    # Полное содержимое четырёх таблиц — чтобы сравнить «до» и «после».
    return {
        t: sorted(tuple(r) for r in storage.connection.execute("SELECT * FROM " + t))
        for t in TABLES
    }


def balance(storage, user_id):
    return get_coin_balance(storage, user_id)["data"]["balance"]


def stock_of(storage, product_id, size):
    return storage.get_product(product_id)["stock"][size]


# --- Тест 1. Расчёт стоимости и списание при покупке --------------------------
def test_purchase_bottle_costs_150_and_updates_balance_and_stock(tmp_path):
    storage = make_storage(tmp_path)
    try:
        result = create_order(storage, "student_01", "bottle", "one_size", 1)
        assert result["ok"] is True
        assert result["data"]["status"] == "created"
        assert result["data"]["total_price"] == 150
        assert balance(storage, "student_01") == 850
        assert stock_of(storage, "bottle", "one_size") == 11
    finally:
        storage.close()


# --- Тест 2. Отказ: данные не изменились --------------------------------------
def test_refused_purchase_changes_nothing(tmp_path):
    storage = make_storage(tmp_path)
    try:
        before = snapshot(storage)
        result = create_order(storage, "student_poor", "hoodie", "M", 1)
        assert result["ok"] is False
        assert result["error"]["code"] == "INSUFFICIENT_COINS"
        assert snapshot(storage) == before
    finally:
        storage.close()


# --- Тест 3. Повторная отмена не возвращает коины второй раз ------------------
def test_second_cancel_is_refused_and_refunds_only_once(tmp_path):
    storage = make_storage(tmp_path)
    try:
        order_id = create_order(storage, "student_01", "bottle", "one_size", 1)["data"]["order_id"]
        first = cancel_order(storage, order_id)
        assert first["ok"] is True and first["data"]["status"] == "cancelled"
        after_first = snapshot(storage)
        second = cancel_order(storage, order_id)
        assert second["ok"] is False
        assert second["error"]["code"] == "ORDER_STATUS_ERROR"
        assert snapshot(storage) == after_first          # второй вызов ничего не изменил
        assert balance(storage, "student_01") == 1000    # вернули ровно 1 раз
        assert stock_of(storage, "bottle", "one_size") == 12
    finally:
        storage.close()


# --- Тест 4. Выдача не трогает коины и остатки, потом отмена запрещена --------
def test_pickup_changes_only_status_and_blocks_cancel(tmp_path):
    storage = make_storage(tmp_path)
    try:
        order_id = create_order(storage, "student_01", "bottle", "one_size", 1)["data"]["order_id"]
        coins, left = balance(storage, "student_01"), stock_of(storage, "bottle", "one_size")
        picked = confirm_pickup(storage, order_id)
        assert picked["ok"] is True and picked["data"]["status"] == "picked_up"
        assert balance(storage, "student_01") == coins
        assert stock_of(storage, "bottle", "one_size") == left
        for answer in (cancel_order(storage, order_id), confirm_pickup(storage, order_id)):
            assert answer["ok"] is False
            assert answer["error"]["code"] == "ORDER_STATUS_ERROR"
        assert get_order_status(storage, order_id)["data"]["status"] == "picked_up"
    finally:
        storage.close()


# --- Тест 5. Неизвестный заказ ------------------------------------------------
def test_unknown_order_is_not_found(tmp_path):
    storage = make_storage(tmp_path)
    try:
        for action in (cancel_order, confirm_pickup):
            answer = action(storage, "missing")
            assert answer["ok"] is False
            assert answer["error"]["code"] == "ORDER_NOT_FOUND"
    finally:
        storage.close()


# --- Тест 6. Порядок проверок: пользователь раньше товара ---------------------
def test_unknown_user_is_checked_before_unknown_product(tmp_path):
    storage = make_storage(tmp_path)
    try:
        answer = create_order(storage, "missing", "missing", "M", 1)
        assert answer["error"]["code"] == "USER_NOT_FOUND"
    finally:
        storage.close()


# --- Конверт E4: тест различает старую цену и скидку --------------------------
def test_e4_three_stickers_cost_135_not_150(tmp_path):
    storage = make_storage(tmp_path)
    try:
        result = create_order(storage, "student_01", "stickers", "one_size", 3)
        assert result["data"]["total_price"] == 135      # старое правило дало бы 150
        assert balance(storage, "student_01") == 865     # списали 135, а не 150
    finally:
        storage.close()


def test_e4_two_stickers_have_no_discount(tmp_path):
    storage = make_storage(tmp_path)
    try:
        result = create_order(storage, "student_01", "stickers", "one_size", 2)
        assert result["data"]["total_price"] == 100
    finally:
        storage.close()


def test_e4_cancel_refunds_exactly_what_was_paid(tmp_path):
    storage = make_storage(tmp_path)
    try:
        order_id = create_order(storage, "student_01", "stickers", "one_size", 3)["data"]["order_id"]
        cancel_order(storage, order_id)
        assert balance(storage, "student_01") == 1000    # вернули 135, а не 150
        assert stock_of(storage, "stickers", "one_size") == 50
    finally:
        storage.close()


def test_e4_discount_does_not_bypass_user_limit(tmp_path):
    storage = make_storage(tmp_path)
    try:
        before = snapshot(storage)
        answer = create_order(storage, "student_01", "hoodie", "M", 3)  # лимит худи = 1
        assert answer["error"]["code"] == "USER_LIMIT_EXCEEDED"
        assert snapshot(storage) == before
    finally:
        storage.close()
