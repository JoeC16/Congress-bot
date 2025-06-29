import requests
import time

# --- Hardcoded API Keys & IDs ---
QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"
TELEGRAM_TOKEN = "6514863298:AAGJHkK-jv7DhExUvnk-j-F7DUw3XjMWk38"
TELEGRAM_CHAT_ID = "-1002094978297"

# --- API Endpoints ---
TRADING_ENDPOINT = "https://api.quiverquant.com/beta/live/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"

# --- Headers ---
HEADERS = {"x-api-key": QUIVER_API_KEY}

# --- High-signal tickers for priority scoring ---
PRIORITY_TICKERS = {"NVDA", "MSFT", "AAPL", "AMZN", "GOOG", "META", "TSLA"}

# --- Telegram Message Sender ---
def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Telegram send error: {e}")

# --- Fetch Data Functions ---
def fetch_trades():
    try:
        r = requests.get(TRADING_ENDPOINT, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Trade API error: {e}")
        return []

def fetch_contracts():
    try:
        r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Contracts API error: {e}")
        return []

# --- Scoring Function ---
def score_trade(trade, contracts):
    ticker = trade.get("Ticker", "").upper()
    amount_str = trade.get("Amount", "")
    score = 0

    # Score by trade size
    if "1000001" in amount_str or "500001" in amount_str:
        score += 3
    elif "100001" in amount_str:
        score += 2
    elif "15001" in amount_str:
        score += 1

    # Score by priority ticker
    if ticker in PRIORITY_TICKERS:
        score += 2

    # Score by matching gov contract
    if any(ticker in c.get("Ticker", "") for c in contracts):
        score += 2
        trade["GovMatch"] = True
    else:
        trade["GovMatch"] = False

    return score

# --- Main Execution ---
def main():
    send_message("✅ Bot started and is scanning for trades...")

    trades = fetch_trades()
    contracts = fetch_contracts()

    if not trades:
        send_message("❌ Bot failed to fetch congressional trades.")
        return

    # Score and sort
    for t in trades:
        t["Score"] = score_trade(t, contracts)

    top_trades = sorted(trades, key=lambda x: x["Score"], reverse=True)[:5]

    if not top_trades:
        send_message("⚠️ No high-signal trades found.")
        return

    for t in top_trades:
        rep = t.get("Representative", "Unknown")
        ticker = t.get("Ticker", "N/A").upper()
        amount = t.get("Amount", "N/A")
        date = t.get("ReportDate", "Unknown")
        govflag = "✅ Gov Contract" if t.get("GovMatch") else "❌ No Gov Contract"

        url = f"https://www.quiverquant.com/stock/{ticker}"
        message = (
            f"🚨 <b>New Congressional Trade</b>\n"
            f"👤 {rep}\n"
            f"📅 <b>Filed:</b> {date}\n"
            f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
            f"🏛️ {govflag}\n"
            f"🔗 <a href='{url}'>View on QuiverQuant</a>"
        )
        send_message(message)
        time.sleep(1.1)

if __name__ == "__main__":
    main()
