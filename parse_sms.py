"""Best-effort extraction of (amount, merchant, is_debit) from a Kotak SMS.

Kotak debit SMS come in a few shapes, e.g.:
  "Sent Rs.500.00 from Kotak Bank AC X1234 to some-upi@bank on 16-06-25..."
  "Rs 1,250.00 debited from your A/c XXXX1234 ... at AMAZON ..."
  "Your A/c XXXX1234 is debited for Rs.99.00 ..."
Credits ("credited", "received") are ignored — they are income, not spend.

This is heuristic. The raw SMS is always stored so nothing is lost, and you
can tune the regexes to match the exact wording your bank sends you.
"""
import re

# Rs / Rs. / INR / ₹  followed by an amount with optional thousands separators.
_AMOUNT_RE = re.compile(
    r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)

_DEBIT_WORDS = ("debited", "sent", "spent", "withdrawn", "paid", "debit")
_CREDIT_WORDS = ("credited", "received", "credit", "refund", "reversed")

# Try to grab a merchant / payee after common prepositions.
_MERCHANT_RE = re.compile(
    r"(?:\bto\b|\bat\b|towards)\s+([A-Za-z0-9@._\- ]{2,40}?)(?:\s+on\b|\.|,|$)",
    re.IGNORECASE,
)


def parse_sms(text: str):
    """Return dict(amount, merchant, is_debit) or None if no amount found."""
    if not text:
        return None

    lower = text.lower()
    is_credit = any(w in lower for w in _CREDIT_WORDS)
    is_debit = any(w in lower for w in _DEBIT_WORDS)

    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))

    merchant = None
    mm = _MERCHANT_RE.search(text)
    if mm:
        merchant = mm.group(1).strip()

    # If it clearly says credited and not debited, treat as non-spend.
    debit = is_debit and not (is_credit and not is_debit)
    if is_credit and not is_debit:
        debit = False

    return {"amount": amount, "merchant": merchant, "is_debit": debit}
