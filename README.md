# Finance alert — Bank SMS → Telegram

Fires on **every transaction** (via your bank's SMS), tells you the amount and
how much **budget** you have left this month. Warns you once when your monthly
spend crosses the limit set in `.env`.

```
You swipe card
   │  bank sends SMS instantly
   ▼
iPhone Automation: "When I get a message from <bank>"
   │  POSTs the SMS text to this server
   ▼
server.py ─► parse amount + merchant
   │
   ├─► SQLite (monthly total)
   └─► Telegram message to your phone
```

## Files

| File | Purpose |
|------|---------|
| `server.py`    | Flask server; `/transaction` endpoint the Shortcut hits |
| `parse_sms.py` | Pulls amount/merchant out of the SMS text |
| `core.py`      | Records spend, computes month total, sends alerts |
| `db.py`        | SQLite storage |
| `notify.py`    | Telegram sender |
| `config.py`    | Loads `.env` |
| `Dockerfile`   | Container image for the Flask server |
| `docker-compose.yml` | Runs the server + ngrok tunnel together |

## Setup

### 1. Configure `.env`

```bash
cp .env.example .env
```

Fill in:

| Variable | Where to get it |
|----------|----------------|
| `TELEGRAM_BOT_TOKEN` | Message **@BotFather** → `/newbot` |
| `TELEGRAM_CHAT_ID` | Send any message to your bot, open `https://api.telegram.org/bot<TOKEN>/getUpdates`, copy `chat.id` |
| `WEBHOOK_SECRET` | Any random string — used to authenticate the Shortcut |
| `NGROK_AUTHTOKEN` | [dashboard.ngrok.com/authtokens](https://dashboard.ngrok.com/authtokens) |
| `MONTHLY_BUDGET` | Your monthly spend limit in ₹ |

### 2. Start with Docker

```bash
cd ~/finance-alert
touch finance.db          # create DB file if it doesn't exist yet
docker compose up -d
```

This starts two containers:
- **app** — the Flask server on port 5000
- **ngrok** — public HTTPS tunnel to the server

### 3. Get your ngrok URL

```bash
curl http://localhost:4040/api/tunnels
```

Or open `http://localhost:4040` in a browser. You'll see a URL like:
```
https://xxxx-xx-xx-xx-xx.ngrok-free.app
```

Use this in your iPhone Shortcut.

### 4. Test it

```bash
curl -X POST "https://YOUR_NGROK_URL/transaction?secret=YOUR_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"sms":"Sent Rs.500.00 from Kotak Bank AC X1234 to cafe@upi on 16-06-25"}'
```

You should get a Telegram message.

### 5. iOS Shortcut (the trigger)

Open **Shortcuts** → **Automation** tab → **+**:

1. **When I get a message** → filter by your bank sender name (e.g. "Kotak")
2. Turn **Run Immediately** ON (no confirmation tap needed)
3. Add action **Get Contents of URL**:
   - URL: `https://YOUR_NGROK_URL/transaction?secret=YOUR_WEBHOOK_SECRET`
   - Method: **POST**
   - Request Body: **JSON**, one field — key `sms`, value = the blue **Message** variable from the trigger
4. Save

Now every matching bank SMS fires the shortcut automatically.

## Docker commands

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

## Tuning

- Edit regexes in `parse_sms.py` to match your bank's exact SMS wording — the raw SMS is always stored in SQLite so you can refine against real data
- Change `MONTHLY_BUDGET` in `.env`, then restart: `docker compose up -d`
- Inspect transactions: `sqlite3 finance.db "select * from transactions;"`

## Note on uptime

Docker on Mac runs inside a VM that pauses when your Mac sleeps. The Shortcut will fail while the Mac is asleep. For true 24/7 uptime, deploy to a cloud host (Railway, Render, Fly, or a VPS).
