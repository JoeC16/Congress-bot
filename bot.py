import json
import time
import requests

QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"
TELEGRAM_TOKEN = "7002229112:AAEda8Oa6UQlgZRGQW7RkL9LhxG6FxGZ0vY"
TELEGRAM_CHAT_ID = "-1002124815390"

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = { "x-api-key": QUIVER_API_KEY }

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def get_data(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ ERROR fetching data: {e}")
        send_message("❌ Bot failed to complete scan.")
        return []

def score_trade(trade, gov_contracts):
    score = 0
    amount = trade.get("Amount", "")
    ticker = trade.get("Ticker", "")
    amount_map = {
        "$1,001 - $15,000": 1,
        "$15,001 - $50,000": 2,
        "$50,001 - $100,000": 3,
        "$100,001 - $250,000": 4,
        "$250,001 - $500,000": 5,
        "$500,001 - $1,000,000": 6,
        "$1,000,001 - $5,000,000": 7,
        "Over $5,000,000": 8
    }
    score += amount_map.get(amount, 0)
    if ticker in ['MSFT', 'AAPL', 'NVDA', 'GOOGL', 'AMZN']:
        score += 2
    if any(ticker in c.get("ContractsAwarded", "") for c in gov_contracts):
        score += 5
    return score

def main():
    send_message("✅ Bot started and is scanning for trades...")

    trades = get_data(TRADING_ENDPOINT)
    contracts = get_data(CONTRACTS_ENDPOINT)

    if not trades:
        return

    sorted_trades = sorted(trades, key=lambda t: score_trade(t, contracts), reverse=True)
    top_trades = sorted_trades[:5]

    for trade in top_trades:
        rep = trade.get("Representative", "Unknown")
        ticker = trade.get("Ticker", "Unknown")
        date = trade.get("ReportDate", "Unknown")
        amount = trade.get("Amount", "N/A")
        url = f"https://www.quiverquant.com/stock/{ticker.upper()}"
        message = (
            f"🚨 <b>New Congressional Trade</b>\n"
            f"👤 {rep}\n"
            f"📅 <b>Filed:</b> {date}\n"
            f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
            f"🔗 <a href='{url}'>View on QuiverQuant</a>"
        )
        send_message(message)
        time.sleep(1)

if __name__ == "__main__":
    main()
