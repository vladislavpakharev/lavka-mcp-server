from itertools import product

from src.domain import (calculate_total, purchase_error, refund_amount, can_cancel, can_pickup,)
def test_calculate_total():
    assert calculate_total(150, 2) == 300
def test_discount_for_there_items():
    assert calculate_total(50, 3) == 135
def test_discount_rounds_down():
    assert calculate_total(51, 3) == 137
def test_purchase_error_for_low_balance():
    product = {"stock": {"one_size": 12}, "user_limit": 2}
    error = purchase_error(product, "one_size", 1, 20, 0, 150,)
    assert error == "INSUFFICIENT_COINS"
def test_purchase_error_for_limit():
    product = {"stock": {"S": 10}, "user_limit": 1}
    error = purchase_error(product, "S", 1, 1000, 1, 500,)
    assert error == "USER_LIMIT_EXCEEDED"
def test_refund_amount():
    assert refund_amount (150) == 150
def test_can_cancel_only_created():
    assert can_cancel({"status": "created"}) is True
    assert can_cancel({"status": "cancelled"}) is False
def test_can_pickup_only_created():
    assert can_pickup({"status": "created"}) is True
    assert can_pickup({"status": "picked_up"}) is False



