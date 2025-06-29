import json
import time
import requests
import os

# --- Hardcoded tokens ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = "1430731878"
QUIVER_API_KEY = "fCwaEjCyRUoaCglXcBLfubImyKZfQfdu4eOSyxvL"  # ✅ Replace with updated key if needed

# --- API Endpoints ---
TRADE_ENDPOINT = "https://api.quiverquant.com/beta/live/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontracts"
HEADERS = {"x-api-key": QUIVER_API_KEY}

# --- State File ---
SENT_FILE = "sent_trades.json"

def load_sent_ids():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent_ids(ids):
    with open(SENT_FILE, "w") as f:
        json.dump(list(ids), f)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

def get_recent_contracts():
    try:
        r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
        contracts = r.json()
        recent = {c.get("Company", "") for c in contracts if c.get("Date", "") >= "2025-06-01"}
        return recent
    except Exception as e:
        print(f"⚠️ Contract API error: {e}")
        return set()

def main():
    send_message("✅ Bot started and is scanning for trades...")

    sent_ids = sent()

    try:
        r = requests.get(TRADE_ENDPOINT, headers=HEADERS)
        trades = r.json()
    except Exception as e:
        print(f"❌ Trade API error: {e}")
        return

    recent_contracts = get_recent_contracts()

    for trade in trades:
        if not isinstance(trade, dict):
            continue

        rep = trade.get("Representative", "Unknown")
        ticker = trade.get("Ticker", "Unknown")
        date = trade.get("ReportDate", "Unknown")
        transaction = trade.get("Transaction", "").lower()
        amount = trade.get("Amount", "N/A")

        if "purchase" not in transaction:
            continue

        trade_id = f"{rep}-{ticker}-{date}"
        if trade_id in sent_ids:
            continue

        contract_flag = ""
        if ticker and any(ticker.lower() in company.lower() for company in recent_contracts):
            contract_flag = "\n🏛️ <b>Recent Gov Contract Awarded</b>"

        url = f"https://www.quiverquant.com/stock/{ticker.upper()}"

        message = (
            f"🚨 <b>New Congressional Trade</b>\n"
            f"👤 {rep}\n"
            f"📅 <b>Filed:</b> {date}\n"
            f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
            f"🔗 <a href='{url}'>View on QuiverQuant</a>{contract_flag}"
        )

        send_message(message)
        print(f"✅ Sent to Telegram: {trade_id}")
        sent_ids.add(trade_id)
        time.sleep(1)

    save_sent_ids(sent_ids)

if __name__ == "__main__":
    main()
