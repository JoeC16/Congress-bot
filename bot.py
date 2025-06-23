import os
import requests
import sqlite3
from datetime import datetime, timedelta
from telegram import Bot

# --- Config ---
QUANT_API_KEY = os.getenv("QUANT_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TRADING_ENDPOINT = "https://api.quiverquant.com/beta/historical/congresstradingall"
CONTRACTS_ENDPOINT = "https://api.quiverquant.com/beta/historical/govcontractsall"
DB_FILE = "posted_trades.db"

# --- DB Setup ---
def init_db():
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

# --- Trade Analysis ---
def is_high_potential(trade, bonus_tickers):
    amount = trade.get("Amount", "")
    sector = trade.get("Sector", "").lower() if trade.get("Sector") else ""
    asset_type = trade.get("AssetType", "").lower()
    ticker = trade.get("Ticker", "").upper()

    big_trade = any(x in amount for x in ["$15,001", "$50,000", "$100,000", "$250,000", "$500,000"])
    good_sector = any(x in sector for x in ["tech", "energy", "defense", "semiconductor"])
    good_asset = "stock" in asset_type or asset_type == ""
    strong_ticker = ticker in ["MSFT", "AAPL", "GOOGL", "NVDA", "AMZN", "LMT", "XOM", "RTX"]

    filed_date = datetime.strptime(trade["ReportDate"], "%Y-%m-%dT%H:%M:%S")
    recent = filed_date >= datetime.utcnow() - timedelta(days=2)

    is_bonus = ticker in bonus_tickers

    return recent and big_trade and (good_sector or strong_ticker or is_bonus) and good_asset, is_bonus

def format_trade(trade, bonus=False):
    name = trade["Representative"]
    ticker = trade["Ticker"]
    date = trade["ReportDate"][:10]
    amount = trade["Amount"]
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

    msg += "\n🔍 High-potential trade detected based on size, sector, or federal funding profile."
    return msg

# --- Main Bot Logic ---
def main():
    init_db()
    trades = fetch_recent_trades()
    bonus_tickers = get_recent_contract_tickers()
    bot = Bot(token=TELEGRAM_TOKEN)

    for trade in trades:
        trade_id = f"{trade['Representative']}-{trade['TransactionDate']}-{trade['Ticker']}"
        if is_new_trade(trade_id):
            high_potential, is_bonus = is_high_potential(trade, bonus_tickers)
            if high_potential:
                msg = format_trade(trade, bonus=is_bonus)
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

if __name__ == "__main__":
    main()
