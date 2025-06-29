import requests
import time
from telegram import Bot
from telegram.constants import ParseMode

# --- HARDCODED CREDENTIALS ---
TELEGRAM_TOKEN = "7526029013:AAHnrL0gKEuuGj_lL71aypUTa5Rdz-oxYRE"
TELEGRAM_CHAT_ID = 1430731878
QUIVER_API_KEY = "7b4295f308c82b0f8594adb7765ade174b9b9884"

# --- API ENDPOINTS ---
TRADE_URL = "https://api.quiverquant.com/beta/live/congresstrading"
CONTRACT_URL = "https://api.quiverquant.com/beta/live/govcontractsall"
HEADERS = {"x-api-key": QUIVER_API_KEY}

# --- INIT TELEGRAM BOT ---
bot = Bot(token=TELEGRAM_TOKEN)

# --- FETCH QUANT DATA ---
def fetch_data(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ ERROR fetching data: {e}")
        return []

congress_trades = fetch_data(TRADE_URL)
gov_contracts = fetch_data(CONTRACT_URL)

# --- GOV CONTRACT TICKERS ---
contract_tickers = {c.get("Ticker", "").upper() for c in gov_contracts if c.get("Ticker")}

# --- SCORING ---
def score_trade(trade):
    amount = trade.get("Amount", "")
    ticker = trade.get("Ticker", "").upper()
    score = 0

    if "1,000,001" in amount:
        score += 5
    elif "500,001" in amount:
        score += 4
    elif "100,001" in amount:
        score += 3
    elif "15,001" in amount:
        score += 2
    elif "1,001" in amount:
        score += 1

    if ticker in contract_tickers:
        score += 2

    return score

# --- FORMAT MESSAGE ---
def format_trade(trade, rank):
    rep = trade.get("Representative", "Unknown")
    date = trade.get("TransactionDate", "Unknown")
    ticker = trade.get("Ticker", "Unknown")
    amount = trade.get("Amount", "N/A")
    amount_display = amount if amount != "N/A" else "Undisclosed"
    gov_contract_note = "✅ Gov Contract" if ticker in contract_tickers else ""
    link = f"https://www.quiverquant.com/stock/{ticker}"

    return (
        f"🔻 <b>Top {rank} Congressional Trade</b>\n"
        f"👤 {rep}\n"
        f"📅 <b>Filed:</b> {date}\n"
        f"💼 <b>Trade:</b> {amount_display} of <b>${ticker}</b>\n"
        f"{gov_contract_note}\n"
        f"🔗 <a href='{link}'>View on QuiverQuant</a>"
    )

# --- SELECT & SEND TOP 5 ---
ranked_trades = sorted(congress_trades, key=score_trade, reverse=True)[:5]

for i, trade in enumerate(ranked_trades, start=1):
    msg = format_trade(trade, i)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
    time.sleep(1.2)
