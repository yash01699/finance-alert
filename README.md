# Finance alert — Kotak SMS trigger + Balance API + Telegram

Fires on **every transaction** (via your bank's SMS), tells you the amount,
how much **budget** you have left this month, and the **real account balance**
(`EFFAVL`) pulled live from Kotak's Balance Enquiry API. Warns you once when
your monthly spend crosses **₹10,000**.

```
You swipe card
   │  bank sends SMS instantly
   ▼
iPhone "Automation: When I get a message from <bank>"  ── the real trigger
   │  POSTs the SMS text to this server
   ▼
server.py ─► parse amount ─► Kotak Balance Enquiry API (EFFAVL)
   │                           │
   ▼                           ▼
SQLite (monthly total)   Telegram message to your phone
```

## Why this shape

Kotak's Balance Enquiry API is **pull-only** — it has no webhook, so it cannot
itself "trigger" on a transaction. Your bank's **transaction SMS** is the real
real-time trigger; the API is used right after to read the authoritative
**EFFAVL** ("Effective Available" — the balance after lien/other liabilities,
which the doc says is the one to consume).

## Files

| File | Purpose |
|------|---------|
| `server.py`    | Flask server; `/transaction` endpoint the Shortcut hits |
| `parse_sms.py` | Pulls amount/merchant out of the SMS text |
| `kotak.py`     | OAuth + FIXML balance enquiry + parses `EFFAVL` |
| `core.py`      | Records spend, computes month total, sends alerts |
| `db.py`        | SQLite storage |
| `notify.py`    | Telegram sender |
| `config.py`    | Loads `.env` |

## Setup

### 1. Install
```bash
cd ~/finance-alert
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit .env
```

### 2. Telegram bot
1. Message **@BotFather** → `/newbot` → copy the **token** into `TELEGRAM_BOT_TOKEN`.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates`, find `chat.id`, put it
   in `TELEGRAM_CHAT_ID`.

### 3. Kotak credentials
Fill the `KOTAK_*` values in `.env` from the tech doc + the OAuth/auth doc Kotak
gives you. UAT values from your doc are already prefilled in `.env.example`.
Leave `MOCK_KOTAK=1` while testing without live credentials.

> The balance-enquiry doc doesn't cover the OAuth handshake. `kotak.py` assumes
> a standard OAuth2 `client_credentials` grant with HTTP Basic auth. If Kotak's
> auth doc differs, adjust `get_token()` and the request headers in `kotak.py`.

### 4. Test it locally (mock mode)
```bash
# in .env set MOCK_KOTAK=1
source .venv/bin/activate
python server.py            # starts on http://0.0.0.0:5000
```
In another terminal:
```bash
curl -X POST "http://localhost:5000/transaction?secret=YOUR_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"sms":"Sent Rs.500.00 from Kotak Bank AC X1234 to cafe@upi on 16-06-25"}'
```
You should get a Telegram message and a JSON response.

### 5. Make the server reachable from your phone
- **Same Wi-Fi (simplest):** use your Mac's LAN IP, e.g. `http://192.168.1.5:5000`.
  Only works when phone + Mac are on the same network and the Mac is awake.
- **Anywhere (recommended):** run `ngrok http 5000` and use the public
  `https://...ngrok...` URL, or deploy `server.py` to a small always-on host
  (Railway / Fly / a VPS).

### 6. iOS Shortcut (the trigger)
On your iPhone, open the **Shortcuts** app → **Automation** tab → **+**:
1. **When I get a message** → choose the sender/bank (or "Message contains" a
   keyword like "debited" / "Kotak").
2. Turn **Run Immediately** ON (no confirmation tap).
3. Add action **Get Contents of URL**:
   - URL: `https://YOUR_SERVER/transaction?secret=YOUR_WEBHOOK_SECRET`
   - Method: **POST**
   - Request Body: **JSON**, one field `sms` = the **Shortcut "Message" variable**.
4. Save. Now every matching bank SMS auto-POSTs to your server.

## Running it for real
- Set `MOCK_KOTAK=0` once your Kotak credentials work.
- Keep `server.py` running (a host, or `ngrok` + your Mac).
- Spend money → get a Telegram ping with amount, budget left, and live balance.

## Tuning
- Edit the regexes in `parse_sms.py` to match your bank's exact SMS wording
  (the raw SMS is always stored in SQLite so you can refine against real data).
- Change `MONTHLY_BUDGET` in `.env`.
- Inspect data: `sqlite3 finance.db "select * from transactions;"`
