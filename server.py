"""Local server the iOS Shortcut POSTs to whenever a bank SMS arrives.

Endpoints:
  GET  /health        -> liveness check
  POST /transaction   -> the SMS trigger (auth via ?secret= or X-Secret header)
  GET  /summary       -> this month's spend so far (handy for testing)

The Shortcut sends the raw SMS text; the server parses out the amount, fetches
EFFAVL from Kotak, records it, and pushes a Telegram alert.
"""
from flask import Flask, request, jsonify

import config
import db
import core
from parse_sms import parse_sms

app = Flask(__name__)
db.init_db()


def _authorized(req) -> bool:
    secret = req.args.get("secret") or req.headers.get("X-Secret")
    return secret == config.WEBHOOK_SECRET


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.get("/summary")
def summary():
    if not _authorized(request):
        return jsonify(error="unauthorized"), 401
    spent = db.month_total()
    return jsonify(
        spent_this_month=spent,
        budget=config.MONTHLY_BUDGET,
        budget_left=config.MONTHLY_BUDGET - spent,
    )


@app.post("/transaction")
def transaction():
    if not _authorized(request):
        return jsonify(error="unauthorized"), 401

    # Accept either {"sms": "..."} or an explicit {"amount": 123, "merchant": "..."}.
    data = request.get_json(silent=True) or {}
    raw_sms = data.get("sms") or request.form.get("sms")

    amount = data.get("amount")
    merchant = data.get("merchant")

    if amount is None and raw_sms:
        parsed = parse_sms(raw_sms)
        if not parsed:
            return jsonify(error="could not parse amount from sms",
                           sms=raw_sms), 422
        if not parsed["is_debit"]:
            # A credit / refund -- acknowledge but don't count as spend.
            return jsonify(skipped="not a debit", parsed=parsed), 200
        amount = parsed["amount"]
        merchant = merchant or parsed["merchant"]

    if amount is None:
        return jsonify(error="no amount and no sms provided"), 400

    result = core.handle_transaction(float(amount), merchant, raw_sms)
    return jsonify(ok=True, **result)


if __name__ == "__main__":
    # 0.0.0.0 so your phone on the same network (or ngrok) can reach it.
    app.run(host="0.0.0.0", port=config.PORT)
