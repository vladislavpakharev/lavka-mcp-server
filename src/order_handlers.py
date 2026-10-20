"""Порядок работы с заказом. Правила в domain, SQL в storage."""
from . import domain
from .errors import success, failure

MESSAGES = {
    "OUT_OF_STOCK": "Недостаточно товара",
    "USER_LIMIT_EXCEEDED": "Превышен лимит товара на участника",
    "INSUFFICIENT_COINS": "Недостаточно коинов",
}

def create_order(storage, user_id, product_id, size, quantity):
    'Покупка: проверки по порядку, затем одна запись в базу.'
    # 1. Пользователь существует?
    user = storage.get_user(user_id)
    if user is None:
        return failure("USER_NOT_FOUND", "Пользователь не найден")
    # 2. Товар существует?
    product = storage.get_product(product_id)
    if product is None:
        return failure("PRODUCT_NOT_FOUND", "Товар не найден")
    # Считаем данные для правил 3-5: стоимость (со скидкой E4) и уже купленное.
    total = domain.calculate_total(product["price_coins"], quantity)
    owned = storage.count_owned(user_id, product_id)
    # 3-5. Размер/остаток, лимит, коины — внутри одного правила.
    code = domain.purchase_error(product, size, quantity, user["coins"], owned, total)
    if code is not None:
        return failure(code, MESSAGES[code])  # до записи в базу
    # Все проверки пройдены: одна транзакция (заказ + коины + остаток).
    order = storage.create_order(user_id, product_id, size, quantity, total)
    return success({
        "order_id": order["id"],
        "status": order["status"],
        "total_price": order["total_price"],
    })

def cancel_order(storage, order_id):
    'Отмена: только для заказа в статусе created, возврат ровно один раз.'
    order = storage.get_order(order_id)
    if order is None:
        return failure("ORDER_NOT_FOUND", "Заказ не найден")
    if not domain.can_cancel(order):
        return failure("ORDER_STATUS_ERROR", "Заказ нельзя отменить в текущем статусе")
    # Возврат — по сохранённой в заказе стоимости, а не по текущей цене товара.
    refund = domain.refund_amount(order["total_price"])
    storage.cancel_order(order, refund)
    updated = storage.get_order(order_id)
    return success({"order_id": updated["id"], "status": updated["status"]})

def confirm_pickup(storage, order_id):
    'Выдача: только для заказа в статусе created, меняется один статус.'
    order = storage.get_order(order_id)
    if order is None:
        return failure("ORDER_NOT_FOUND", "Заказ не найден")
    if not domain.can_pickup(order):
        return failure("ORDER_STATUS_ERROR", "Заказ нельзя выдать в текущем статусе")
    storage.confirm_pickup(order_id)
    updated = storage.get_order(order_id)
    return success({"order_id": updated["id"], "status": updated["status"]})

