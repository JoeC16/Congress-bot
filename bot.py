import os
import requests
import sqlite3
from datetime import datetime, timedelta
from telegram import Bot

# --- Config ---
QUANT_API_KEY = os.getenv("QUANT_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/bulk/congresstrading"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/live/govcontractsall"
DB_FILE = "posted_trades.db"

# --- DB Setup ---
def init_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)  # ❌ wipe old DB
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

def is_new_trade(trade_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM trades WHERE id=?", (trade_id,))
    exists = cur.fetchone()
    if not exists:
        cur.execute("INSERT INTO trades (id) VALUES (?)", (trade_id,))
        conn.commit()
    conn.close()
    return not exists

# --- API Fetching ---
def fetch_recent_trades():
    if not QUANT_API_KEY:
        raise ValueError("❌ QUANT_API_KEY is missing.")
    headers = {"Authorization": f"Bearer {QUANT_API_KEY}"}
    r = requests.get(TRADING_ENDPOINT, headers=headers)
    if r.status_code != 200:
        print(f"❌ Trade fetch failed: {r.status_code} - {r.text}")
        r.raise_for_status()
    return r.json()

def fetch_recent_contracts():
    headers = {"Authorization": f"Bearer {QUANT_API_KEY}"}
    r = requests.get(CONTRACTS_ENDPOINT, headers=headers)
    r.raise_for_status()
    return r.json()

def get_recent_contract_tickers(days=7):
    data = fetch_recent_contracts()
    recent_tickers = set()
    cutoff = datetime.utcnow() - timedelta(days=days)
    for item in data:
        try:
            contract_date = datetime.strptime(item["Date"], "%Y-%m-%dT%H:%M:%S")
            if contract_date >= cutoff:
                ticker = item.get("Ticker", "").upper()
                if ticker:
                    recent_tickers.add(ticker)
        except:
            continue
    return recent_tickers

# --- Trade Scoring ---
def score_trade(trade, bonus_tickers):
    try:
        amount = trade.get("Amount", "")
        sector = trade.get("Sector", "").lower()
        asset_type = trade.get("AssetType", "").lower()
        ticker = trade.get("Ticker", "").upper()
        filed_date = datetime.strptime(trade.get("Filed", ""), "%Y-%m-%dT%H:%M:%S")

        recent = filed_date >= datetime.utcnow() - timedelta(days=7)
        if not recent:
            return 0  # skip old trades

        score = 0

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
    except Exception as e:
        print(f"⚠️ Scoring error: {e}")
        return 0

def format_trade(trade, bonus=False):
    name = trade.get("Name", "Unknown")
    ticker = trade.get("Ticker", "N/A")
    date = trade.get("Filed", "")[:10]
    amount = trade.get("Amount", "N/A")
    link = f"https://www.quiverquant.com/congresstrading/{ticker.upper()}"

    msg = (
        f"🚨 New Congressional Trade Alert\n\n"
        f"👤 {name}\n"
        f"📅 Filed: {date}\n"
        f"💼 Bought: {amount} of ${ticker.upper()}\n"
        f"📍 View: {link}\n"
    )
    if bonus:
        msg += "\n💥 BONUS: This company also received a recent government contract.\n"

    msg += "\n🔍 Trade ranked as high-potential based on timing, size, sector, and contracts."
    return msg

# --- Main Bot Logic ---
def main():
    print("🟢 Congress Bot Starting...")
    init_db()

    try:
        trades = fetch_recent_trades()
        bonus_tickers = get_recent_contract_tickers()
        bot = Bot(token=TELEGRAM_TOKEN)

        scored_trades = []
        for trade in trades:
            try:
                score = score_trade(trade, bonus_tickers)
                if score > 0:
                    trade["score"] = score
                    scored_trades.append(trade)
            except Exception as e:
                print(f"⚠️ Error processing trade: {e}")

        # Sort and take top 5
        top_trades = sorted(scored_trades, key=lambda x: x["score"], reverse=True)[:5]

        for trade in top_trades:
            trade_id = f"{trade.get('Name', 'Unknown')}-{trade.get('Traded', 'unknown')}-{trade.get('Ticker', 'N/A')}"
            if is_new_trade(trade_id):
                msg = format_trade(trade, bonus=(trade.get("Ticker", "").upper() in bonus_tickers))
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
                print("✅ Sent trade alert:", trade_id)
            else:
                print("⏭️ Already sent:", trade_id)

        if not top_trades:
            print("⚠️ No trades ranked high enough this week.")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
