import time
import requests

# --- Hardcoded credentials ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "e3fbd99b6ff08c6c73ba3b507942db16"

# --- API setup ---
HEADERS = {"Authorization": f"Bearer {QUIVER_API_KEY}"}
TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
MAX_TRADES = 5

# --- Send Telegram message ---
def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# --- Load contract tickers for bonus scoring ---
def fetch_contracts():
    r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
    r.raise_for_status()
    return {c["Ticker"] for c in r.json() if "Ticker" in c}

# --- Load all recent trades ---
def fetch_trades():
    r = requests.get(TRADING_ENDPOINT, headers=HEADERS)
    r.raise_for_status()
    return r.json()

# --- Score trade based on logic ---
def score_trade(t, contract_bonus_set):
    score = 0
    amount_str = t.get("Amount", "").replace("$", "").replace(",", "")
    try:
        amount = float(amount_str)
        if amount >= 500000:
            score += 3
        elif amount >= 100000:
            score += 2
        elif amount >= 15000:
            score += 1
    except:
        pass

    ticker = t.get("Ticker", "").upper()
    if ticker in {"NVDA", "MSFT", "AAPL", "TSLA", "LMT", "PLTR"}:
        score += 2
    if ticker in contract_bonus_set:
        score += 3

    return score

# --- Main logic ---
def main():
    send_message("✅ Bot started and is scanning for trades...")

    try:
        contracts = fetch_contracts()
        trades = fetch_trades()
    except Exception as e:
        send_message("❌ Bot failed to complete scan.")
        return

    scored_trades = []
    for trade in trades:
        if trade.get("Transaction", "").lower() != "purchase":
            continue
        trade["score"] = score_trade(trade, contracts)
        scored_trades.append(trade)

    top_trades = sorted(scored_trades, key=lambda x: x["score"], reverse=True)[:MAX_TRADES]

    for trade in top_trades:
        rep = trade.get("Representative", "Unknown")
        ticker = trade.get("Ticker", "N/A").upper()
        date = trade.get("ReportDate", "Unknown")
        amount = trade.get("Amount", "N/A")
        url = f"https://www.quiverquant.com/stock/{ticker}"

        contract_flag = " 💥 GOV CONTRACT" if ticker in contracts else ""
        message = (
            f"🚨 <b>New Congressional Trade</b>{contract_flag}\n"
            f"👤 {rep}\n"
            f"📅 <b>Filed:</b> {date}\n"
            f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
            f"🔗 <a href='{url}'>View on QuiverQuant</a>"
        )

        send_message(message)
        time.sleep(1.1)

if __name__ == "__main__":
    main()
