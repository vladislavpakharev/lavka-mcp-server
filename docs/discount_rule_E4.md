# Rule change E4: 10 % discount from three units

- Price of an order of 3 or more units of one product is reduced by 10 %, rounded down
  (all arithmetic is in whole coins): `price * quantity * 9 // 10`.
- For quantity 1 and 2 the price is unchanged.
- The user limit and the stock are **not** affected by the discount: the limit is checked on units, not on price.
- A cancelled order refunds exactly the stored `total_price` (what was actually paid), not the current catalogue price.
- Covered by tests in `tests/test_rules.py` (rounding) and `tests/test_orders.py` (3 stickers cost 135, refund 135, limit still enforced).
