import json
import requests
from datetime import datetime, timedelta

# --- Hardcoded config ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = {"Authorization": f"Bearer {QUIVER_API_KEY}"}

# --- Utility functions ---
def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, data=payload)

def fetch_trades():
    r = requests.get(TRADING_ENDPOINT, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def fetch_contracts():
    r = requests.get(CONTRACTS_ENDPOINT, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def get_recent_contract_tickers(days=7):
    tickers = set()
    cutoff = datetime.utcnow() - timedelta(days=days)
    for c in fetch_contracts():
        date_str = c.get("Date", "")
        try:
            date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if date_obj >= cutoff and c.get("Ticker"):
                tickers.add(c["Ticker"].upper())
        except:
            continue
    return tickers

def score_trade(trade, bonus_tickers):
    score = 0
    amount = trade.get("Amount", "")
    sector = trade.get("Sector", "").lower()
    asset_type = trade.get("AssetType", "").lower()
    ticker = trade.get("Ticker", "").upper()
    transaction = trade.get("Transaction", "").lower()
    date_str = trade.get("Filed", "")

    try:
        filed_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        if filed_date < datetime.utcnow() - timedelta(days=7):
            return 0
    except:
        return 0

    if transaction != "purchase":
        return 0

    if not amount.startswith("$1,000 or less"):
        score += 1
    if any(x in sector for x in ["tech", "energy", "defense", "semiconductor"]):
        score += 1
    if "stock" in asset_type or asset_type == "":
        score += 1
    if ticker in ["MSFT", "AAPL", "GOOGL", "NVDA", "AMZN", "LMT", "XOM", "RTX"]:
        score += 1
    if ticker in bonus_tickers:
        score += 2

    return score

def format_message(trade, has_contract):
    rep = trade.get("Name", "Unknown")
    ticker = trade.get("Ticker", "N/A")
    date = trade.get("Filed", "")[:10]
    amount = trade.get("Amount", "N/A")
    link = f"https://www.quiverquant.com/congresstrading/{ticker.upper()}"

    msg = (
        f"🚨 <b>New Congressional Trade</b>\n"
        f"👤 <b>{rep}</b>\n"
        f"📅 <b>Filed:</b> {date}\n"
        f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
        f"🔗 <a href='{link}'>View on QuiverQuant</a>"
    )
    if has_contract:
        msg += "\n💥 <i>BONUS: This company received a recent government contract.</i>"
    return msg

# --- Main ---
def main():
    print("📡 Running bot scan...")

    try:
        trades = fetch_trades()
        bonus_tickers = get_recent_contract_tickers()
    except Exception as e:
        print(f"❌ API fetch error: {e}")
        return

    # Score and sort trades
    scored = []
    for trade in trades:
        score = score_trade(trade, bonus_tickers)
        if score > 0:
            trade["score"] = score
            scored.append(trade)

    top_trades = sorted(scored, key=lambda x: x["score"], reverse=True)[:5]

    if not top_trades:
        send_message("📭 No high-scoring congressional trades found this run.")
        return

    for trade in top_trades:
        ticker = trade.get("Ticker", "").upper()
        has_contract = ticker in bonus_tickers
        msg = format_message(trade, has_contract)
        send_message(msg)

if __name__ == "__main__":
    main()
