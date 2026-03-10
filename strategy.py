"""
Strategy Engine — Supertrend + EMA200 + RSI + VWAP
────────────────────────────────────────────────────

WHY THIS COMBINATION WORKS:

  Supertrend   → Best crypto trend indicator. ATR-based so it
                 adapts to volatility. Flips direction cleanly.
                 Less lag than EMA crossovers.

  EMA 200      → The most-watched MA by institutional traders.
                 Price above EMA200 = bull market. Below = bear.
                 Acts as the master trend filter.

  RSI 14       → Momentum filter. We only buy when RSI shows
                 healthy momentum (45-70), not when overbought.
                 Prevents chasing tops/bottoms.

  VWAP (20)    → Volume-weighted price. Institutions use this
                 as fair value reference. Buy below VWAP in
                 uptrend = buying at discount.

ENTRY RULES (ALL 4 must be true):
  BUY:  Supertrend flips BULLISH + Price > EMA200
        + Price > VWAP + RSI between 45-70

  SELL: Supertrend flips BEARISH + Price < EMA200
        + Price < VWAP + RSI between 30-55

EXIT RULES:
  1. Take Profit hit (ATR × 4.5 from entry)
  2. Stop Loss hit   (ATR × 1.5 from entry)
  3. Supertrend flips opposite direction (trail exit)
"""

import numpy as np
import pandas as pd
from config import CONFIG


class Strategy:

    # ─── SUPERTREND ──────────────────────────────────────
    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> pd.DataFrame:
        """
        Supertrend indicator.
        Returns dataframe with columns: ST, ST_DIR (1=bull, -1=bear)
        """
        hl2 = (df['high'] + df['low']) / 2

        # ATR (Wilder's smoothing)
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low']  - df['close'].shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(com=period - 1, adjust=False).mean()

        # Basic bands
        upper_basic = hl2 + mult * atr
        lower_basic = hl2 - mult * atr

        # Final bands (never move against trend)
        upper = upper_basic.copy()
        lower = lower_basic.copy()
        direction = pd.Series(1, index=df.index)
        st = pd.Series(index=df.index, dtype=float)

        for i in range(1, len(df)):
            # Upper band
            if upper_basic.iloc[i] < upper.iloc[i-1] or df['close'].iloc[i-1] > upper.iloc[i-1]:
                upper.iloc[i] = upper_basic.iloc[i]
            else:
                upper.iloc[i] = upper.iloc[i-1]

            # Lower band
            if lower_basic.iloc[i] > lower.iloc[i-1] or df['close'].iloc[i-1] < lower.iloc[i-1]:
                lower.iloc[i] = lower_basic.iloc[i]
            else:
                lower.iloc[i] = lower.iloc[i-1]

            # Direction
            prev_dir = direction.iloc[i-1]
            if prev_dir == 1:
                direction.iloc[i] = -1 if df['close'].iloc[i] < lower.iloc[i] else 1
            else:
                direction.iloc[i] = 1 if df['close'].iloc[i] > upper.iloc[i] else -1

            st.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

        df = df.copy()
        df['ST']     = st
        df['ST_DIR'] = direction
        df['ST_UP']  = lower    # bull line (support)
        df['ST_DN']  = upper    # bear line (resistance)
        df['ATR']    = atr
        return df

    # ─── RSI ─────────────────────────────────────────────
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain  = delta.clip(lower=0).ewm(com=period-1, adjust=False).mean()
        loss  = (-delta).clip(lower=0).ewm(com=period-1, adjust=False).mean()
        return 100 - 100 / (1 + gain / loss.replace(0, 1e-10))

    # ─── VWAP ────────────────────────────────────────────
    @staticmethod
    def vwap(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Rolling VWAP over N periods."""
        typical = (df['high'] + df['low'] + df['close']) / 3
        tp_vol  = typical * df['volume']
        return tp_vol.rolling(period).sum() / df['volume'].rolling(period).sum()

    # ─── ATR ─────────────────────────────────────────────
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low']  - df['close'].shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(com=period-1, adjust=False).mean()

    # ─── MAIN SIGNAL ─────────────────────────────────────
    def get_signal(self, df_15m: pd.DataFrame,
                   df_1h: pd.DataFrame = None) -> dict:
        """
        Returns signal dict:
          action: 'BUY' | 'SELL' | 'HOLD'
          confidence: 0-100
          reason: string
          atr: float (for SL/TP calculation)
          st_line: float (Supertrend line for trailing SL)
        """
        if len(df_15m) < 220:
            return self._hold('Not enough data')

        # ── Compute indicators on 15m ──
        df = self.supertrend(df_15m,
                             CONFIG['ST_PERIOD'],
                             CONFIG['ST_MULT'])
        df['RSI']  = self.rsi(df['close'], CONFIG['RSI_PERIOD'])
        df['VWAP'] = self.vwap(df, CONFIG['VWAP_PERIOD'])
        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

        # ── Latest values ──
        cur  = df.iloc[-1]
        prev = df.iloc[-2]

        price    = cur['close']
        st_dir   = cur['ST_DIR']
        prev_dir = prev['ST_DIR']
        st_line  = cur['ST']
        rsi_val  = cur['RSI']
        vwap_val = cur['VWAP']
        ema200   = cur['EMA200']
        atr_val  = cur['ATR']

        # ── Supertrend flip detection ──
        flip_bull = st_dir == 1  and prev_dir == -1
        flip_bear = st_dir == -1 and prev_dir == 1

        # ── 1H trend confirmation ──
        htf_bull = htf_bear = False
        if df_1h is not None and len(df_1h) >= 50:
            df1h = self.supertrend(df_1h, CONFIG['ST_PERIOD'], CONFIG['ST_MULT'])
            htf_bull = df1h['ST_DIR'].iloc[-1] == 1
            htf_bear = df1h['ST_DIR'].iloc[-1] == -1
        else:
            # Use EMA200 as fallback
            htf_bull = price > ema200
            htf_bear = price < ema200

        # ── BUY SIGNAL ──
        if flip_bull:
            reasons = []
            score   = 0

            if htf_bull:
                score += 40; reasons.append('HTF trend UP')
            else:
                return self._hold('ST flipped bull but HTF is bearish — skip')

            if price > vwap_val:
                score += 25; reasons.append('Price > VWAP')
            else:
                score += 5   # weaker signal

            if CONFIG['RSI_MIN_BUY'] <= rsi_val <= CONFIG['RSI_MAX_BUY']:
                score += 25; reasons.append(f'RSI healthy ({rsi_val:.0f})')
            elif rsi_val > CONFIG['RSI_MAX_BUY']:
                return self._hold(f'RSI overbought ({rsi_val:.0f}) — skip buy')
            else:
                score += 10

            if score >= 65:
                return {
                    'action':     'BUY',
                    'confidence': min(score, 95),
                    'reason':     ' + '.join(reasons),
                    'atr':        atr_val,
                    'st_line':    st_line,
                }

        # ── SELL SIGNAL ──
        if flip_bear:
            reasons = []
            score   = 0

            if htf_bear:
                score += 40; reasons.append('HTF trend DOWN')
            else:
                return self._hold('ST flipped bear but HTF is bullish — skip')

            if price < vwap_val:
                score += 25; reasons.append('Price < VWAP')
            else:
                score += 5

            if CONFIG['RSI_MIN_SELL'] <= rsi_val <= CONFIG['RSI_MAX_SELL']:
                score += 25; reasons.append(f'RSI healthy ({rsi_val:.0f})')
            elif rsi_val < CONFIG['RSI_MIN_SELL']:
                return self._hold(f'RSI oversold ({rsi_val:.0f}) — skip sell')
            else:
                score += 10

            if score >= 65:
                return {
                    'action':     'SELL',
                    'confidence': min(score, 95),
                    'reason':     ' + '.join(reasons),
                    'atr':        atr_val,
                    'st_line':    st_line,
                }

        return self._hold('No Supertrend flip this candle')

    @staticmethod
    def _hold(reason: str) -> dict:
        return {'action': 'HOLD', 'confidence': 0,
                'reason': reason, 'atr': 0, 'st_line': 0}
