# Merch Store MCP Server ("Lavka")

An [MCP](https://modelcontextprotocol.io) server (FastMCP + SQLite) for a small merch store
where participants spend virtual coins. It exposes seven tools that an AI agent can call:

| Tool | Kind | What it does |
|------|------|--------------|
| `list_products`, `get_product` | read | catalogue and one product with stock per size |
| `get_coin_balance`, `get_order_status` | read | balance of a user, status of an order |
| `create_order` | write | validates, then writes order + coins + stock in **one transaction** |
| `cancel_order` | write | only for status `created`; refunds exactly what was paid, once |
| `confirm_pickup` | write | only for status `created` → `picked_up`; coins and stock untouched |

Every tool returns `{"ok": true, "data": ...}` or `{"ok": false, "error": {"code", "message"}}`
with codes such as `INSUFFICIENT_COINS`, `OUT_OF_STOCK`, `USER_LIMIT_EXCEEDED`,
`ORDER_STATUS_ERROR`, `*_NOT_FOUND`.

## Architecture

```
mcp_adapter.py     registers the tools, input types, schemas from contracts/
   └── read_handlers.py / order_handlers.py     order of checks, builds the response
          ├── domain.py     pure rules: price, discount, limits, who can cancel   (no SQL, no MCP)
          └── storage.py    SQLite access; write methods run in one transaction   (no rules)
```

Rules, SQL and protocol are separated on purpose: rules are tested without a database,
handlers are tested against a throw-away SQLite file built from `data/seed.sql`.

## My part

This was a four-person team project, one area per person. **My area was the order actions:**

- `src/order_handlers.py` – `create_order`, `cancel_order`, `confirm_pickup`:
  the order of checks (user → product → size/stock → user limit → balance), refusal
  *before* any write, refund by the **stored** `total_price`, repeat cancel / pickup refused.
- `tests/test_orders.py` – 10 tests: a refused purchase changes nothing (full table
  snapshot before/after), a second cancel refunds only once, pickup changes only the
  status and blocks later cancel, unknown user is reported before unknown product.
- Late rule change **E4** (10 % off from three units): implemented together with the team,
  tested so that old and new behaviour are distinguishable (3 stickers cost 135, not 150;
  refund is 135; the discount does not bypass the per-user limit). See `docs/discount_rule_E4.md`.

The other areas (tool registration and read handlers, domain rules and their tests,
SQLite storage and seed data) were written by teammates and are included so the project runs.

## Run

```bash
pip install -r requirements.txt
python3 -m pytest                       # 18 tests, no server needed
python3 -m src.server                   # MCP server over stdio
python3 client.py --help                # local client for manual calls
```

## Notes

- The tests exercise handlers, rules and storage; they do not need `fastmcp`.
  `server.py`, `mcp_adapter.py` and `client.py` need it (they were not re-run while preparing this repository).
- Arithmetic is in whole coins; the discount rounds down.
- The server has no authentication: any `user_id` can act for itself. This is documented
  as a known limit of the learning scenario, not a feature.
- Context: a team assignment from the School 21 (Moscow) intensive.
