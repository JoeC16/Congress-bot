import json
import time
import requests
from datetime import datetime, timedelta

# --- CONFIG (hardcoded) ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "YOUR_QUIVER_API_KEY"  # Replace with your actual Quiver API key
QUIVER_TRADE_URL = "https://api.quiverquant.com/beta/live/congresstrading"
QUIVER_CONTRACT_URL = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = {"x-api-key": QUIVER_API_KEY}


# --- Functions ---
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)


def fetch_trades():
    r = requests.get(QUIVER_TRADE_URL, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def fetch_contract_tickers(days=7):
    r = requests.get(QUIVER_CONTRACT_URL, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    tickers = set()
    cutoff = datetime.utcnow() - timedelta(days=days)
    for item in data:
        try:
            contract_date = datetime.strptime(item["Date"], "%Y-%m-%dT%H:%M:%S")
        except:
            continue
        if contract_date >= cutoff and item.get("Ticker"):
            tickers.add(item["Ticker"].upper())
    return tickers


def score_trade(trade, contract_tickers):
    score = 0
    ticker = trade.get("Ticker", "").upper()
    amount = trade.get("Amount", "")
    sector = trade.get("Sector", "").lower()
    asset_type = trade.get("AssetType", "").lower()

    if amount and not amount.startswith("$1,000 or less"):
        score += 1
    if any(x in sector for x in ["tech", "semiconductor", "energy", "defense"]):
        score += 1
    if ticker in ["NVDA", "MSFT", "AAPL", "LMT", "AMD", "AVGO", "XOM", "AMZN"]:
        score += 1
    if "stock" in asset_type or asset_type == "":
        score += 1
    if ticker in contract_tickers:
        score += 2

    return score


def format_trade(trade, contract_match=False):
    rep = trade.get("Representative", "Unknown")
    ticker = trade.get("Ticker", "N/A").upper()
    date = trade.get("ReportDate", "")[:10]
    amount = trade.get("Amount", "N/A")
    link = f"https://www.quiverquant.com/stock/{ticker}"
    msg = (
        f"🚨 <b>New Congressional Trade</b>\n"
        f"👤 {rep}\n"
        f"📅 <b>Filed:</b> {date}\n"
        f"💼 <b>Trade:</b> {amount} of <b>${ticker}</b>\n"
        f"🔗 <a href='{link}'>View on QuiverQuant</a>"
    )
    if contract_match:
        msg += "\n💥 <i>This company received a recent government contract.</i>"
    return msg


def main():
    try:
        print("📡 Scanning...")
        trades = fetch_trades()
        contract_tickers = fetch_contract_tickers()

        filtered = []
        for t in trades:
            if t.get("Transaction", "").lower() != "purchase":
                continue
            score = score_trade(t, contract_tickers)
            if score > 0:
                t["score"] = score
                filtered.append(t)

        top5 = sorted(filtered, key=lambda x: x["score"], reverse=True)[:5]

        for t in top5:
            ticker = t.get("Ticker", "").upper()
            has_contract = ticker in contract_tickers
            message = format_trade(t, contract_match=has_contract)
            send_telegram(message)
            time.sleep(1.5)

        print(f"✅ Sent {len(top5)} trade alerts.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        send_telegram("❌ Bot failed to complete scan.")

if __name__ == "__main__":
    main()
