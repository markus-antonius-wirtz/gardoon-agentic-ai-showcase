"""Deterministic static code & policy guardrails complementing LLM reasoning."""

from __future__ import annotations

import re

from app.schemas import AuditFinding

_LOOKAHEAD_LEAK_RE = re.compile(r"lookahead\s*=\s*barmerge\.lookahead_on", re.IGNORECASE)
_SAFE_OFFSET_RE = re.compile(r"\[\s*1\s*\]\s*,\s*(?:gaps[^)]*,)?\s*lookahead\s*=\s*barmerge\.lookahead_on")
_V4_STUDY_RE = re.compile(r"\bstudy\s*\(")
_BARE_SECURITY_RE = re.compile(r"(?<!request\.)\bsecurity\s*\(")
_UNREALISTIC_WINRATE_RE = re.compile(
    r"\b(?:8[0-9]|9[0-9]|100)\s*%\s*(?:guaranteed\s*)?(?:win\s*rate|winrate|accuracy|alpha)"
    r"|\bguaranteed\s+(?:profit|return|win|alpha)",
    re.IGNORECASE,
)
_HEIKIN_ASHI_RE = re.compile(r"heikin[-_\s]?ashi|ticker\.heikinashi|\brenko\b", re.IGNORECASE)
_LEVERAGE_RE = re.compile(r"\b([4-9]|[1-9][0-9]+)\s*x\b(?:\s*(?:leverage|perpetual|futures|margin))?", re.IGNORECASE)
_DRAWDOWN_HINT_RE = re.compile(r"drawdown[^0-9]{0,25}([2-9][0-9](?:\.[0-9]+)?)\s*%", re.IGNORECASE)


def scan_user_submission(prompt: str) -> tuple[list[AuditFinding], float, float]:
    """Scan user prompt/script for deterministic repainting, v4 syntax, and risk traps.

    Returns:
        (findings, detected_leverage_x, hinted_drawdown_pct)
    """
    findings: list[AuditFinding] = []
    leverage_x = 1.0
    hinted_dd = 0.0

    lev_match = _LEVERAGE_RE.search(prompt)
    if lev_match:
        leverage_x = float(lev_match.group(1))

    dd_match = _DRAWDOWN_HINT_RE.search(prompt)
    if dd_match:
        hinted_dd = float(dd_match.group(1))

    if _LOOKAHEAD_LEAK_RE.search(prompt) and not _SAFE_OFFSET_RE.search(prompt):
        findings.append(
            AuditFinding(
                rule_id="TT-REP-001",
                severity="critical",
                title="Future Price Leak (`barmerge.lookahead_on` without `[1]` offset)",
                explanation=(
                    "Submitted script accesses higher-timeframe unclosed bar data on intraday candles using "
                    "`lookahead=barmerge.lookahead_on` without shifting series `[1]`, fabricating illusory historical winrates."
                ),
                cited_doc_id="TT-REP-001",
                remediation=(
                    "Use `request.security(syminfo.tickerid, 'D', close[1], gaps=barmerge.gaps_off, "
                    "lookahead=barmerge.lookahead_on)` so only confirmed prior daily closes are referenced."
                ),
            )
        )

    if "//@version=4" in prompt or _V4_STUDY_RE.search(prompt) or _BARE_SECURITY_RE.search(prompt):
        findings.append(
            AuditFinding(
                rule_id="TT-PINE-001",
                severity="critical",
                title="Deprecated Pine Script v4 Syntax (`study` / bare `security` / unnamespaced TA)",
                explanation=(
                    "Legacy Pine v4 primitives (`//@version=4`, `study()`, `security()`, `ema()`) fail Pine v5 compilation "
                    "and lack structured `strategy()` execution parameters."
                ),
                cited_doc_id="TT-PINE-001",
                remediation="Migrate header to `//@version=5`, `strategy(...)`, `request.security()`, and `ta.*` namespaces.",
            )
        )

    if _HEIKIN_ASHI_RE.search(prompt):
        findings.append(
            AuditFinding(
                rule_id="TT-REP-005",
                severity="critical",
                title="Synthetic Candle Execution Trap (Heikin-Ashi / Renko Pricing)",
                explanation=(
                    "Backtesting order fills on Heikin-Ashi synthetic averaged prices executes trades at non-existent "
                    "order-book levels, severely inflating historical equity curves."
                ),
                cited_doc_id="TT-REP-005",
                remediation="Execute all entries and stops strictly on standard exchange OHLC candles.",
            )
        )

    if "zero commission" in prompt.lower() or "no stop-loss" in prompt.lower() or "100% equity" in prompt.lower():
        findings.append(
            AuditFinding(
                rule_id="TT-REP-003",
                severity="critical",
                title="Missing Transaction Friction, Uncapped 100% Sizing & Absent Hard Stop-Loss",
                explanation=(
                    "Zero-fee backtesting with 100% equity sizing and no hard `strategy.exit(stop=...)` violates "
                    "both TT-REP-003 (0.06% + 2 ticks baseline) and TT-RISK-003/004 capital-preservation rules."
                ),
                cited_doc_id="TT-REP-003",
                remediation=(
                    "Configure `commission_value=0.06, slippage=2, default_qty_value=15` and attach an ATR hard stop."
                ),
            )
        )

    if _UNREALISTIC_WINRATE_RE.search(prompt):
        findings.append(
            AuditFinding(
                rule_id="TT-RISK-001",
                severity="critical",
                title="Prohibited Deceptive Performance Claim (>75% / 'Guaranteed' Winrate)",
                explanation=(
                    "Marketing or publishing '96% guaranteed winrate' claims violates EU ESMA retail communication "
                    "standards and TradingTackle YMYL publishing policy TT-RISK-001."
                ),
                cited_doc_id="TT-RISK-001",
                remediation="Strip deceptive return claims and report realistic empirical post-friction intervals.",
            )
        )

    if leverage_x > 3.0 or hinted_dd > 20.0:
        findings.append(
            AuditFinding(
                rule_id="TT-RISK-002",
                severity="warning",
                title=f"High-Risk Exposure Threshold Triggered (Leverage {leverage_x:.0f}x / Est. DD > 20%)",
                explanation=(
                    "Policy TT-RISK-002 forbids unattended publication when leverage exceeds 3x or estimated maximum "
                    "drawdown exceeds 20.0% of portfolio equity."
                ),
                cited_doc_id="TT-RISK-002",
                remediation="Pause pipeline via LangGraph interrupt() for mandatory Human Risk Officer governance.",
            )
        )

    return findings, leverage_x, hinted_dd


def verify_generated_pine_v5(code: str, executive_summary: str) -> list[str]:
    """Deterministic Critic checklist run against the Architect's generated Pine v5 output."""
    defects: list[str] = []

    if "//@version=5" not in code:
        defects.append("Generated script is missing mandatory `//@version=5` compiler directive (TT-PINE-001).")

    if "strategy(" not in code:
        defects.append("Generated script must declare `strategy(...)` with friction parameters (TT-PINE-001).")

    if "commission_value" not in code or "slippage" not in code:
        defects.append(
            "Generated `strategy()` header omits mandatory `commission_value` and `slippage` settings (TT-REP-003)."
        )

    if "strategy.exit(" not in code:
        defects.append("Generated script omits hard stop protection via `strategy.exit(...)` (TT-PINE-005 / TT-RISK-003).")

    if _LOOKAHEAD_LEAK_RE.search(code) and not _SAFE_OFFSET_RE.search(code):
        defects.append(
            "Generated code still contains unsafe `barmerge.lookahead_on` without `[1]` series offset (TT-REP-001)."
        )

    if _V4_STUDY_RE.search(code) or _BARE_SECURITY_RE.search(code):
        defects.append("Generated code contains legacy v4 `study()` or bare `security()` call (TT-PINE-001/011).")

    if _UNREALISTIC_WINRATE_RE.search(executive_summary):
        defects.append("Executive summary repeats prohibited guaranteed/>80% winrate promise (TT-RISK-001).")

    return defects
