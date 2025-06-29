import requests
from datetime import datetime
from telegram import Bot

# --- Hardcoded Keys ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"

# --- API URLs (Fixed) ---
TRADE_URL = "https://api.quiverquant.com/beta/live/congresstrading/"
CONTRACT_URL = "https://api.quiverquant.com/beta/live/govcontracts/"

# --- Headers ---
HEADERS = {"x-api-key": QUIVER_API_KEY}

# --- Scoring Function ---
def score_trade(trade, contract_tickers):
    score = 0
    ticker = trade.get("Ticker", "").upper()
    amount_range = trade.get("Range", "")

    if amount_range == "$1,001 - $15,000":
        score += 1
    elif amount_range == "$15,001 - $50,000":
        score += 2
    elif amount_range == "$50,001 - $100,000":
        score += 3
    elif amount_range == "$100,001 - $250,000":
        score += 4
    elif amount_range == "$250,001 - $500,000":
        score += 5
    elif amount_range == "$500,001 - $1,000,000":
        score += 6
    elif amount_range == "$1,000,001 - $5,000,000":
        score += 7
    elif amount_range == "$5,000,001 - $25,000,000":
        score += 8
    elif amount_range == "$25,000,001 - $50,000,000":
        score += 9
    elif amount_range == "$50,000,000+":
        score += 10

    if ticker in contract_tickers:
        score += 2

    return score

# --- Fetch Trades ---
def fetch_trades():
    res = requests.get(TRADE_URL, headers=HEADERS)
    res.raise_for_status()
    return res.json()

# --- Fetch Gov Contracts ---
def fetch_gov_contracts():
    res = requests.get(CONTRACT_URL, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    return {item["Ticker"].upper() for item in data if "Ticker" in item}

# --- Format Trade Message ---
def format_trade(trade, score, rank, gov_flag=False):
    ticker = trade.get("Ticker", "N/A")
    politician = trade.get("Representative", "N/A")
    amount = trade.get("Range", "N/A")
    date = trade.get("TransactionDate", "N/A")
    link = f"https://www.quiverquant.com/stock/{ticker}/congresstrading"
    gov_text = "\n🏛️ Gov Contract Detected!" if gov_flag else ""

    return (
        f"🔔 *Top {rank} Congressional Trade*\n"
        f"👤 {politician}\n"
        f"🗓️ Filed: {date}\n"
        f"💰 Trade: {amount} of [${ticker}]({link})\n"
        f"{gov_text}"
    )

# --- Main Bot Logic ---
def send_top_trades():
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        trades = fetch_trades()
        contracts = fetch_gov_contracts()

        # Score and sort
        ranked_trades = []
        for trade in trades:
            ticker = trade.get("Ticker", "").upper()
            score = score_trade(trade, contracts)
            ranked_trades.append((score, trade, ticker in contracts))

        top_trades = sorted(ranked_trades, key=lambda x: x[0], reverse=True)[:5]

        for idx, (score, trade, has_contract) in enumerate(top_trades, start=1):
            message = format_trade(trade, score, idx, has_contract)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ Bot Error: {e}")

# --- Trigger Function ---
if __name__ == "__main__":
    send_top_trades()
