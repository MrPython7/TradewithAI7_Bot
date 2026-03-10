"""
Telegram Notifier
──────────────────
Sends alerts for: trade entry, exit, daily summary,
errors, circuit breakers, and hourly status.
"""

import requests
import logging
from datetime import datetime
from config import CONFIG

logger = logging.getLogger(__name__)


class Telegram:

    BASE = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self):
        self.token   = CONFIG['TELEGRAM_TOKEN']
        self.chat_id = CONFIG['TELEGRAM_CHAT_ID']
        self.enabled = (self.token != "YOUR_TELEGRAM_BOT_TOKEN")

    def _send(self, text: str):
        if not self.enabled:
            logger.info(f"[TELEGRAM DISABLED] {text}")
            return
        try:
            url = self.BASE.format(token=self.token, method='sendMessage')
            requests.post(url, json={
                'chat_id':    self.chat_id,
                'text':       text,
                'parse_mode': 'HTML',
            }, timeout=10)
        except Exception as e:
            logger.error(f"Telegram error: {e}")

    # ── TRADE ENTRY ──────────────────────────────────────
    def trade_opened(self, symbol, side, price, qty, sl, tp,
                     reason, confidence, balance):
        emoji = "🟢" if side == "BUY" else "🔴"
        rr = abs(tp - price) / abs(sl - price)
        risk_amt = balance * CONFIG['RISK_PER_TRADE_PCT'] / 100
        self._send(
            f"{emoji} <b>TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Pair:       <b>{symbol}</b>\n"
            f"Direction:  <b>{side}</b>\n"
            f"Entry:      <b>${price:,.2f}</b>\n"
            f"Qty:        {qty}\n"
            f"Stop Loss:  ${sl:,.2f}\n"
            f"Take Profit:${tp:,.2f}\n"
            f"R:R Ratio:  {rr:.1f}:1\n"
            f"Risk:       ₹{risk_amt:.0f}\n"
            f"Signal:     {reason} ({confidence}%)\n"
            f"Balance:    ₹{balance:,.0f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%d %b %H:%M IST')}"
        )

    # ── TRADE EXIT ───────────────────────────────────────
    def trade_closed(self, symbol, side, entry, exit_price,
                     pnl, pnl_pct, exit_type, balance):
        if pnl >= 0:
            emoji = "✅"
            result = "WIN"
        else:
            emoji = "❌"
            result = "LOSS"

        self._send(
            f"{emoji} <b>TRADE CLOSED — {result}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Pair:       <b>{symbol}</b>\n"
            f"Direction:  {side}\n"
            f"Entry:      ${entry:,.2f}\n"
            f"Exit:       ${exit_price:,.2f}\n"
            f"P&L:        <b>{'+'if pnl>=0 else ''}₹{pnl:,.0f} ({pnl_pct:+.2f}%)</b>\n"
            f"Exit type:  {exit_type}\n"
            f"Balance:    ₹{balance:,.0f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%d %b %H:%M IST')}"
        )

    # ── DAILY SUMMARY ────────────────────────────────────
    def daily_summary(self, stats: dict, balance: float):
        dpnl = stats['daily_pnl']
        mpnl = stats['monthly_pnl']
        emoji = "📈" if dpnl >= 0 else "📉"
        self._send(
            f"{emoji} <b>DAILY SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Today P&L:    <b>{'+'if dpnl>=0 else ''}₹{dpnl:,.0f} ({stats['daily_pnl_pct']:+.2f}%)</b>\n"
            f"Monthly P&L:  {'+'if mpnl>=0 else ''}₹{mpnl:,.0f} ({stats['monthly_pnl_pct']:+.2f}%)\n"
            f"Balance:      ₹{balance:,.0f}\n"
            f"Open pos:     {stats['open_positions']}\n"
            f"Consec loss:  {stats['consec_losses']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%d %b %H:%M IST')}"
        )

    # ── CIRCUIT BREAKER ──────────────────────────────────
    def circuit_breaker(self, reason: str, balance: float):
        self._send(
            f"⛔ <b>CIRCUIT BREAKER TRIGGERED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Reason:   {reason}\n"
            f"Balance:  ₹{balance:,.0f}\n"
            f"Action:   Bot paused\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Review before restarting!"
        )

    # ── BOT STATUS ───────────────────────────────────────
    def bot_started(self, balance: float, testnet: bool):
        mode = "🧪 TESTNET" if testnet else "💰 LIVE"
        self._send(
            f"🚀 <b>BOT STARTED — {mode}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Balance:  ₹{balance:,.0f}\n"
            f"Strategy: Supertrend + EMA200 + RSI + VWAP\n"
            f"Risk:     {CONFIG['RISK_PER_TRADE_PCT']}%/trade\n"
            f"Leverage: {CONFIG['LEVERAGE']}x\n"
            f"Pairs:    {', '.join(CONFIG['PAIRS'])}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%d %b %H:%M IST')}"
        )

    def error(self, msg: str):
        self._send(f"🔴 <b>BOT ERROR</b>\n{msg}")
