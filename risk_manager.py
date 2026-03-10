"""
Risk Manager — Position Sizing + Circuit Breakers
───────────────────────────────────────────────────
Every trade goes through this before execution.
If any check fails → trade is REJECTED.
"""

import math
import logging
from datetime import datetime, date
from config import CONFIG

logger = logging.getLogger(__name__)


class RiskManager:

    def __init__(self):
        self.daily_pnl      = {}   # {date: float}
        self.monthly_pnl    = {}   # {"2024-01": float}
        self.consecutive_loss = 0
        self.last_loss_time   = None
        self.open_positions   = {}  # {symbol: side}

    # ─── POSITION SIZE ───────────────────────────────────
    def position_size(self, symbol: str, price: float,
                      atr: float, balance: float) -> dict:
        """
        Returns exact qty to trade.
        Formula:
          risk_amount = balance × RISK_PCT
          sl_distance = ATR × SL_MULT
          sl_pct      = sl_distance / price
          notional    = risk_amount / sl_pct
          qty         = notional / price
        """
        risk_amount  = balance * (CONFIG['RISK_PER_TRADE_PCT'] / 100)
        sl_distance  = atr * CONFIG['SL_ATR_MULT']
        sl_pct       = sl_distance / price

        # Safety: SL must be 0.2%–5% away
        if sl_pct < 0.002:
            logger.warning(f"{symbol}: SL too tight ({sl_pct:.4f}) — skip")
            return None
        if sl_pct > 0.05:
            logger.warning(f"{symbol}: SL too wide ({sl_pct:.4f}) — skip")
            return None

        notional    = risk_amount / sl_pct
        raw_qty     = notional / price

        # Round to exchange precision
        decimals    = CONFIG['QTY_DECIMALS'].get(symbol, 3)
        qty         = math.floor(raw_qty * 10**decimals) / 10**decimals

        # Check minimum qty
        min_qty     = CONFIG['MIN_QTY'].get(symbol, 0.001)
        if qty < min_qty:
            logger.warning(f"{symbol}: Qty {qty} below minimum {min_qty}")
            return None

        # Margin check: never use more than 25% balance on one trade
        margin_used = (qty * price) / CONFIG['LEVERAGE']
        if margin_used > balance * 0.25:
            qty = math.floor((balance * 0.25 * CONFIG['LEVERAGE'] / price)
                             * 10**decimals) / 10**decimals
            logger.info(f"{symbol}: Qty capped to {qty} (25% margin limit)")

        return {
            'qty':         qty,
            'notional':    qty * price,
            'risk_amount': risk_amount,
            'sl_distance': sl_distance,
            'sl_pct':      sl_pct,
            'margin_used': margin_used,
        }

    # ─── SL / TP PRICES ──────────────────────────────────
    def sl_tp(self, side: str, price: float, atr: float) -> tuple:
        """Returns (stop_loss_price, take_profit_price)."""
        sl_dist = atr * CONFIG['SL_ATR_MULT']
        tp_dist = atr * CONFIG['TP_ATR_MULT']   # 3:1 R:R

        if side == 'BUY':
            sl = round(price - sl_dist, 2)
            tp = round(price + tp_dist, 2)
        else:
            sl = round(price + sl_dist, 2)
            tp = round(price - tp_dist, 2)

        return sl, tp

    # ─── CAN TRADE? ──────────────────────────────────────
    def can_trade(self, symbol: str, balance: float) -> tuple[bool, str]:
        """
        Returns (True, '') or (False, reason).
        Checks all circuit breakers before allowing a trade.
        """
        today     = date.today().isoformat()
        month_key = datetime.now().strftime('%Y-%m')

        # 1. Max open positions
        if len(self.open_positions) >= CONFIG['MAX_OPEN_POSITIONS']:
            return False, f"Max {CONFIG['MAX_OPEN_POSITIONS']} open positions reached"

        # 2. Already in this symbol
        if symbol in self.open_positions:
            return False, f"Already in position on {symbol}"

        # 3. Daily loss limit
        daily_loss_pct = self.daily_pnl.get(today, 0) / balance * 100
        if daily_loss_pct <= -CONFIG['MAX_DAILY_LOSS_PCT']:
            return False, f"Daily loss limit hit ({daily_loss_pct:.1f}%) — no more trades today"

        # 4. Monthly loss limit
        monthly_loss_pct = self.monthly_pnl.get(month_key, 0) / balance * 100
        if monthly_loss_pct <= -CONFIG['MAX_MONTHLY_LOSS_PCT']:
            return False, f"⛔ MONTHLY LOSS LIMIT HIT ({monthly_loss_pct:.1f}%) — BOT PAUSED"

        # 5. Consecutive losses pause
        if self.consecutive_loss >= CONFIG['MAX_CONSECUTIVE_LOSS']:
            if self.last_loss_time:
                hours_since = (datetime.now() - self.last_loss_time).seconds / 3600
                if hours_since < 4:
                    return False, f"{self.consecutive_loss} losses in a row — cooling off ({4-hours_since:.1f}h left)"
                else:
                    self.consecutive_loss = 0  # reset after cool-off

        return True, ''

    # ─── RECORD TRADE RESULT ────────────────────────────
    def record_result(self, pnl: float):
        """Call this after every trade closes."""
        today     = date.today().isoformat()
        month_key = datetime.now().strftime('%Y-%m')

        self.daily_pnl[today]       = self.daily_pnl.get(today, 0) + pnl
        self.monthly_pnl[month_key] = self.monthly_pnl.get(month_key, 0) + pnl

        if pnl < 0:
            self.consecutive_loss += 1
            self.last_loss_time    = datetime.now()
        else:
            self.consecutive_loss  = 0

    # ─── OPEN / CLOSE POSITION TRACKING ─────────────────
    def open_position(self, symbol: str, side: str):
        self.open_positions[symbol] = side

    def close_position(self, symbol: str):
        self.open_positions.pop(symbol, None)

    # ─── DAILY STATS ────────────────────────────────────
    def daily_summary(self, balance: float) -> dict:
        today     = date.today().isoformat()
        month_key = datetime.now().strftime('%Y-%m')
        return {
            'daily_pnl':      self.daily_pnl.get(today, 0),
            'monthly_pnl':    self.monthly_pnl.get(month_key, 0),
            'daily_pnl_pct':  self.daily_pnl.get(today, 0) / balance * 100,
            'monthly_pnl_pct':self.monthly_pnl.get(month_key, 0) / balance * 100,
            'open_positions': len(self.open_positions),
            'consec_losses':  self.consecutive_loss,
        }
