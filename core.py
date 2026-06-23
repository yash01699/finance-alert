"""Ties the pieces together: record a spend, notify."""
import config
import db
import notify


def _fmt(amount) -> str:
    if amount is None:
        return "?"
    return f"₹{amount:,.2f}"


def handle_transaction(amount: float, merchant: str | None, raw_sms: str | None):
    """Process one detected debit. Returns a summary dict."""
    db.record_transaction(amount, merchant, None, raw_sms)
    spent = db.month_total()
    budget = config.MONTHLY_BUDGET
    budget_left = budget - spent
    over = spent > budget

    where = f" at <b>{merchant}</b>" if merchant else ""
    lines = [
        f"💸 Spent {_fmt(amount)}{where}",
        f"📅 This month: {_fmt(spent)} / {_fmt(budget)}",
    ]
    if budget_left >= 0:
        lines.append(f"🟢 Budget left: {_fmt(budget_left)}")
    else:
        lines.append(f"🔴 Over budget by {_fmt(-budget_left)}")
    notify.send("\n".join(lines))

    if over and not db.already_alerted_this_month():
        notify.send(
            f"⚠️ <b>Budget exceeded!</b>\n"
            f"You've spent {_fmt(spent)} this month, over your "
            f"{_fmt(budget)} limit by {_fmt(spent - budget)}."
        )
        db.mark_alerted()

    return {
        "amount": amount,
        "merchant": merchant,
        "spent_this_month": spent,
        "budget_left": budget_left,
        "over_budget": over,
    }
