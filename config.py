"""
╔══════════════════════════════════════════════════════════╗
║          FINAL BOT CONFIG — 10-15% MONTHLY TARGET        ║
║                                                          ║
║  Strategy: Supertrend + EMA200 + RSI + VWAP              ║
║  Risk:     1.5% per trade  (conservative)                ║
║  Leverage: 10x             (survives bad streaks)        ║
║  R:R:      3:1             (TP = 3 × SL distance)        ║
║  Circuit:  Stop if -8% monthly loss                      ║
╚══════════════════════════════════════════════════════════╝

MATH (₹20,000 capital):
  Risk/trade  = 1.5% = ₹300
  Position    = ₹300 / SL% (e.g. 0.5% SL → ₹60,000 notional)
  Leverage    = 10x  (margin used = ₹6,000 per trade)
  Win payout  = ₹300 × 3 = ₹900
  Loss cost   = ₹300

  3 trades/day × 55% WR:
    Wins:   1.65 × ₹900  = ₹1,485
    Losses: 1.35 × ₹300  = ₹405
    Daily net             = ₹1,080 = 5.4%
    Monthly (20 days)     = ~10-15% ✅
"""

CONFIG = {

    # ══════════════════════════════════════════
    # 🔑 BYBIT API — GET FROM:
    # bybit.com → Profile → API Management
    # Permissions: Unified Trade + Read
    # ══════════════════════════════════════════
    "API_KEY":    "N2B9Z8lrVHQujUnYfP",
    "API_SECRET": "mhC3RvZ3fNsFn3qV1p5fMp88qhyRvO6DorDz",

    # START ON TESTNET FIRST — ALWAYS
    # testnet.bybit.com (free, fake money)
    "TESTNET": True,

    # ══════════════════════════════════════════
    # 📊 PAIRS — Most liquid, tight spreads
    # ══════════════════════════════════════════
    "PAIRS": [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
    ],

    # ══════════════════════════════════════════
    # ⚡ CORE RISK SETTINGS
    # ══════════════════════════════════════════
    "LEVERAGE":           10,      # 10x — safe enough to survive 5 losing trades
    "RISK_PER_TRADE_PCT": 1.5,     # 1.5% of balance per trade
    "SL_ATR_MULT":        1.5,     # SL = entry ± (ATR × 1.5)
    "TP_ATR_MULT":        4.5,     # TP = entry ± (ATR × 4.5) → 3:1 R:R
    "COMPOUNDING":        True,    # Reinvest profits

    # ══════════════════════════════════════════
    # 🛡️ CIRCUIT BREAKERS
    # ══════════════════════════════════════════
    "MAX_MONTHLY_LOSS_PCT":  8.0,  # Stop bot for rest of month if -8%
    "MAX_DAILY_LOSS_PCT":    4.0,  # Stop trading today if -4%
    "MAX_DAILY_TRADES":      6,    # Max trades per day per pair
    "MAX_OPEN_POSITIONS":    2,    # Never hold more than 2 at once
    "MAX_CONSECUTIVE_LOSS":  4,    # Pause 4 hours after 4 losses in a row

    # ══════════════════════════════════════════
    # 📐 SUPERTREND SETTINGS (best for crypto)
    # ══════════════════════════════════════════
    "ST_PERIOD": 10,     # ATR period for Supertrend
    "ST_MULT":   3.0,    # Multiplier (higher = fewer signals, more reliable)

    # ══════════════════════════════════════════
    # 📈 OTHER INDICATOR SETTINGS
    # ══════════════════════════════════════════
    "EMA_TREND":    200,  # Only trade in direction of EMA 200
    "RSI_PERIOD":   14,
    "RSI_MIN_BUY":  45,   # RSI must be above this to buy
    "RSI_MAX_BUY":  70,   # RSI must be below this to buy (not overbought)
    "RSI_MIN_SELL": 30,   # RSI must be above this to sell (not oversold)
    "RSI_MAX_SELL": 55,   # RSI must be below this to sell
    "VWAP_PERIOD":  20,   # Rolling VWAP period

    # ══════════════════════════════════════════
    # ⏱️ TIMEFRAMES
    # ══════════════════════════════════════════
    "TIMEFRAME_ENTRY": "15",   # 15min candles for entry
    "TIMEFRAME_TREND": "60",   # 1H candles for trend direction
    "SCAN_INTERVAL":   60,     # Scan every 60 seconds

    # ══════════════════════════════════════════
    # 📱 TELEGRAM
    # 1. Message @BotFather → /newbot → get TOKEN
    # 2. Message your bot once
    # 3. Visit: api.telegram.org/bot<TOKEN>/getUpdates
    # 4. Find your chat id number
    # ══════════════════════════════════════════
    "TELEGRAM_TOKEN":   "8407045841:AAH9sys7d7CJnIn3jCerQBDjj5RzQ2LIWmg",
    "TELEGRAM_CHAT_ID": "TradewithAI7_Bot",

    # ══════════════════════════════════════════
    # 📏 BYBIT MIN QTY (do not change)
    # ══════════════════════════════════════════
    "MIN_QTY": {
        "BTCUSDT": 0.001, "ETHUSDT": 0.01,
        "SOLUSDT": 0.1,   "BNBUSDT": 0.01,
    },
    "QTY_DECIMALS": {
        "BTCUSDT": 3, "ETHUSDT": 2,
        "SOLUSDT": 1, "BNBUSDT": 2,
    },
}
