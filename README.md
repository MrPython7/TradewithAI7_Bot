╔══════════════════════════════════════════════════════════════╗
║          BYBIT TRADING BOT — COMPLETE SETUP GUIDE           ║
║          Strategy: Supertrend + EMA200 + RSI + VWAP         ║
║          Target:   10-15% monthly | 10x leverage            ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — BYBIT API KEYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For TESTNET (start here — FREE, fake money):
  1. Go to: testnet.bybit.com
  2. Create account
  3. Profile → API Management → Create New Key
  4. Permissions: ✅ Read  ✅ Unified Trade
  5. Copy API Key and Secret

For LIVE (only after 2+ weeks profitable testnet):
  1. Go to: bybit.com
  2. Same steps as above

Paste into config.py:
  "API_KEY":    "paste_key_here",
  "API_SECRET": "paste_secret_here",
  "TESTNET":    True,   ← keep True until ready for live

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — TELEGRAM BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Open Telegram → search @BotFather
2. Send: /newbot
3. Choose a name: e.g. "MyBybitBot"
4. Choose a username: e.g. "mybybit_bot"
5. BotFather gives you a TOKEN — copy it

6. Open your new bot and send any message (e.g. "hello")
7. Visit this URL in browser (replace YOUR_TOKEN):
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
8. Find "chat":{"id":XXXXXXXXX} — that number is your CHAT_ID

Paste into config.py:
  "TELEGRAM_TOKEN":   "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
  "TELEGRAM_CHAT_ID": "987654321",

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — VPS SERVER SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommended VPS: Contabo / Hetzner / DigitalOcean
Cost: ~₹400–800/month
OS: Ubuntu 22.04

After getting VPS, connect via SSH:
  ssh root@YOUR_VPS_IP

Run these commands one by one:

  # Update system
  apt update && apt upgrade -y

  # Install Python
  apt install python3 python3-pip screen -y

  # Upload bot files (from your computer):
  # Use FileZilla or run this on your LOCAL computer:
  scp -r final_bot_v2/ root@YOUR_VPS_IP:/root/bot/

  # On VPS — install dependencies:
  cd /root/bot
  pip3 install -r requirements.txt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — CONFIGURE AND TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Edit config with your keys:
  nano config.py
  # (Ctrl+X to save)

  # Test run (you should see logs and Telegram message):
  python3 bot.py

  # Check for errors — should see:
  # "Bot initialized"
  # "Starting balance: ₹XX"
  # "Bot STARTED — TESTNET" in Telegram

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — RUN 24/7 WITH SCREEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Start screen session:
  screen -S bybitbot

  # Run bot:
  python3 bot.py

  # Detach (bot keeps running after you close SSH):
  Press Ctrl+A then D

  # Reattach to see logs anytime:
  screen -r bybitbot

  # Stop bot:
  screen -r bybitbot → then Ctrl+C

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — TESTNET RULES (DO NOT SKIP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run on TESTNET for minimum 2 weeks.
Only move to LIVE if BOTH are true:
  ✅ Positive P&L on testnet
  ✅ Bot behaved correctly (proper SL/TP, no errors)

To switch to LIVE:
  config.py → "TESTNET": False
  Replace testnet API keys with LIVE keys

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CIRCUIT BREAKERS (AUTO-PROTECTION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The bot protects you automatically:

  Daily loss > 4%     → No new trades today
  Monthly loss > 8%   → Bot pauses, sends Telegram alert
  4 losses in a row   → 4-hour cool-off period
  2 open positions    → No new entries until one closes

When monthly circuit breaks:
  → You get Telegram alert
  → Review what happened
  → Restart bot next month manually

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILES OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  config.py       — All settings (edit this first)
  strategy.py     — Supertrend + EMA200 + RSI + VWAP logic
  risk_manager.py — Position sizing + circuit breakers
  telegram_bot.py — All Telegram notifications
  bot.py          — Main bot (run this)
  requirements.txt— Python packages to install
  bot.log         — Auto-created log file

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT EACH TELEGRAM ALERT MEANS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🟢 TRADE OPENED  → Bot entered a BUY position
  🔴 TRADE OPENED  → Bot entered a SELL position
  ✅ TRADE CLOSED  → Trade was a WIN (TP hit)
  ❌ TRADE CLOSED  → Trade was a LOSS (SL hit)
  📈 DAILY SUMMARY → Sent at 8pm every day
  ⛔ CIRCUIT BREAK → Monthly/daily loss limit hit
  🚀 BOT STARTED   → Bot just started

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  FINAL WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This bot does NOT guarantee profits.
Crypto trading involves significant risk.
Only trade money you can afford to lose completely.
Start with ₹5,000-10,000 on live, not your full capital.
Always test on TESTNET first — minimum 2 weeks.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
