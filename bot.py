import os
import re
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
        os.remove(DB_FILE)  # wipe on start
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

# --- Strip HTML for Telegram compatibility ---
def strip_html_tags(text):
    return re.sub('<[^<]+?>', '', text)

# --- Fetch from QuiverQuant ---
def fetch_recent_trades():
    headers = {"Authorization": f"Bearer {QUANT_API_KEY}"}
    r = requests.get(TRADING_ENDPOINT, headers=headers)
    r.raise_for_status()
    return r.json()

def fetch_recent_contracts():
    headers = {"Authorization": f"Bearer {QUANT_API_KEY}"}
    r = requests.get(CONTRACTS_ENDPOINT, headers=headers)
    r.raise_for_status()
    return r.json()

def get_recent_contract_tickers(days=7):
    data = fetch_recent_contracts()
    tickers = set()
    cutoff = datetime.utcnow() - timedelta(days=days)
    for item in data:
        try:
            contract_date = datetime.strptime(item["Date"], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            try:
                contract_date = datetime.strptime(item["Date"], "%Y-%m-%d")
            except:
                continue
        if contract_date >= cutoff:
            ticker = item.get("Ticker", "").upper()
            if ticker:
                tickers.add(ticker)
    return tickers

# --- Scoring System ---
def score_trade(trade, bonus_tickers):
    try:
        amount = trade.get("Amount", "")
        sector = trade.get("Sector", "").lower()
        asset_type = trade.get("AssetType", "").lower()
        ticker = trade.get("Ticker", "").upper()
        filed_raw = trade.get("Filed", "")

        try:
            filed_date = datetime.strptime(filed_raw, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            filed_date = datetime.strptime(filed_raw, "%Y-%m-%d")

        if filed_date < datetime.utcnow() - timedelta(days=7):
            return 0

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

# --- Formatter ---
def format_trade(trade, bonus=False):
    name = trade.get("Name", "Unknown")
    ticker = trade.get("Ticker", "N/A")
    date = trade.get("Filed", "")[:10]
    amount = trade.get("Amount", "N/A")
    link = f"https://www.quiverquant.com/congresstrading/{ticker.upper()}"

    msg = (
        f"<b>🚨 New Congressional Trade Alert</b>\n\n"
        f"👤 <b>{name}</b>\n"
        f"📅 Filed: {date}\n"
        f"💼 Bought: {amount} of <b>${ticker.upper()}</b>\n"
        f"🔗 <a href='{link}'>View on QuiverQuant</a>\n"
    )
    if bonus:
        msg += "\n💥 <i>BONUS: This company received a recent government contract.</i>\n"

    msg += "\n🔍 <i>Ranked as high-potential based on timing, size, sector & contracts.</i>"
    return msg

# --- Main ---
def main():
    print("🟢 Congress Bot Starting...")
    init_db()

    try:
        trades = fetch_recent_trades()
        bonus_tickers = get_recent_contract_tickers()
        bot = Bot(token=TELEGRAM_TOKEN)

        scored = []
        for trade in trades:
            score = score_trade(trade, bonus_tickers)
            if score > 0:
                trade["score"] = score
                scored.append(trade)

        top = sorted(scored, key=lambda x: x["score"], reverse=True)[:5]

        for i, trade in enumerate(top, 1):
            trade_id = f"{trade.get('Name')}-{trade.get('Traded')}-{trade.get('Ticker')}"
            if is_new_trade(trade_id):
                raw_msg = format_trade(trade, bonus=(trade.get("Ticker", "").upper() in bonus_tickers))
                plain_msg = strip_html_tags(raw_msg)
                print(f"📤 Sending Telegram alert:\n#{i}: {plain_msg}\n")
                bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=plain_msg,
                    parse_mode=None,
                    disable_web_page_preview=True
                )
                print(f"✅ Telegram alert sent for {trade_id}")
            else:
                print(f"⏭️ Already sent: {trade_id}")

        if not top:
            print("⚠️ No trades ranked high enough this week.")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
