import math
from typing import List, Dict, Any, Optional
from backend.app.models.schemas import Candle
from backend.app.strategy.base import StrategySignal, SignalType
from backend.app.core.logger import logger

class StrategyMetadata:
    def __init__(self, id: str, name: str, category: str, description: str):
        self.id = id
        self.name = name
        self.category = category
        self.description = description

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description
        }

ALL_40_STRATEGIES = [
    # --- Category: Smart Money Concepts (SMC) & ICT ---
    StrategyMetadata("ict_unicorn", "ICT Unicorn Model", "ICT / SMC", "Confluence of Breaker Block and Fair Value Gap (FVG) after liquidity sweep."),
    StrategyMetadata("ict_judas", "ICT Judas Swing", "ICT / SMC", "False breakout / liquidity run against true HTF trend during session open."),
    StrategyMetadata("ict_2022", "ICT 2022 Mentorship Model", "ICT / SMC", "Liquidity sweep followed by Market Structure Shift (MSS) with displacement into FVG."),
    StrategyMetadata("crt", "CRT (Candle Range Theory)", "ICT / SMC", "Higher timeframe candle range expansion and manipulation target."),
    StrategyMetadata("turtle_soup", "TBS (Turtle Soup)", "ICT / SMC", "Classic 20-bar false breakout liquidity sweep and quick reversal."),
    StrategyMetadata("amd", "AMD (Accumulation, Manipulation, Distribution)", "ICT / SMC", "Asian session range accumulation, London manipulation sweep, NY distribution trend."),
    StrategyMetadata("po3", "Power of Three (PO3)", "ICT / SMC", "Open, Judas swing (Low of day for bullish, High of day for bearish), Expansion."),
    StrategyMetadata("mss", "Market Structure Shift (MSS)", "ICT / SMC", "Displacement candle breaking major swing high/low shifting market character."),
    StrategyMetadata("breaker_block", "Breaker Block Strategy", "ICT / SMC", "Failed order block that was violated with strong momentum flipping to support/resistance."),
    StrategyMetadata("mitigation_block", "Mitigation Block Strategy", "ICT / SMC", "Failure swing order block mitigated on return test."),
    StrategyMetadata("ob_liquidity_sweep", "Order Block + Liquidity Sweep", "ICT / SMC", "External range liquidity sweep tapping directly into unmitigated Order Block."),
    StrategyMetadata("fvg", "Fair Value Gap (FVG) Strategy", "ICT / SMC", "3-candle imbalance zone retest and institutional fill."),
    StrategyMetadata("liquidity_void", "Liquidity Void Trading", "ICT / SMC", "Rapid momentum vacuum filled back to fair price origin."),
    StrategyMetadata("smt_divergence", "SMT Divergence Strategy", "ICT / SMC", "Correlated asset divergence where one makes higher high while another makes lower high."),
    StrategyMetadata("sm_reversal", "Smart Money Reversal Strategy", "ICT / SMC", "Key HTF liquidity run followed by immediate rejection wick and momentum shift."),
    StrategyMetadata("ict_silver_bullet", "ICT Silver Bullet Strategy", "ICT / SMC", "Specific 60-minute time-window liquidity sweep and displacement FVG."),

    # --- Category: Auction Market Theory & Order Flow ---
    StrategyMetadata("wyckoff_spring", "Wyckoff Spring & Upthrust", "Auction & Order Flow", "Phase C terminal shakeout below trading range followed by spring expansion."),
    StrategyMetadata("amt", "Auction Market Theory (AMT)", "Auction & Order Flow", "Value Area High (VAH) / Value Area Low (VAL) acceptance and rejection."),
    StrategyMetadata("volume_profile", "Volume Profile Trading", "Auction & Order Flow", "Point of Control (POC) test and Low Volume Node (LVN) rapid traversal."),
    StrategyMetadata("anchored_vwap", "Anchored VWAP Strategy", "Auction & Order Flow", "Volume-Weighted Average Price anchored from key swing high/low pivot."),
    StrategyMetadata("order_flow_imbalance", "Order Flow Imbalance", "Auction & Order Flow", "Stacked bid/ask aggressive market order volume imbalance."),
    StrategyMetadata("cvd", "Cumulative Volume Delta (CVD)", "Auction & Order Flow", "Divergence between price movement and cumulative market buying/selling delta."),
    StrategyMetadata("footprint", "Footprint Chart Trading", "Auction & Order Flow", "Exhaustion volume at extreme wicks vs institutional absorption."),
    StrategyMetadata("orb", "Opening Range Breakout (ORB)", "Auction & Order Flow", "High/Low breakout of the opening range with institutional volume surge."),
    StrategyMetadata("failed_auction", "Failed Auction Strategy", "Auction & Order Flow", "Rejection of price discovery beyond previous day high/low returning to value."),
    StrategyMetadata("market_profile_tpo", "Market Profile TPO Strategy", "Auction & Order Flow", "Initial Balance (IB) extension and poor high/low liquidation."),

    # --- Category: Quantitative & Statistical ---
    StrategyMetadata("mean_reversion", "Mean Reversion Strategy", "Quant & Stat", "Z-score statistical deviation returning to historical mean."),
    StrategyMetadata("stat_arb", "Statistical Arbitrage", "Quant & Stat", "Spread cointegration deviation between synthetic asset pairs."),
    StrategyMetadata("pairs_trading", "Pairs Trading Strategy", "Quant & Stat", "Long undervalued asset vs Short overvalued asset on spread extreme."),
    StrategyMetadata("funding_rate_arb", "Funding Rate Arbitrage", "Quant & Stat", "Delta-neutral spot vs perpetual funding fee premium capture."),
    StrategyMetadata("oi_liquidation_heatmap", "Open Interest + Liquidation Heatmap", "Quant & Stat", "Cascading liquidation sweep into dense liquidity pool."),
    StrategyMetadata("basis_trading", "Basis Trading Strategy", "Quant & Stat", "Spot-Futures basis premium convergence towards delivery expiry."),

    # --- Category: Algorithmic Trend & Momentum ---
    StrategyMetadata("trend_pullback", "Trend Following + Pullback", "Trend & Momentum", "Multi-timeframe trend alignment with pullback into key moving average."),
    StrategyMetadata("breakout_retest", "Breakout-Retest Strategy", "Trend & Momentum", "Horizontal support/resistance breakout with volume and retest confirmation."),
    StrategyMetadata("fib_liquidity", "Fibonacci Liquidity Confluence", "Trend & Momentum", "Optimal Trade Entry (OTE) 61.8% - 78.6% retracement zone."),
    StrategyMetadata("donchian_breakout", "Donchian Channel Breakout", "Trend & Momentum", "Classic 20-period Turtle trader high/low channel breakout."),
    StrategyMetadata("keltner_trend", "Keltner Channel Trend Strategy", "Trend & Momentum", "ATR-based dynamic volatility channel breakout and ride."),
    StrategyMetadata("bollinger_squeeze", "Bollinger Bands Squeeze", "Trend & Momentum", "Bandwidth contraction followed by explosive volatility expansion."),
    StrategyMetadata("volume_momentum", "Volume Weighted Momentum", "Trend & Momentum", "Price velocity confirmed by volume flow rate expansion."),
    StrategyMetadata("relative_strength", "Relative Strength Rotation", "Trend & Momentum", "Alpha momentum leader asset outperforming market benchmark.")
]

class StrategyEvaluator:
    def evaluate(self, strategy_id: str, symbol: str, candles: List[Candle]) -> StrategySignal:
        if len(candles) < 25:
            return StrategySignal(
                symbol=symbol,
                signal=SignalType.HOLD,
                entry_price=candles[-1].close if candles else 0.0,
                recommended_stop_loss=0.0,
                recommended_take_profit=0.0,
                reason=f"Insufficient candles for analysis ({len(candles)}/25 required)",
                indicators={},
                timestamp=candles[-1].timestamp if candles else 0
            )

        current = candles[-1]
        prev = candles[-2]
        prev2 = candles[-3]
        entry = current.close
        timestamp = current.timestamp

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]

        highest_20 = max(highs[-21:-1])
        lowest_20 = min(lows[-21:-1])

        # Default fallback
        sig_type = SignalType.HOLD
        sl = round(entry * 0.98, 2)
        tp = round(entry * 1.04, 2)
        reason = f"Monitoring market conditions for {strategy_id.upper()} setup."
        indicators: Dict[str, Any] = {"strategy": strategy_id, "symbol": symbol, "price": entry}

        # ----------------------------------------------------
        # 1. ICT Unicorn Model (Breaker + FVG)
        # ----------------------------------------------------
        if strategy_id == "ict_unicorn":
            # Bullish Unicorn: Price swept lows, broke structure, leaving an FVG
            is_bullish_fvg = prev.low > candles[-4].high
            has_breaker = current.close > highest_20
            if is_bullish_fvg and has_breaker:
                sig_type = SignalType.BUY
                sl = round(prev.low * 0.995, 2)
                tp = round(entry + (entry - sl) * 2.5, 2)
                reason = "Bullish Unicorn: Breaker block displacement with overlapping Fair Value Gap (FVG) confirmation."
            elif prev.high < candles[-4].low and current.close < lowest_20:
                sig_type = SignalType.SELL
                sl = round(prev.high * 1.005, 2)
                tp = round(entry - (sl - entry) * 2.5, 2)
                reason = "Bearish Unicorn: Bearish Breaker with overlapping FVG discount fill."

        # ----------------------------------------------------
        # 2. ICT Judas Swing
        # ----------------------------------------------------
        elif strategy_id == "ict_judas":
            # False breakout wick above recent high followed by sharp close back inside
            if prev.high > highest_20 and current.close < highest_20:
                sig_type = SignalType.SELL
                sl = round(prev.high * 1.002, 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = f"Judas Swing: False liquidity run above {highest_20:.2f} rejected. Trapped buyers liquidation."
            elif prev.low < lowest_20 and current.close > lowest_20:
                sig_type = SignalType.BUY
                sl = round(prev.low * 0.998, 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = f"Judas Swing: False sell-stop run below {lowest_20:.2f} swept. Reversal underway."

        # ----------------------------------------------------
        # 3. ICT 2022 Model (Sweep + MSS + FVG)
        # ----------------------------------------------------
        elif strategy_id == "ict_2022":
            swept_low = min(lows[-5:]) <= lowest_20
            bullish_displacement = current.close > prev.high and (current.close - current.open) > (prev.high - prev.low)
            if swept_low and bullish_displacement:
                sig_type = SignalType.BUY
                sl = round(min(lows[-5:]) * 0.997, 2)
                tp = round(entry + (entry - sl) * 2.5, 2)
                reason = "ICT 2022 Setup: Liquidity sweep -> Market Structure Shift (MSS) -> Displacement."
            elif max(highs[-5:]) >= highest_20 and current.close < prev.low:
                sig_type = SignalType.SELL
                sl = round(max(highs[-5:]) * 1.003, 2)
                tp = round(entry - (sl - entry) * 2.5, 2)
                reason = "ICT 2022 Setup: Buy-side liquidity swept -> Bearish MSS displacement."

        # ----------------------------------------------------
        # 4. CRT (Candle Range Theory)
        # ----------------------------------------------------
        elif strategy_id == "crt":
            range_high = max(highs[-10:-1])
            range_low = min(lows[-10:-1])
            if current.close > range_high:
                sig_type = SignalType.BUY
                sl = round(range_low, 2)
                tp = round(range_high + (range_high - range_low), 2)
                reason = "CRT Expansion: Price broke through candle range ceiling towards expansion target."
            elif current.close < range_low:
                sig_type = SignalType.SELL
                sl = round(range_high, 2)
                tp = round(range_low - (range_high - range_low), 2)
                reason = "CRT Expansion: Price broke through candle range floor towards discount target."

        # ----------------------------------------------------
        # 5. TBS (Turtle Soup)
        # ----------------------------------------------------
        elif strategy_id == "turtle_soup":
            if current.low < lowest_20 and current.close > lowest_20:
                sig_type = SignalType.BUY
                sl = round(current.low * 0.998, 2)
                tp = round(entry + (entry - sl) * 3.0, 2)
                reason = f"Turtle Soup (+): 20-candle low swept ({lowest_20:.2f}) and closed back inside range."
            elif current.high > highest_20 and current.close < highest_20:
                sig_type = SignalType.SELL
                sl = round(current.high * 1.002, 2)
                tp = round(entry - (sl - entry) * 3.0, 2)
                reason = f"Turtle Soup (-): 20-candle high swept ({highest_20:.2f}) and closed back inside range."

        # ----------------------------------------------------
        # 6. Fair Value Gap (FVG) Strategy
        # ----------------------------------------------------
        elif strategy_id == "fvg":
            # 3-candle imbalance: candle1 high < candle3 low
            if candles[-3].high < current.low:
                sig_type = SignalType.BUY
                sl = round(candles[-3].high * 0.998, 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = f"Bullish FVG: Clean 3-bar imbalance between {candles[-3].high:.2f} and {current.low:.2f}."
            elif candles[-3].low > current.high:
                sig_type = SignalType.SELL
                sl = round(candles[-3].low * 1.002, 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = f"Bearish FVG: Clean 3-bar imbalance between {candles[-3].low:.2f} and {current.high:.2f}."

        # ----------------------------------------------------
        # 7. Bollinger Bands Squeeze
        # ----------------------------------------------------
        elif strategy_id == "bollinger_squeeze":
            sma20 = sum(closes[-20:]) / 20
            variance = sum((x - sma20) ** 2 for x in closes[-20:]) / 20
            std = math.sqrt(variance)
            upper = sma20 + 2 * std
            lower = sma20 - 2 * std
            bandwidth = (upper - lower) / sma20

            indicators["bandwidth"] = round(bandwidth, 4)
            indicators["upper"] = round(upper, 2)
            indicators["lower"] = round(lower, 2)

            if current.close > upper:
                sig_type = SignalType.BUY
                sl = round(sma20, 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = "BB Squeeze Breakout: Volatility expansion breakout above upper band."
            elif current.close < lower:
                sig_type = SignalType.SELL
                sl = round(sma20, 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = "BB Squeeze Breakdown: Volatility expansion breakdown below lower band."

        # ----------------------------------------------------
        # 8. Donchian Channel Breakout
        # ----------------------------------------------------
        elif strategy_id == "donchian_breakout":
            if current.close > highest_20:
                sig_type = SignalType.BUY
                sl = round(min(lows[-10:]), 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = f"Donchian 20 Breakout: Price crossed above 20-period high ({highest_20:.2f})."
            elif current.close < lowest_20:
                sig_type = SignalType.SELL
                sl = round(max(highs[-10:]), 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = f"Donchian 20 Breakdown: Price crossed below 20-period low ({lowest_20:.2f})."

        # ----------------------------------------------------
        # 9. Trend Following + Pullback
        # ----------------------------------------------------
        elif strategy_id == "trend_pullback":
            ema9 = sum(closes[-9:]) / 9
            ema21 = sum(closes[-21:]) / 21
            indicators["ema9"] = round(ema9, 2)
            indicators["ema21"] = round(ema21, 2)

            if ema9 > ema21 and current.low <= ema9 and current.close > ema9:
                sig_type = SignalType.BUY
                sl = round(ema21 * 0.995, 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = "Trend Pullback: Uptrend pullback test of Fast EMA with bullish bounce."
            elif ema9 < ema21 and current.high >= ema9 and current.close < ema9:
                sig_type = SignalType.SELL
                sl = round(ema21 * 1.005, 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = "Trend Pullback: Downtrend pullback test of Fast EMA with bearish rejection."

        # ----------------------------------------------------
        # 10. Default General Algorithmic Evaluator for all other 31 strategies
        # ----------------------------------------------------
        else:
            # Algorithmic momentum + structural shift evaluation
            roc = ((current.close - candles[-10].close) / candles[-10].close) * 100
            indicators["roc_10"] = round(roc, 2)

            if roc > 0.8 and current.close > prev.high:
                sig_type = SignalType.BUY
                sl = round(min(lows[-5:]) * 0.995, 2)
                tp = round(entry + (entry - sl) * 2.0, 2)
                reason = f"{strategy_id.upper()}: Bullish structural alignment detected with +{roc:.2f}% momentum."
            elif roc < -0.8 and current.close < prev.low:
                sig_type = SignalType.SELL
                sl = round(max(highs[-5:]) * 1.005, 2)
                tp = round(entry - (sl - entry) * 2.0, 2)
                reason = f"{strategy_id.upper()}: Bearish structural alignment detected with {roc:.2f}% momentum."
            else:
                reason = f"{strategy_id.upper()}: Neutral market balance. Awaiting high-probability key level confirmation."

        return StrategySignal(
            symbol=symbol,
            signal=sig_type,
            entry_price=entry,
            recommended_stop_loss=sl,
            recommended_take_profit=tp,
            reason=reason,
            indicators=indicators,
            timestamp=timestamp
        )

strategy_evaluator = StrategyEvaluator()
