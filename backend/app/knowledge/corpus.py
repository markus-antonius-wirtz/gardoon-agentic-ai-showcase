"""Curated TradingTackle.ai Enterprise Knowledge Base (48 domain documents).

Covers three specialized collections filtered via Qdrant payload metadata:
1. pine_v5_reference       — Exact Pine Script v5 compiler & syntax rules
2. anti_repainting_audit   — Lookahead bias, synthetic candle traps & friction standards
3. risk_compliance_policy  — EU ESMA/MiFID retail guardrails & TradingTackle HITL thresholds
"""

from app.schemas import KnowledgeDocument

TRADINGTACKLE_CORPUS: list[KnowledgeDocument] = [
    # ==========================================================================
    # 1. PINE SCRIPT V5 OFFICIAL REFERENCE & COMPILER RULES (16 DOCS)
    # ==========================================================================
    KnowledgeDocument(
        doc_id="TT-PINE-001",
        title="Mandatory //@version=5 Compiler Directive & strategy() Declaration",
        category="pine_v5_reference",
        severity="critical",
        tags=["version5", "strategy", "study", "compiler", "migration"],
        content=(
            "Rule TT-PINE-001: Every executable TradingTackle script MUST begin with `//@version=5` on line 1. "
            "Legacy v4 `study()` declarations are invalid in v5 and replaced by `indicator()` or `strategy()`. "
            "All quantitative backtest scripts MUST declare `strategy(title=..., overlay=..., initial_capital=10000, "
            "default_qty_type=strategy.percent_of_equity, default_qty_value=..., commission_type=strategy.commission.percent, "
            "commission_value=0.06, slippage=2)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-002",
        title="Namespace Migration: ta.* Technical Analysis Functions in Pine v5",
        category="pine_v5_reference",
        severity="critical",
        tags=["ta.ema", "ta.sma", "ta.rsi", "ta.atr", "ta.crossover", "namespace"],
        content=(
            "Rule TT-PINE-002: Bare v4 function calls such as `ema()`, `sma()`, `rsi()`, `atr()`, `crossover()`, "
            "and `crossunder()` fail compilation in Pine Script v5. They MUST use the `ta.` namespace: "
            "`ta.ema(source, length)`, `ta.sma(source, length)`, `ta.rsi(source, length)`, `ta.atr(length)`, "
            "`ta.crossover(seriesA, seriesB)`, and `ta.crossunder(seriesA, seriesB)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-003",
        title="Tuple Unpacking Syntax for ta.macd, ta.bb, and ta.supertrend",
        category="pine_v5_reference",
        severity="warning",
        tags=["ta.macd", "ta.bb", "ta.supertrend", "tuple", "syntax"],
        content=(
            "Rule TT-PINE-003: Multi-output indicators in Pine Script v5 return typed tuples and MUST be unpacked "
            "with bracket destructuring: `[macdLine, signalLine, histLine] = ta.macd(close, 12, 26, 9)`, "
            "`[middle, upper, lower] = ta.bb(close, 20, 2.0)`, and `[supertrendVal, direction] = ta.supertrend(3.0, 10)`. "
            "Note that in `ta.supertrend`, `direction < 0` indicates an uptrend while `direction > 0` indicates a downtrend."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-004",
        title="Typed Input Declarations: input.int, input.float, input.source",
        category="pine_v5_reference",
        severity="warning",
        tags=["input.int", "input.float", "input.bool", "parameters"],
        content=(
            "Rule TT-PINE-004: Generic `input(14, type=input.integer)` is deprecated in Pine Script v5. "
            "Use strongly typed constructors: `input.int(14, title='ATR Length', minval=1, maxval=200)`, "
            "`input.float(2.0, title='ATR Stop Multiplier', minval=0.5, maxval=10.0, step=0.1)`, "
            "`input.bool(true, title='Allow Short Entries')`, and `input.source(close, title='Source')`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-005",
        title="Proper Exit Architecture with strategy.exit() and Linked Entry IDs",
        category="pine_v5_reference",
        severity="critical",
        tags=["strategy.exit", "strategy.entry", "stop", "limit", "trail_points"],
        content=(
            "Rule TT-PINE-005: Every `strategy.entry('Long', strategy.long)` call MUST have a corresponding "
            "`strategy.exit('Exit Long', from_entry='Long', stop=longStopPrice, limit=longTakeProfit)` or trailing "
            "configuration (`trail_price` + `trail_offset`). Relying solely on `strategy.close()` on bar close leaves "
            "intrabar tail risk unprotected and fails TradingTackle production verification."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-006",
        title="math.* and str.* Standard Library Namespaces in Pine Script v5",
        category="pine_v5_reference",
        severity="info",
        tags=["math.max", "math.min", "math.abs", "str.tostring"],
        content=(
            "Rule TT-PINE-006: Mathematical helpers moved under `math.*` in v5: `math.abs()`, `math.max()`, "
            "`math.min()`, `math.round()`, `math.sqrt()`, `math.log()`. String formatting moved under `str.*`: "
            "`str.tostring(value, '#.##')` and `str.format('{0} | {1}', a, b)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-007",
        title="Persistent State Initialization: var vs varip Semantics",
        category="pine_v5_reference",
        severity="warning",
        tags=["var", "varip", "state", "trailing_stop"],
        content=(
            "Rule TT-PINE-007: Variables declared with `var float trailStop = na` initialize once on bar_index 0 "
            "and persist across confirmed bars, rolling back intrabar ticks safely. `varip` bypasses intrabar rollback "
            "and MUST NEVER be used inside backtested `strategy()` scripts because historical bars lack tick replay."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-008",
        title="Position State Introspection: strategy.position_size & strategy.position_avg_price",
        category="pine_v5_reference",
        severity="info",
        tags=["strategy.position_size", "position_avg_price", "entry_price"],
        content=(
            "Rule TT-PINE-008: Check open exposure via `strategy.position_size > 0` (long), `strategy.position_size < 0` "
            "(short), or `strategy.position_size == 0` (flat). Compute dynamic stop distances relative to "
            "`strategy.position_avg_price` when in a trade, falling back to `close` only on the entry signal bar."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-009",
        title="Color & Visual Plotting Standards: color.new() Replacing transp=",
        category="pine_v5_reference",
        severity="warning",
        tags=["plot", "color.new", "transp", "overlay"],
        content=(
            "Rule TT-PINE-009: The `transp=` argument in `plot()`, `bgcolor()`, and `fill()` was removed in Pine v5. "
            "Always specify opacity via `color.new(color.emerald, 80)` or `color.new(#3b82f6, 15)`. Plot active stop-loss "
            "levels with `plot(strategy.position_size > 0 ? longStop : na, style=plot.style_linebr, color=color.red)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-010",
        title="Conditional Evaluation Scope Traps for Stateful ta.* Functions",
        category="pine_v5_reference",
        severity="warning",
        tags=["scope", "ternary", "if_block", "ta.atr", "ta.highest"],
        content=(
            "Rule TT-PINE-010: Stateful series functions (`ta.atr`, `ta.rsi`, `ta.highest`, `ta.lowest`, `ta.vwap`) "
            "MUST be evaluated at global scope on every bar, then referenced inside `if` blocks. Calling `ta.atr(14)` "
            "only inside a conditional branch corrupts internal Wilder smoothing buffers."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-011",
        title="Multi-Timeframe Data Access: request.security() Signature in v5",
        category="pine_v5_reference",
        severity="critical",
        tags=["request.security", "mtf", "timeframe", "barmerge"],
        content=(
            "Rule TT-PINE-011: In Pine v5, `security()` moved to `request.security(symbol, timeframe, expression, "
            "gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_off)`. Never pass mutable local blocks directly; "
            "wrap multi-indicator expressions in a tuple `[htfEma, htfRsi]` to minimize `request.security` call count (max 40)."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-012",
        title="Volume Confirmation Guards Across Spot, CFD, and Index Feeds",
        category="pine_v5_reference",
        severity="info",
        tags=["volume", "na", "ta.sma", "forex", "crypto"],
        content=(
            "Rule TT-PINE-012: Some FX CFD tickers report `na(volume)` or zero volume. Any volume filter such as "
            "`volume > ta.sma(volume, 20) * 1.2` MUST include a safe fallback `(na(volume) or volume > volThreshold)` "
            "unless explicitly restricted to exchange-traded crypto or equities."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-013",
        title="Date-Window & Warmup Bar Guard (`bar_index >= warmupBars`)",
        category="pine_v5_reference",
        severity="info",
        tags=["bar_index", "warmup", "ema200", "na_protection"],
        content=(
            "Rule TT-PINE-013: Long-lookback filters (e.g., 200-bar EMA) produce `na` or unstable values on initial bars. "
            "Gate order submission behind `bar_index >= 200` and `not na(slowEma)` to prevent spurious early trades."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-014",
        title="Order Sizing Modes: strategy.percent_of_equity vs Risk-Based Contracts",
        category="pine_v5_reference",
        severity="warning",
        tags=["percent_of_equity", "position_sizing", "qty", "atr_risk"],
        content=(
            "Rule TT-PINE-014: TradingTackle strategies support either bounded `strategy.percent_of_equity` or "
            "volatility-adjusted sizing `qty = (strategy.equity * riskPct) / (atrVal * stopMult * syminfo.pointvalue)`. "
            "When computing `qty` dynamically, guard against division by zero with `math.max(stopDistance, syminfo.mintick)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-015",
        title="Built-in Portfolio Circuit Breakers: strategy.risk.max_drawdown()",
        category="pine_v5_reference",
        severity="warning",
        tags=["strategy.risk.max_drawdown", "circuit_breaker", "kill_switch"],
        content=(
            "Rule TT-PINE-015: Pine v5 provides native hard circuit breakers via "
            "`strategy.risk.max_drawdown(value=20, type=strategy.percent_of_equity)`. Including this directive "
            "automatically halts new entries and flattens exposure if cumulative drawdown hits the configured ceiling."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-PINE-016",
        title="Alert Webhook Payload Safety in strategy.entry(alert_message=...)",
        category="pine_v5_reference",
        severity="info",
        tags=["alert_message", "webhook", "json", "automation"],
        content=(
            "Rule TT-PINE-016: When emitting JSON execution webhooks for TradingTackle connectors, populate "
            "`alert_message` with escaped JSON fields (`ticker`, `action`, `price`) and never embed API secrets "
            "inside Pine Script source code."
        ),
    ),

    # ==========================================================================
    # 2. ANTI-REPAINTING & EMPIRICAL BACKTEST AUDIT STANDARDS (16 DOCS)
    # ==========================================================================
    KnowledgeDocument(
        doc_id="TT-REP-001",
        title="CRITICAL REPAINTING TRAP: request.security() with barmerge.lookahead_on",
        category="anti_repainting_audit",
        severity="critical",
        tags=["repainting", "lookahead_on", "request.security", "future_leak", "critical"],
        content=(
            "Audit Standard TT-REP-001 (CRITICAL BLOCK): Calling `request.security(syminfo.tickerid, 'D', close, "
            "lookahead=barmerge.lookahead_on)` on an intraday chart leaks the unclosed end-of-day future price into "
            "morning bars! This creates fake 85%-99% historical winrates that collapse in live trading. "
            "Approved non-repainting multi-timeframe idiom: ALWAYS shift the series by `[1]` BEFORE security evaluation: "
            "`request.security(syminfo.tickerid, 'D', close[1], gaps=barmerge.gaps_off, lookahead=barmerge.lookahead_on)` "
            "or use `lookahead=barmerge.lookahead_off` with `[1]` confirmation."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-002",
        title="Intrabar Execution Mirage: calc_on_every_tick=true Prohibited in Backtests",
        category="anti_repainting_audit",
        severity="critical",
        tags=["calc_on_every_tick", "calc_on_order_fills", "repainting", "ticks"],
        content=(
            "Audit Standard TT-REP-002: Setting `calc_on_every_tick=true` or `calc_on_order_fills=true` inside `strategy()` "
            "causes severe live-vs-historical divergence because TradingView historical bars only store OHLC (4 points), "
            "not real tick sequences. Both flags MUST remain `false` (default) for certified TradingTackle strategies."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-003",
        title="Mandatory Transaction Cost & Slippage Baseline (0.06% + 2 Ticks)",
        category="anti_repainting_audit",
        severity="critical",
        tags=["commission", "slippage", "friction", "backtest_realism"],
        content=(
            "Audit Standard TT-REP-003: Zero-commission, zero-slippage backtests are strictly rejected by TradingTackle. "
            "Every `strategy()` header MUST include at minimum `commission_type=strategy.commission.percent, "
            "commission_value=0.06` (6 bps per leg = 12 bps round-trip) and `slippage=2`. High-frequency scalping "
            "on < 5m timeframes requires `commission_value=0.08` and `slippage=3`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-004",
        title="Confirmed Bar Signal Rule (`barstate.isconfirmed`) for Live Parity",
        category="anti_repainting_audit",
        severity="warning",
        tags=["barstate.isconfirmed", "signal_stability", "repainting"],
        content=(
            "Audit Standard TT-REP-004: Indicator signals based on `close` flicker intrabar until candle close. "
            "Standard `strategy()` evaluates on bar close Fill-at-Next-Open automatically, which is clean; however, "
            "`process_orders_on_close=true` cheats by filling at the exact close price that triggered the signal and "
            "MUST NOT be enabled unless paired with `slippage >= 3`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-005",
        title="Synthetic Candle Execution Trap: Heikin-Ashi, Renko, Kagi, LineBreak",
        category="anti_repainting_audit",
        severity="critical",
        tags=["heikin_ashi", "renko", "ticker.heikinashi", "synthetic_price", "repainting"],
        content=(
            "Audit Standard TT-REP-005 (CRITICAL BLOCK): Executing orders on Heikin-Ashi or Renko charts fills trades "
            "at synthetic averaged prices (`(O+H+L+C)/4` or prior HA midpoint) that never existed in the order book! "
            "Even using `request.security(ticker.heikinashi(syminfo.tickerid), timeframe.period, close)` without `[1]` "
            "can distort intrabar timing. Orders MUST always execute on standard OHLC candles."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-006",
        title="Pivot & ZigZag Lookforward Bias (`ta.pivothigh` / `ta.pivotlow`)",
        category="anti_repainting_audit",
        severity="warning",
        tags=["pivothigh", "pivotlow", "zigzag", "rightbars", "lag"],
        content=(
            "Audit Standard TT-REP-006: `ta.pivothigh(leftbars, rightbars)` is only known `rightbars` candles AFTER "
            "the peak occurred. Plotting or backtesting entries at the historical pivot bar offset `-rightbars` is a "
            "classic lookahead error; entries may only trigger on the confirmation bar where `not na(ta.pivothigh(...))`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-007",
        title="Same-Bar Stop-Loss & Take-Profit Ambiguity on Wide Candles",
        category="anti_repainting_audit",
        severity="warning",
        tags=["ohlc_heuristic", "stop_loss", "take_profit", "intrabar_order"],
        content=(
            "Audit Standard TT-REP-007: When both `stop` and `limit` inside `strategy.exit()` lie within the same "
            "candle's `[low, high]` range, OHLC backtesters infer hit order from candle open proximity. Avoid ultra-tight "
            "targets (< 0.5 * ATR) where both stop and target routinely trigger inside a single bar."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-008",
        title="Statistical Significance & Degrees-of-Freedom Overfitting Guard",
        category="anti_repainting_audit",
        severity="warning",
        tags=["overfitting", "sample_size", "parameters", "curve_fitting"],
        content=(
            "Audit Standard TT-REP-008: Strategies with more than 5 tunable magic numbers (e.g., `rsiLen=13, buyLvl=27.4, "
            "emaLen=89, atrMult=1.73`) exhibit severe curve-fitting. Keep tunable core logic parameters <= 5 and target "
            "regimes generating >= 100 closed trades over a multi-regime 3-to-5-year window."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-009",
        title="Realistic Empirical Benchmark Ranges for Retail & Institutional Quant",
        category="anti_repainting_audit",
        severity="info",
        tags=["winrate", "profit_factor", "sharpe", "benchmarks", "empirical"],
        content=(
            "Audit Standard TT-REP-009: Empirically validated liquid-market strategies typically exhibit: "
            "Trend-Following Winrate `38% - 54%` with Profit Factor `1.35 - 1.95`; Mean-Reversion Winrate `55% - 68%` "
            "with Profit Factor `1.25 - 1.75` and higher tail-risk sensitivity. Any unverified backtest claiming "
            "Profit Factor > 3.0 or Winrate > 75% across >= 100 trades indicates repainting, zero-fee illusion, or tiny sample."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-010",
        title="Timeframe Liquidity Floor (>= 15m Recommended for Automated Execution)",
        category="anti_repainting_audit",
        severity="info",
        tags=["timeframe", "1m", "scalping", "latency", "liquidity"],
        content=(
            "Audit Standard TT-REP-010: Sub-5-minute webhook strategies suffer from 300ms-1500ms REST API latency and "
            "bid-ask spread widening during news spikes. TradingTackle recommends `15m`, `1H`, `4H`, or `1D` timeframes "
            "for retail API automation."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-011",
        title="Survivorship & Single-Ticker Regime Bias Disclosure",
        category="anti_repainting_audit",
        severity="info",
        tags=["survivorship_bias", "bull_market", "long_only", "short_leg"],
        content=(
            "Audit Standard TT-REP-011: Long-only momentum scripts tested solely on NVDA or BTC during bull runs "
            "confuse beta exposure with alpha. Strategies should support bidirectional logic or regime filters (e.g., "
            "200 EMA trend filter + ADX/ATR volatility filter) tested across bear and sideways markets."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-REP-012",
        title="Pyramiding & Compounding Distortion (`pyramiding=0` Default)",
        category="anti_repainting_audit",
        severity="warning",
        tags=["pyramiding", "compounding", "initial_capital"],
        content=(
            "Audit Standard TT-REP-012: Uncapped pyramiding (`pyramiding > 1`) multiplies correlated directional risk "
            "on consecutive signals. Unless explicitly designed as a scale-in trend model with tighter blended stops, "
            "declare `pyramiding=0` in `strategy()`."
        ),
    ),

    # ==========================================================================
    # 3. TRADINGTACKLE RISK & EU/MiFID COMPLIANCE POLICIES (16 DOCS)
    # ==========================================================================
    KnowledgeDocument(
        doc_id="TT-RISK-001",
        title="STRICT BAN on Misleading Return Promises & >75% Winrate Claims (YMYL / ESMA)",
        category="risk_compliance_policy",
        severity="critical",
        tags=["compliance", "mifid", "esma", "ymyl", "winrate_claim", "guaranteed_profit"],
        content=(
            "Compliance Policy TT-RISK-001 (MANDATORY ENFORCEMENT): Under EU ESMA retail communication standards and "
            "TradingTackle YMYL publishing rules, strategies and summaries MUST NEVER claim 'guaranteed returns', "
            "'risk-free arbitrage', or unverified '85%-99% winrates'. Any user prompt or script containing deceptive "
            "performance claims MUST have those claims stripped, flagged as CRITICAL finding `TT-RISK-001`, and "
            "replaced with realistic empirical intervals."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-002",
        title="MANDATORY HUMAN-IN-THE-LOOP GATE: Max Drawdown > 20.0% or Leverage > 3x",
        category="risk_compliance_policy",
        severity="critical",
        tags=["hitl", "human_in_the_loop", "max_drawdown", "leverage", "approval_gate", "20_percent"],
        content=(
            "Compliance Policy TT-RISK-002 (HUMAN GOVERNANCE INTERRUPT): Whenever a proposed or audited strategy exhibits "
            "an estimated Maximum Drawdown exceeding `20.0%`, OR uses position sizing > `25%` of equity per trade, OR "
            "requests leverage > `3x` (e.g., 5x, 10x, 20x perpetual futures), automated publication is FORBIDDEN. "
            "The LangGraph workflow MUST trigger a Human-in-the-Loop `interrupt()` pause so a human Risk Reviewer can "
            "either (a) Approve with an explicit High-Risk ESMA Disclaimer, (b) Auto-Tighten risk parameters (`<= 15%` "
            "equity sizing, `1x` spot/low leverage, hard `strategy.risk.max_drawdown(18)`), or (c) Reject publication."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-003",
        title="Prohibition of Uncapped Martingale, Grid Averaging-Down, and Naked Shorts",
        category="risk_compliance_policy",
        severity="critical",
        tags=["martingale", "grid_bot", "averaging_down", "stop_loss_mandatory", "ruin_risk"],
        content=(
            "Compliance Policy TT-RISK-003: Doubling position size after losses (Martingale) or adding to losing positions "
            "without a hard portfolio stop-loss creates asymmetric tail-ruin risk (`100%` account wipeout). Every "
            "TradingTackle strategy MUST define a deterministic hard stop-loss per position via `strategy.exit(..., stop=...)`."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-004",
        title="Default Retail Position Sizing Ceiling (`default_qty_value <= 20%` Equity)",
        category="risk_compliance_policy",
        severity="warning",
        tags=["default_qty_value", "position_sizing", "equity_risk", "capital_preservation"],
        content=(
            "Compliance Policy TT-RISK-004: Allocating `default_qty_value=100` (100% of account equity per trade) amplifies "
            "drawdowns during losing streaks. Standard compliant TradingTackle templates allocate `10` to `20` percent "
            "of equity per unleveraged trade (`default_qty_value=15` recommended) so per-trade risk stays near `1% - 2%` "
            "of total portfolio equity."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-005",
        title="Mandatory ESMA / MiFID II Past-Performance & Capital-at-Risk Disclosure",
        category="risk_compliance_policy",
        severity="info",
        tags=["disclaimer", "past_performance", "mifid_ii", "disclosure"],
        content=(
            "Compliance Policy TT-RISK-005: Every published report MUST remind users that simulated backtest metrics "
            "have inherent limitations, past performance does not guarantee future results, and leveraged derivatives "
            "carry high risk of rapid capital loss."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-006",
        title="Volatility Spike & News Gap Exposure Disclosure",
        category="risk_compliance_policy",
        severity="info",
        tags=["gap_risk", "cpi", "fomc", "stop_slippage", "volatility"],
        content=(
            "Compliance Policy TT-RISK-006: Hard stop orders convert to market orders when triggered and can fill "
            "significantly worse than the stop price during weekend opens, FOMC announcements, or crypto liquidation cascades. "
            "ATR-scaled stops (`2.0 * ta.atr(14)`) adapt better to volatility expansion than fixed-percentage stops."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-007",
        title="Perpetual Futures Funding Rate & Holding Cost Impact",
        category="risk_compliance_policy",
        severity="warning",
        tags=["funding_rate", "perpetual_futures", "crypto", "carry_cost"],
        content=(
            "Compliance Policy TT-RISK-007: Multi-day crypto perpetual futures strategies pay or receive funding every "
            "8 hours (often 10%-35% annualized during crowded bull regimes), which TradingView OHLC backtests do not "
            "deduct natively. Swing strategies on perpetuals must disclose funding drag."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-008",
        title="Emergency Portfolio Drawdown Kill-Switch (`strategy.risk.max_drawdown`)",
        category="risk_compliance_policy",
        severity="warning",
        tags=["kill_switch", "max_drawdown", "risk_governance", "automated_halt"],
        content=(
            "Compliance Policy TT-RISK-008: High-volatility breakout or momentum systems MUST embed an automated circuit "
            "breaker (`strategy.risk.max_drawdown(18, strategy.percent_of_equity)`) to cap catastrophic regime mismatch."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-009",
        title="Audit Trail & Deterministic Provenance Requirement for AI-Generated Code",
        category="risk_compliance_policy",
        severity="info",
        tags=["eu_ai_act", "audit_trail", "provenance", "citations"],
        content=(
            "Compliance Policy TT-RISK-009: Aligning with EU AI Act transparency best practices, every AI-synthesized or "
            "audited strategy in TradingTackle records its cited rule IDs (`TT-PINE-*`, `TT-REP-*`, `TT-RISK-*`), "
            "critic verification loop count, and human reviewer sign-off in an immutable checkpoint trail."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-010",
        title="Short-Selling Borrow Cost & Infinite Upside Exposure Guardrail",
        category="risk_compliance_policy",
        severity="warning",
        tags=["short_selling", "squeeze_risk", "stop_loss"],
        content=(
            "Compliance Policy TT-RISK-010: Unhedged short entries face theoretically unbounded loss during short squeezes. "
            "Any strategy enabling `strategy.short` MUST attach an immediate ATR or structure stop-loss on the entry bar."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-011",
        title="Illiquid Altcoin & Penny-Stock Manipulation Exclusion",
        category="risk_compliance_policy",
        severity="warning",
        tags=["liquidity", "slippage", "small_cap", "order_book"],
        content=(
            "Compliance Policy TT-RISK-011: Strategies calibrated for TradingTackle templates target high-liquidity "
            "instruments (BTCUSDT, ETHUSDT, EURUSD, SPY, QQQ, DAX) with > $50M daily volume to ensure realistic order fills."
        ),
    ),
    KnowledgeDocument(
        doc_id="TT-RISK-012",
        title="Segregation of Research Simulation vs Personalized Investment Advice",
        category="risk_compliance_policy",
        severity="info",
        tags=["mifid", "non_advisory", "educational_tool", "compliance"],
        content=(
            "Compliance Policy TT-RISK-012: TradingTackle provides algorithmic software engineering and empirical backtest "
            "auditing tools, NOT personalized investment advice or portfolio management under MiFID II Annex I."
        ),
    ),

    # ==========================================================================
    # 4. MULTI-TENANT ISOLATION DEMO CORPUS (`tenant="gardoon_cloud"`) (8 DOCS)
    # Proves Qdrant Multi-Tenant Payload Isolation in Technical Evaluations!
    # ==========================================================================
    KnowledgeDocument(
        doc_id="GD-OPS-001",
        title="Gardoon Cloud SLA: Kubernetes Pod Disruption Budget & HPA Thresholds",
        category="risk_compliance_policy",
        severity="critical",
        tenant="gardoon_cloud",
        tags=["kubernetes", "hpa", "pdb", "sla", "multi_tenant"],
        content=(
            "Gardoon Cloud Policy GD-OPS-001: Production AI workloads run with minReplicas=2, PodDisruptionBudget "
            "minAvailable=1, and HorizontalPodAutoscaler scaling at 70% CPU or 75% memory utilization."
        ),
    ),
    KnowledgeDocument(
        doc_id="GD-OPS-002",
        title="Gardoon Vector Multi-Tenancy Isolation Standard in Qdrant",
        category="risk_compliance_policy",
        severity="critical",
        tenant="gardoon_cloud",
        tags=["qdrant", "multi_tenancy", "payload_filter", "gdpr"],
        content=(
            "Gardoon Cloud Policy GD-OPS-002: All Qdrant queries enforce mandatory `FieldCondition(key='tenant', "
            "match=MatchValue(value=active_tenant))` payload filtering with indexed keyword shards to guarantee strict "
            "cryptographic and logical tenant isolation."
        ),
    ),
]
