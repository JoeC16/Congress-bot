import json
import os
import time
import requests

# --- HARDCODED CONFIG ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = "1430731878"
QUIVER_API_KEY = "qvpub_sHrkgyqbbkkpbXk8CdCDMAUDWqYovOBB"

SENT_FILE = "sent_trades.json"
TRADE_ENDPOINT = "https://api.quiverquant.com/beta/live/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontracts"
HEADERS = {"x-api-key": QUIVER_API_KEY}


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
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Telegram send error: {e}")


def get_recent_contracts():
    try:
        r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
        contracts = r.json()
        recent = {c["Company"] for c in contracts if c.get("Date", "") >= "2025-06-01"}
        return recent
    except Exception as e:
        print(f"⚠️ Contract API error: {e}")
        return set()


def main():
    send_message("✅ Bot started and is scanning for trades...")

    try:
        trades = requests.get(TRADE_ENDPOINT, headers=HEADERS).json()
    except Exception as e:
        print(f"❌ API error: {e}")
        return

    recent_contracts = get_recent_contracts()
    sent_ids = load_sent_ids()

    for trade in trades:
        rep = trade.get("Representative", "Unknown")
        ticker = trade.get("Ticker", "Unknown")
        date = trade.get("ReportDate", "Unknown")
        transaction = trade.get("Transaction", "").lower()
        amount = trade.get("Range", trade.get("Amount", "N/A"))

        if "purchase" not in transaction:
            continue

        trade_id = f"{rep}-{ticker}-{date}"
        if trade_id in sent_ids:
            continue

        url = f"https://www.quiverquant.com/stock/{ticker.upper()}"
        gov_flag = "📄 <b>Gov Contract Awarded</b>\n" if ticker.upper() in recent_contracts else ""

        message = (
            f"🚨 <b>New Congressional Trade</b>\n"
            f"👤 {rep}\n"
            f"📅 <b>Filed:</b> {date}\n"
            f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
            f"{gov_flag}"
            f"🔗 <a href='{url}'>View on QuiverQuant</a>"
        )

        send_message(message)
        print(f"✅ Sent to Telegram: {trade_id}")
        sent_ids.add(trade_id)
        time.sleep(1.1)

    save_sent_ids(sent_ids)


if __name__ == "__main__":
    main()
