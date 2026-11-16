"""Curated 1-click showcase scenarios demonstrating every LangGraph & Vector DB capability."""

from app.schemas import ScenarioPreset

SHOWCASE_SCENARIOS: list[ScenarioPreset] = [
    ScenarioPreset(
        id="volatility-atr-breakout",
        badge="Scenario 01 · Clean Build + Self-Check",
        title="Adaptive Volatility Breakout (EMA 200 + ATR Trailing Stop)",
        subtitle="Synthesizes production Pine Script v5 with hybrid documentation grounding and passes Critic verification.",
        highlight_feature="Parallel Hybrid RAG + Pine v5 Synthesis",
        prompt=(
            "Design a production-ready Pine Script v5 trend-following breakout strategy for BTCUSDT and EURUSD on the "
            "1H timeframe. Use a 200-EMA regime filter, Donchian/20-bar high breakout entries with volume confirmation, "
            "and a dynamic 2.2x ATR(14) stop-loss and trailing exit via strategy.exit(). Ensure realistic friction "
            "(commission & slippage) and compliant position sizing."
        ),
    ),
    ScenarioPreset(
        id="repainting-trap-audit",
        badge="Scenario 02 · Repainting & YMYL Trap",
        title="Audit Submitted '96% Winrate' Multi-Timeframe Script",
        subtitle="Exposes hidden future-leak (`lookahead_on`) and zero-fee illusions that naive single-LLM chats miss, then auto-remediates.",
        highlight_feature="Corrective Self-Reflection Loop (Critic -> Architect)",
        prompt=(
            "Audit and remediate our draft strategy that achieved a 96% guaranteed winrate on 15m charts:\n"
            "//@version=4\n"
            "study('Guaranteed 96% Alpha Sniper', overlay=true)\n"
            "dailyClose = security(syminfo.tickerid, 'D', close, lookahead=barmerge.lookahead_on)\n"
            "fast = ema(close, 9)\n"
            "if close > dailyClose and fast > fast[1]\n"
            "    // Enter 100% equity with zero commission on Heikin-Ashi candles, no stop-loss needed!"
        ),
    ),
    ScenarioPreset(
        id="high-drawdown-hitl",
        badge="Scenario 03 · Human-in-the-Loop Gate",
        title="Aggressive 5x Leveraged Momentum Swing (Drawdown > 20%)",
        subtitle="Triggers Policy TT-RISK-002 (>20% Max Drawdown / >3x Leverage) and pauses LangGraph via interrupt() for human governance.",
        highlight_feature="Stateful LangGraph interrupt() & Checkpoint Resume",
        prompt=(
            "Build an aggressive high-beta crypto momentum strategy for SOLUSDT 4H using 5x perpetual futures leverage "
            "and 45% equity allocation per trade, riding MACD + Supertrend breakouts with wide 4.5x ATR stops "
            "(expected max drawdown around 28% - 32% during choppy regimes)."
        ),
    ),
]
