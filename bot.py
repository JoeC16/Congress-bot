import json
import time
import requests

# --- Hardcoded credentials ---
TELEGRAM_TOKEN = "6874043235:AAGzbsM-jWUbZYN7nG1xOsOCD9-3_4D5C0U"
TELEGRAM_CHAT_ID = "-1002092198009"
QUIVER_API_KEY = "q4b0x0qf9f1b4xrn9yzv"

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = {"x-api-key": QUIVER_API_KEY}

MAX_TRADES = 5

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
        print(f"Failed to send message: {e}")

def get_gov_contract_tickers():
    try:
        r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
        r.raise_for_status()
        return set(entry["Ticker"] for entry in r.json() if "Ticker" in entry)
    except Exception as e:
        print(f"❌ Contract API error: {e}")
        send_message("❌ Bot failed to complete scan.")
        return set()

def fetch_trades():
    try:
        r = requests.get(TRADING_ENDPOINT, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Trade API error: {e}")
        send_message("❌ Bot failed to complete scan.")
        return []

def score_trade(trade, contract_tickers):
    score = 0
    ticker = trade.get("Ticker", "").upper()
    amount_raw = trade.get("Amount", "").replace("$", "").replace(",", "")
    amount_score = 0
    try:
        amount = float(amount_raw)
        if amount >= 500000:
            amount_score = 3
        elif amount >= 100000:
            amount_score = 2
        elif amount >= 15000:
            amount_score = 1
    except:
        pass
    score += amount_score

    if ticker in {"NVDA", "MSFT", "AAPL", "TSLA", "LMT", "PLTR"}:
        score += 2
    if ticker in contract_tickers:
        score += 3

    return score

def main():
    send_message("✅ Bot started and is scanning for trades...")

    trades = fetch_trades()
    if not trades:
        return

    contract_tickers = get_gov_contract_tickers()

    scored_trades = []
    for trade in trades:
        if trade.get("Transaction", "").lower() != "purchase":
            continue
        trade["score"] = score_trade(trade, contract_tickers)
        scored_trades.append(trade)

    top_trades = sorted(scored_trades, key=lambda x: x["score"], reverse=True)[:MAX_TRADES]

    for trade in top_trades:
        rep = trade.get("Representative", "Unknown")
        ticker = trade.get("Ticker", "Unknown")
        date = trade.get("ReportDate", "Unknown")
        amount = trade.get("Amount", "N/A")
        url = f"https://www.quiverquant.com/stock/{ticker}"

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
