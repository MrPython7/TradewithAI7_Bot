"""
Main Bot — Bybit Futures Auto Trader
──────────────────────────────────────────────────────────
Runs 24/7 on VPS. Scans all pairs every 60 seconds.
Places trades automatically with SL/TP on every order.

HOW TO RUN:
  1. Fill in config.py (API keys + Telegram)
  2. Start with TESTNET=True for minimum 2 weeks
  3. pip install pybit pandas numpy requests
  4. python bot.py

ON VPS (keeps running after you disconnect):
  screen -S mybot
  python bot.py
  Ctrl+A then D   ← detach (bot keeps running)
  screen -r mybot ← reattach anytime
"""

import time
import logging
import traceback
from datetime import datetime, timedelta

import pandas as pd
from pybit.unified_trading import HTTP

from config import CONFIG
from strategy import Strategy
from risk_manager import RiskManager
from telegram_bot import Telegram

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log'),
    ]
)
logger = logging.getLogger(__name__)


class Bot:

    def __init__(self):
        self.client  = HTTP(
            testnet    = CONFIG['TESTNET'],
            api_key    = CONFIG['API_KEY'],
            api_secret = CONFIG['API_SECRET'],
        )
        self.strategy = Strategy()
        self.risk     = RiskManager()
        self.telegram = Telegram()
        self.positions = {}   # {symbol: position_dict}
        self.last_daily_msg = None
        logger.info("Bot initialized")

    # ─── FETCH CANDLES ───────────────────────────────────
    def get_candles(self, symbol: str, interval: str,
                    limit: int = 250) -> pd.DataFrame:
        resp = self.client.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        if resp['retCode'] != 0:
            raise Exception(f"Kline error: {resp['retMsg']}")

        rows = resp['result']['list']
        df   = pd.DataFrame(rows, columns=[
            'timestamp','open','high','low','close','volume','turnover'
        ])
        df = df.astype({
            'timestamp':'int64','open':'float','high':'float',
            'low':'float','close':'float','volume':'float'
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df

    # ─── GET BALANCE ─────────────────────────────────────
    def get_balance(self) -> float:
        resp = self.client.get_wallet_balance(accountType="UNIFIED")
        if resp['retCode'] != 0:
            raise Exception(f"Balance error: {resp['retMsg']}")
        coins = resp['result']['list'][0]['coin']
        for coin in coins:
            if coin['coin'] == 'USDT':
                return float(coin['walletBalance'])
        return 0.0

    # ─── SET LEVERAGE ────────────────────────────────────
    def set_leverage(self, symbol: str):
        try:
            self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(CONFIG['LEVERAGE']),
                sellLeverage=str(CONFIG['LEVERAGE']),
            )
        except Exception as e:
            logger.warning(f"Leverage set warning for {symbol}: {e}")

    # ─── PLACE ORDER ─────────────────────────────────────
    def place_order(self, symbol: str, side: str,
                    qty: float, sl: float, tp: float) -> str:
        """Places market order with SL and TP attached."""
        order_side = "Buy" if side == "BUY" else "Sell"
        resp = self.client.place_order(
            category       = "linear",
            symbol         = symbol,
            side           = order_side,
            orderType      = "Market",
            qty            = str(qty),
            stopLoss       = str(sl),
            takeProfit     = str(tp),
            slTriggerBy    = "MarkPrice",
            tpTriggerBy    = "MarkPrice",
            timeInForce    = "GoodTillCancel",
            reduceOnly     = False,
        )
        if resp['retCode'] != 0:
            raise Exception(f"Order error: {resp['retMsg']}")
        return resp['result']['orderId']

    # ─── CLOSE POSITION ──────────────────────────────────
    def close_position(self, symbol: str, side: str, qty: float):
        """Market close a position."""
        close_side = "Sell" if side == "BUY" else "Buy"
        self.client.place_order(
            category    = "linear",
            symbol      = symbol,
            side        = close_side,
            orderType   = "Market",
            qty         = str(qty),
            reduceOnly  = True,
            timeInForce = "GoodTillCancel",
        )

    # ─── GET OPEN POSITIONS ──────────────────────────────
    def get_open_positions(self) -> dict:
        resp = self.client.get_positions(
            category="linear", settleCoin="USDT"
        )
        if resp['retCode'] != 0:
            return {}
        positions = {}
        for p in resp['result']['list']:
            if float(p['size']) > 0:
                positions[p['symbol']] = {
                    'side':       'BUY' if p['side'] == 'Buy' else 'SELL',
                    'size':       float(p['size']),
                    'entry':      float(p['avgPrice']),
                    'unrealised': float(p['unrealisedPnl']),
                    'sl':         float(p['stopLoss']) if p['stopLoss'] else 0,
                    'tp':         float(p['takeProfit']) if p['takeProfit'] else 0,
                }
        return positions

    # ─── SCAN ONE PAIR ───────────────────────────────────
    def scan_pair(self, symbol: str, balance: float):
        try:
            # Get candles for both timeframes
            df_15m = self.get_candles(symbol, CONFIG['TIMEFRAME_ENTRY'], 250)
            df_1h  = self.get_candles(symbol, CONFIG['TIMEFRAME_TREND'],  100)

            # Get signal
            signal = self.strategy.get_signal(df_15m, df_1h)

            if signal['action'] == 'HOLD':
                logger.debug(f"{symbol}: HOLD — {signal['reason']}")
                return

            action = signal['action']

            # Check if already in position
            open_pos = self.get_open_positions()
            if symbol in open_pos:
                # Check for Supertrend flip exit
                existing = open_pos[symbol]
                if (existing['side'] == 'BUY' and action == 'SELL') or \
                   (existing['side'] == 'SELL' and action == 'BUY'):
                    logger.info(f"{symbol}: Supertrend flip — closing {existing['side']}")
                    self.close_position(symbol, existing['side'], existing['size'])
                    pnl = existing['unrealised']
                    self.risk.record_result(pnl)
                    self.risk.close_position(symbol)
                    self.telegram.trade_closed(
                        symbol, existing['side'],
                        existing['entry'], df_15m['close'].iloc[-1],
                        pnl, pnl/balance*100, 'ST_FLIP', balance
                    )
                return

            # Check risk manager
            can, reason = self.risk.can_trade(symbol, balance)
            if not can:
                logger.info(f"{symbol}: BLOCKED — {reason}")
                if 'MONTHLY LOSS' in reason or 'CIRCUIT' in reason:
                    self.telegram.circuit_breaker(reason, balance)
                return

            # Calculate position size
            price    = df_15m['close'].iloc[-1]
            pos_info = self.risk.position_size(
                symbol, price, signal['atr'], balance
            )
            if not pos_info:
                return

            sl, tp = self.risk.sl_tp(action, price, signal['atr'])

            # Set leverage
            self.set_leverage(symbol)

            # Place order
            order_id = self.place_order(
                symbol, action, pos_info['qty'], sl, tp
            )

            # Track
            self.risk.open_position(symbol, action)
            self.positions[symbol] = {
                'side':   action,
                'entry':  price,
                'qty':    pos_info['qty'],
                'sl':     sl,
                'tp':     tp,
                'reason': signal['reason'],
            }

            # Telegram alert
            self.telegram.trade_opened(
                symbol, action, price, pos_info['qty'],
                sl, tp, signal['reason'], signal['confidence'], balance
            )

            logger.info(
                f"✅ {action} {symbol} | "
                f"Price: ${price:,.2f} | SL: ${sl:,.2f} | TP: ${tp:,.2f} | "
                f"Qty: {pos_info['qty']} | Risk: ₹{pos_info['risk_amount']:.0f} | "
                f"Signal: {signal['reason']} ({signal['confidence']}%)"
            )

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            logger.debug(traceback.format_exc())

    # ─── CHECK CLOSED POSITIONS ──────────────────────────
    def check_closed_positions(self, balance: float):
        """Check if any tracked positions were closed by SL/TP."""
        open_now = self.get_open_positions()
        for symbol in list(self.positions.keys()):
            if symbol not in open_now:
                pos = self.positions.pop(symbol)
                # Fetch PnL from closed PnL history
                try:
                    resp = self.client.get_closed_pnl(
                        category="linear", symbol=symbol, limit=1
                    )
                    if resp['retCode'] == 0 and resp['result']['list']:
                        record = resp['result']['list'][0]
                        pnl    = float(record['closedPnl'])
                        exit_p = float(record['avgExitPrice'])
                        etype  = 'TP' if pnl > 0 else 'SL'
                    else:
                        pnl    = 0
                        exit_p = pos['entry']
                        etype  = 'UNKNOWN'

                    self.risk.record_result(pnl)
                    self.risk.close_position(symbol)
                    self.telegram.trade_closed(
                        symbol, pos['side'], pos['entry'],
                        exit_p, pnl, pnl/balance*100, etype, balance
                    )
                    logger.info(
                        f"📊 {symbol} closed | PnL: ₹{pnl:+.0f} | Type: {etype}"
                    )
                except Exception as e:
                    logger.error(f"Error fetching closed PnL for {symbol}: {e}")

    # ─── DAILY SUMMARY ───────────────────────────────────
    def maybe_send_daily_summary(self, balance: float):
        now = datetime.now()
        if now.hour == 20 and (
            self.last_daily_msg is None or
            (now - self.last_daily_msg).seconds > 3600
        ):
            stats = self.risk.daily_summary(balance)
            self.telegram.daily_summary(stats, balance)
            self.last_daily_msg = now

    # ─── MAIN LOOP ───────────────────────────────────────
    def run(self):
        logger.info("=" * 55)
        logger.info("  BYBIT TRADING BOT STARTING")
        logger.info(f"  Mode:     {'TESTNET' if CONFIG['TESTNET'] else '⚠️  LIVE'}")
        logger.info(f"  Strategy: Supertrend + EMA200 + RSI + VWAP")
        logger.info(f"  Pairs:    {', '.join(CONFIG['PAIRS'])}")
        logger.info(f"  Leverage: {CONFIG['LEVERAGE']}x")
        logger.info(f"  Risk:     {CONFIG['RISK_PER_TRADE_PCT']}%/trade")
        logger.info("=" * 55)

        balance = self.get_balance()
        logger.info(f"Starting balance: ₹{balance:,.2f}")
        self.telegram.bot_started(balance, CONFIG['TESTNET'])

        while True:
            try:
                balance = self.get_balance()

                # Check if any positions got closed by exchange
                self.check_closed_positions(balance)

                # Scan each pair for new signals
                for symbol in CONFIG['PAIRS']:
                    self.scan_pair(symbol, balance)
                    time.sleep(1)  # small delay between pairs

                # Daily summary at 8pm
                self.maybe_send_daily_summary(balance)

                logger.info(
                    f"Scan complete | Balance: ₹{balance:,.0f} | "
                    f"Open: {len(self.get_open_positions())} | "
                    f"Next scan in {CONFIG['SCAN_INTERVAL']}s"
                )

                time.sleep(CONFIG['SCAN_INTERVAL'])

            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                logger.debug(traceback.format_exc())
                self.telegram.error(str(e))
                time.sleep(30)  # wait before retrying


# ── ENTRY POINT ──────────────────────────────────────────
if __name__ == '__main__':
    bot = Bot()
    bot.run()
