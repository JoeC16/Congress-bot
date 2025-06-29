import json
import requests
from datetime import datetime, timedelta

# --- Hardcoded Config ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = {"Authorization": f"Bearer {QUIVER_API_KEY}"}


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
    for item in fetch_contracts():
        date_str = item.get("Date", "")[:10]
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj >= cutoff and item.get("Ticker"):
                tickers.add(item["Ticker"].upper())
        except:
            continue
    return tickers


def score_trade(trade, bonus_tickers):
    try:
        amount = trade.get("Amount", "").lower()
        sector = trade.get("Sector", "").lower()
        asset_type = trade.get("AssetType", "").lower()
        ticker = trade.get("Ticker", "").upper()
        transaction = trade.get("Transaction", "").lower()
        filed = trade.get("Filed", "")

        filed_date = datetime.strptime(filed[:10], "%Y-%m-%d")
        if filed_date < datetime.utcnow() - timedelta(days=7):
            return 0
        if transaction != "purchase":
            return 0

        score = 0
        # Value ranges
        amount_scores = {
            ">$5,000,000": 4,
            "$1,000,001 - $5,000,000": 3,
            "$100,001 - $250,000": 2,
            "$15,001 - $50,000": 1
        }
        for range_val, val in amount_scores.items():
            if range_val.lower() in amount:
                score += val
                break

        # Additions
        if any(x in sector for x in ["tech", "defense", "semiconductor", "energy"]):
            score += 1
        if "stock" in asset_type or not asset_type:
            score += 1
        if ticker in ["MSFT", "AAPL", "GOOGL", "NVDA", "AMZN", "LMT", "XOM", "RTX"]:
            score += 1
        if ticker in bonus_tickers:
            score += 2

        return score
    except Exception as e:
        print(f"Scoring error: {e}")
        return 0


def format_message(trade, bonus=False):
    rep = trade.get("Name", "Unknown")
    ticker = trade.get("Ticker", "N/A")
    date = trade.get("Filed", "")[:10]
    amount = trade.get("Amount", "N/A")
    url = f"https://www.quiverquant.com/congresstrading/{ticker.upper()}"

    msg = (
        f"🚨 <b>New Congressional Trade</b>\n"
        f"👤 <b>{rep}</b>\n"
        f"📅 <b>Filed:</b> {date}\n"
        f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
        f"🔗 <a href='{url}'>View on QuiverQuant</a>"
    )
    if bonus:
        msg += "\n💥 <i>BONUS: This company received a recent government contract.</i>"
    return msg


def main():
    print("📡 Bot running...")
    try:
        trades = fetch_trades()
        bonus_tickers = get_recent_contract_tickers()
    except Exception as e:
        send_message(f"❌ API error: {e}")
        return

    scored = []
    for trade in trades:
        score = score_trade(trade, bonus_tickers)
        if score > 0:
            trade["score"] = score
            scored.append(trade)

    top_trades = sorted(scored, key=lambda x: x["score"], reverse=True)[:5]

    if not top_trades:
        send_message("📭 No high-scoring congressional trades found.")
        return

    for trade in top_trades:
        bonus = trade.get("Ticker", "").upper() in bonus_tickers
        msg = format_message(trade, bonus)
        send_message(msg)


if __name__ == "__main__":
    main()
