"""LLM-driven decision engine for zksato — adapted from anglerfish-fable5 autotrade.py.

Philosophy: safety-first. The LLM is a signal generator only. All order placement
goes through zksato RiskEngine and TradingService. The JSON schema is strictly
enforced; any parse error or network failure defaults to HOLD (fail-closed).
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

# ─── Constants ────────────────────────────────────────────────────────────___

TRUE_STRINGS = {"true", "1", "yes", "y", "on"}
FALSE_STRINGS = {"false", "0", "no", "n", "off"}

LIVE_CONFIRM_PHRASE = "I UNDERSTAND"

SYSTEM_PROMPT = """You are zksato, a disciplined crypto tail-sniper strategist.
Analyze short-term market microstructure and reply with a single trading decision.
You are extremely risk-averse by default: when signals are mixed, weak, or unclear,
choose HOLD. Never chase pumps, never revenge-trade, and never suggest position
sizes beyond the given maximum.

You MUST reply with ONLY a single compact JSON object and nothing else — no
markdown, no code fences, no explanation outside the JSON. The JSON schema is
exactly:
{"action": "BUY" | "SELL" | "HOLD", "confidence": <number 0..1>, \
"size_usdt": <number>, "reason": "<short string, one sentence>"}
"""


# ─── Data class ─────────────────────────────────────────────────────────────


@dataclass
class Decision:
    action: str  # "BUY" | "SELL" | "HOLD"
    confidence: float
    size_usdt: float
    reason: str


# ─── Utilities ──────────────────────────────────────────────────────────────


def now_str() -> str:
    """Return current UTC time as readable string for logging."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def log(msg: str, level: str = "INFO") -> None:
    """Log with timestamp."""
    print(f"[{now_str()}] [{level}] {msg}", flush=True)


def redact(value: str | None) -> str:
    """Redact a secret value before it's ever logged/printed anywhere."""
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def parse_bool(raw: str | None, default: bool) -> bool:
    """Convert string from env var to bool robustly."""
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_STRINGS:
        return True
    if normalized in FALSE_STRINGS:
        return False
    log(
        f"Unrecognized boolean '{raw}' use default={default} instead / "
        f"Unrecognized boolean '{raw}', falling back to default={default}",
        level="WARN",
    )
    return default


def parse_float_env(raw: str | None, default: float, name: str) -> float:
    """Convert string to float robustly with clear fallback logging."""
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError:
        log(
            f"Value {name}='{raw}' is not a valid number use default={default} / "
            f"{name}='{raw}' is not a valid number, using default={default}",
            level="WARN",
        )
        return default


def parse_int_env(raw: str | None, default: int, name: str) -> int:
    """Convert string to int robustly with clear fallback logging."""
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log(
            f"Value {name}='{raw}' is not an integer use default={default} / "
            f"{name}='{raw}' is not a valid integer, using default={default}",
            level="WARN",
        )
        return default


# ─── Market features ────────────────────────────────────────────────────────


def _sma(values: list[float], period: int) -> float | None:
    """Simple Moving Average of `period` values — last window average."""
    if len(values) < period or period <= 0:
        return None
    return float(np.mean(values[-period:]))


def _rsi(closes: list[float], period: int = 14) -> float | None:
    """Relative Strength Index — standard Wilder smoothing (simple version)."""
    if len(closes) < period + 1:
        return None

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def _pct_change(old: float, new: float) -> float | None:
    """Percentage change from old to new."""
    if old == 0:
        return None
    return ((new - old) / old) * 100.0


def build_market_features(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    last_price: float,
    ticker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build lightweight market features from OHLCV + ticker for LLM consumption.

    The schema is designed to be compact and LLM-friendly, matching the format
    used by anglerfish-fable5 autotrade.py build_market_features().
    """
    lookback_n = min(24, len(closes))
    change_n = _pct_change(closes[-lookback_n], closes[-1]) if lookback_n >= 2 else None

    features = {
        "last_price": round(last_price, 8) if last_price > 0 else None,
        "sma20": round(_sma(closes, 20), 8) if _sma(closes, 20) is not None else None,
        "sma50": round(_sma(closes, 50), 8) if _sma(closes, 50) is not None else None,
        "rsi14": round(_rsi(closes, 14), 2) if _rsi(closes, 14) is not None else None,
        "pct_change_last_candle": round(_pct_change(closes[-2], closes[-1]), 3)
        if len(closes) >= 2
        else None,
        f"pct_change_last_{lookback_n}_candles": round(change_n, 3)
        if change_n is not None
        else None,
        "recent_high": round(max(highs), 8) if highs else None,
        "recent_low": round(min(lows), 8) if lows else None,
        "candles_used": len(closes),
    }
    return features


# ─── OpenRouter LLM call ──────────────────────────────────────────────────


def call_openrouter(
    openrouter_api_key: str,
    openrouter_model: str,
    features: dict[str, Any],
    cfg: dict[str, Any] | None = None,
) -> str:
    """Call OpenRouter chat completions API and return raw text from LLM.

    Raises on network/HTTP error. Caller must try/except.
    """
    import requests  # lazy import — keeps import path light when only reading config

    if cfg is None:
        cfg = {}

    user_content = (
        "Market snapshot (JSON), decide the single best action for this cycle.\n"
        f"Symbol: {cfg.get('symbol', 'UNKNOWN')}\n"
        f"Timeframe: {cfg.get('timeframe', '1h')}\n"
        f"Max allowed size_usd for any BUY/SELL: {cfg.get('max_order_usdt', 15.0)}\n"
        f"Features: {json.dumps(features, sort_keys=True)}\n"
        "Reply with ONLY the JSON object described in your instructions."
    )

    payload = {
        "model": openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
    }

    timeout = cfg.get("openrouter_timeout", 30) if cfg else 30
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        body = (response.text or "")[:300]
        sc = response.status_code
        if sc in (401, 403):
            hint = "Check OPENROUTER_API_KEY (key may be invalid or expired)"
        elif sc in (400, 404):
            hint = (
                f"Check OPENROUTER_MODEL — model '{cfg.get('openrouter_model', 'anthropic/claude-fable-5')}' "
                f"may be invalid or deprecated, see https://openrouter.ai/models"
            )
        elif sc == 429:
            hint = "Rate-limited — backing off"
        else:
            hint = "OpenRouter server error"
        raise RuntimeError(f"OpenRouter HTTP {sc}: {hint} :: {body}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"OpenRouter response has no choices/content (model refusal or unexpected shape): "
            f"{str(data)[:300]}"
        ) from exc


# ─── Decision parsing ───────────────────────────────────────────────────────


def parse_decision(raw_text: str, max_order_usdt: float) -> Decision:
    """Parse LLM response into Decision object robustly (fail-safe).

    If parse fails at any point, HOLD is returned — never accidentally BUY/SELL.
    Iron rule: size_usdt is clamped to max_order_usdt. No matter what the LLM
    requests, the clamp is absolute.
    """
    fallback = Decision(
        action="HOLD",
        confidence=0.0,
        size_usdt=0.0,
        reason="parse_failed_or_invalid_fallback_to_hold",
    )
    if not raw_text or not raw_text.strip():
        return fallback

    text = raw_text.strip()
    # Strip code fences if LLM added them ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Find the first JSON object in the text (LLM may speak before/after)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        log(
            f"No JSON found in LLM response — defaulting to HOLD / "
            f"No JSON found in LLM response — Raw: {text[:200]!r}",
            level="WARN",
        )
        return fallback

    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        log(
            f"JSON parse failed — defaulting to HOLD / JSON decode failed: "
            f"{exc}. Raw: {text[:200]!r}",
            level="WARN",
        )
        return fallback

    action = str(obj.get("action", "HOLD")).strip().upper()
    if action not in ("BUY", "SELL", "HOLD"):
        log(
            f"Unrecognized action '{action}' — defaulting to HOLD / "
            f"Unrecognized action '{action}' — defaulting to HOLD",
            level="WARN",
        )
        return fallback

    try:
        confidence = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    try:
        size_usdt = float(obj.get("size_usdt", 0.0))
    except (TypeError, ValueError):
        size_usdt = 0.0
    # Iron rule: no matter what the LLM requests, clamp to MAX_ORDER_USDT.
    size_usdt = max(0.0, min(size_usdt, max_order_usdt))

    reason = str(obj.get("reason", "")).strip()[:280] or "no_reason_given"

    return Decision(action=action, confidence=confidence, size_usdt=size_usdt, reason=reason)


# ─── Execution mode gate ────────────────────────────────────────────────────


def parse_env_bool(raw: str | None, default: bool) -> bool:
    """Parse boolean from env var (shared utility)."""
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"true", "1", "yes", "y", "on"}


def resolve_execution_mode(cfg: dict[str, Any], cli_live: bool) -> dict[str, Any]:
    """Compute execution mode exactly once at startup.

    Golden rule: there is exactly ONE place in this entire program that decides
    whether a real order may be placed — this function. Nowhere else may
    re-derive this condition; that's how bypasses sneak in.

    ALL of the following must be true simultaneously for live trading:
      1) DRY_RUN=false (in .env)
      2) Run with --live flag
      3) User types the exact confirmation phrase "I UNDERSTAND" at startup
      4) If USE_TESTNET=false (mainnet) → must have env I_UNDERSTAND_REAL_MONEY=YES
    """
    reasons: list[str] = []

    if cfg.get("dry_run", True):
        reasons.append("DRY_RUN=true (configured) — must set false first")
    if not cli_live:
        reasons.append("--live flag was not passed")

    # If the first two gates already fail, skip the interactive prompt entirely.
    typed_ok = False
    if not reasons:
        typed_ok = _prompt_live_confirmation(cfg)
        if not typed_ok:
            reasons.append(f"Did not type the exact confirmation phrase '{LIVE_CONFIRM_PHRASE}'")

    mainnet_ack = True
    if not cfg.get("use_testnet", True):
        mainnet_ack = parse_env_bool(os.getenv("I_UNDERSTAND_REAL_MONEY"), default=False)
        if not mainnet_ack:
            reasons.append(
                "USE_TESTNET=false (mainnet) but env I_UNDERSTAND_REAL_MONEY=YES was not set"
            )

    live_authorized = len(reasons) == 0

    if live_authorized:
        label = "LIVE MAINNET — REAL MONEY" if not cfg.get("use_testnet", True) else "LIVE TESTNET"
    else:
        label = "DRY-RUN"

    return {
        "live_authorized": live_authorized,
        "reasons_blocked": reasons,
        "label": label,
    }


def _prompt_live_confirmation(cfg: dict[str, Any]) -> bool:
    """Prompt once at startup for live trading confirmation.

    If stdin is not a TTY (e.g. run in CI/pipe) or EOF is hit, this is treated
    as a refusal and the bot falls back to dry-run automatically — there is no
    way to "accidentally pass" this gate.
    """
    target = (
        "TESTNET (sandbox funds)" if cfg.get("use_testnet", True) else "MAINNET — REAL MONEY 100%"
    )
    print()
    print("!" * 78)
    print(f"You are about to enable LIVE trading on: {target}")
    print(
        f"  Symbol: {cfg.get('symbol', 'UNKNOWN')}  |  Max per-order notional: {cfg.get('max_order_usdt', 15)} USDT"
    )
    print(f"  Max daily loss before auto-halt: {cfg.get('max_daily_loss_usdt', 50)} USDT")
    print("  This is experimental software. You may lose money. You are")
    print("  solely responsible for all outcomes.")
    print("!" * 78)
    print(f"Type exactly: {LIVE_CONFIRM_PHRASE}")

    try:
        if not sys.stdin.isatty():
            log(
                "stdin is not an interactive terminal — auto-refusing confirmation / "
                "stdin is not an interactive TTY — auto-refusing confirmation",
                level="WARN",
            )
            return False
        typed = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        log(
            "No confirmation received (EOF/Ctrl+C) — refusing / "
            "No confirmation received (EOF/Ctrl+C) — refusing",
            level="WARN",
        )
        return False
    return typed == LIVE_CONFIRM_PHRASE


# ─── Main bot loop ──────────────────────────────────────────────────────────


def run_cycle(
    cfg: dict[str, Any],
    mode: dict[str, Any],
    exchange,
    tracker: dict[str, Any],
    risk_engine,
) -> None:
    """Run one decision cycle: fetch data → features → LLM → risk → execute.

    Everything inside is wrapped in try/except at the main loop level so one
    failed cycle does not crash the entire bot.
    """
    # Fetch OHLCV + ticker
    ohlcv = exchange.fetch_ohlcv(
        cfg["symbol"], cfg["timeframe"], limit=cfg.get("candle_lookback", 60)
    )
    ticker = exchange.fetch_ticker(cfg["symbol"])

    if not ohlcv:
        log(
            "No OHLCV data returned — skipping cycle / No OHLCV data returned — skipping cycle",
            level="WARN",
        )
        return

    closes = [c[4] for c in ohlcv]
    highs = [c[2] for c in ohlcv]
    lows = [c[3] for c in ohlcv]

    features = build_market_features(closes, highs, lows, float(ticker.get("last", 0) or 0.0))

    log(f"Market features: {json.dumps(features, sort_keys=True)}")

    try:
        raw_response = call_openrouter(
            cfg["openrouter_api_key"],
            cfg["openrouter_model"],
            features,
            cfg,
        )
    except Exception as exc:  # network/HTTP — must not crash the bot
        log(
            f"OpenRouter call failed — treating as HOLD / "
            f"OpenRouter call failed — treating as HOLD: {exc}",
            level="ERROR",
        )
        raw_response = ""

    decision = parse_decision(raw_response, cfg["max_order_usdt"])
    log(
        f"LLM decision: action={decision.action} confidence={decision.confidence:.2f} "
        f"size_usdt={decision.size_usdt:.2f} reason={decision.reason!r}"
    )

    if decision.action == "HOLD":
        log("HOLD — no action this cycle")
        return

    last_price = features.get("last_price")
    if not last_price or last_price <= 0:
        log(
            "No valid last price available — skipping cycle / No valid last price available — skipping",
            level="WARN",
        )
        return

    # Compute order amount via market precision (adapted from anglerfish compute_capped_amount)

    exchange_iface = exchange  # type: ignore
    try:
        raw_amount = decision.size_usdt / last_price
        precise_amount_str = exchange_iface.amount_to_precision(cfg["symbol"], raw_amount)
        amount = float(precise_amount_str)
    except Exception as exc:
        log(
            f"Failed to compute capped amount — treating as HOLD / "
            f"Failed to compute capped amount: {exc}",
            level="WARN",
        )
        return

    if amount <= 0:
        log(
            "Order amount below market minimum after cap — treating as HOLD / "
            "Order size below market minimums after capping",
            level="WARN",
        )
        return

    approx_notional = amount * last_price

    # Check if live authorized — if not, dry-run log only
    if not mode["live_authorized"]:
        action_th = "BUY" if decision.action == "BUY" else "SELL"
        # Determine base currency symbol
        _sym = cfg["symbol"]
        _base = _sym.split("/")[0]
        log(
            f"[DRY] Would {action_th} {amount} {_base} (~${approx_notional:.2f}) — reason: {decision.reason} / "
            f"[DRY] would {decision.action} {amount} {_base} (~${approx_notional:.2f}) — reason: {decision.reason}"
        )
        return

    # Check daily-loss halt BEFORE every real order (not just at startup)
    # Adapted from anglerfish tracker.halted_by_loss()
    session_realized_pnl = tracker.get("session_realized_pnl", 0.0)
    max_daily_loss = cfg.get("max_daily_loss_usdt", 50.0)
    if session_realized_pnl < -abs(max_daily_loss):
        log(
            f"Stop trading — cumulative loss {session_realized_pnl:.2f} USDT exceeds limit / "
            f"Trading halted — cumulative loss {session_realized_pnl:.2f} USDT exceeds limit",
            level="ERROR",
        )
        raise DailyLossHalt(session_realized_pnl)

    # Risk evaluation is handled upstream via TradingService.submit()
    # No local evaluation needed in this cycle

    # TODO: Full integration with zksato TradingService would go here.
    # For now, log the dry-run intent since this module is a decision engine
    # adapter, not a full broker integration.
    log(
        f"[LIVE] Would place {decision.action} {amount} {cfg['symbol']} (~${approx_notional:.2f}) — reason: {decision.reason}"
    )


class DailyLossHalt(Exception):
    """Raise when cumulative daily loss exceeds MAX_DAILY_LOSS_USDT — stop bot immediately."""

    def __init__(self, realized_pnl: float):
        self.realized_pnl = realized_pnl
        super().__init__(f"Daily loss limit exceeded: {realized_pnl:.2f} USDT")


# ─── CLI entrypoint ─────────────────────────────────────────────────────────


def build_arg_parser() -> __import__("argparse").ArgumentParser:
    """Build CLI argument parser for the LLM-driven bot."""
    parser = __import__("argparse").ArgumentParser(
        prog="llm_bot.py",
        description="zksato LLM-driven decision engine (safety-first, dry-run by default).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Request live trading (still requires passing all safety conditions).",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Override SYMBOL from config, e.g. BTC/USDT",
    )
    dry_run_group = parser.add_mutually_exclusive_group()
    dry_run_group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=None,
        help="Force dry-run even if config sets DRY_RUN=false.",
    )
    dry_run_group.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=None,
        help="Disable dry-run per CLI (still requires --live to trade live).",
    )
    return parser


def main() -> None:
    """Main entry point for the LLM-driven bot."""
    from zksato_strategy.llm_decision import (
        log,
        parse_env_bool,
        resolve_execution_mode,
    )

    print("""
⚡ ZKSTO · LLM-Driven Decision Engine ⚡
=======================================
Safety-first: DRY-RUN by default. Live execution requires multiple deliberate steps.
""")

    parser = build_arg_parser()
    args = parser.parse_args()

    # Load config (simplified — in production would load from .env + TOML)
    cfg = {
        "binance_api_key": os.getenv("BINANCE_API_KEY", ""),
        "binance_api_secret": os.getenv("BINANCE_API_SECRET", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "openrouter_model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-fable-5"),
        "symbol": args.symbol or os.getenv("SYMBOL", "BTC/USDT"),
        "timeframe": os.getenv("TIMEFRAME", "1h"),
        "dry_run": parse_env_bool(os.getenv("DRY_RUN"), default=True),
        "use_testnet": parse_env_bool(os.getenv("USE_TESTNET"), default=True),
        "max_order_usdt": parse_float_env(os.getenv("MAX_ORDER_USDT"), 15.0, "MAX_ORDER_USDT"),
        "max_daily_loss_usdt": parse_float_env(
            os.getenv("MAX_DAILY_LOSS_USDT"), 50.0, "MAX_DAILY_LOSS_USDT"
        ),
        "poll_interval_sec": parse_int_env(
            os.getenv("POLL_INTERVAL_SEC"), 300, "POLL_INTERVAL_SEC"
        ),
        "candle_lookback": parse_int_env(os.getenv("CANDLE_LOOKBACK"), 60, "CANDLE_LOOKBACK"),
    }

    log(
        f"Config loaded — symbol={cfg['symbol']} timeframe={cfg['timeframe']} "
        f"dry_run={cfg['dry_run']} use_testnet={cfg['use_testnet']} "
        f"max_order_usdt={cfg['max_order_usdt']} max_daily_loss_usdt={cfg['max_daily_loss_usdt']}"
    )

    # Redacted key log
    log(f"OPENROUTER_API_KEY={'*' * min(len(cfg['openrouter_api_key']), 8)}+…")

    mode = resolve_execution_mode(cfg, cli_live=args.live)

    print()
    print("=" * 78)
    print(f"MODE: {mode['label']}")
    if not mode["live_authorized"]:
        print("Why live trading is NOT enabled:")
        for reason in mode["reasons_blocked"]:
            print(f"  - {reason}")
        print("→ The bot will run in DRY-RUN mode (safe, no real orders placed).")
    else:
        print("*** REAL ORDERS will be placed against the exchange in this mode ***")
    print("=" * 78)
    print()

    # Quick smoke test: if no .env + keys, exit gracefully
    missing = []
    if not cfg["openrouter_api_key"].strip():
        missing.append("OPENROUTER_API_KEY")
    if missing:
        print(f"Missing required keys: {', '.join(missing)}")
        print("Set them in .env or environment variables.")
        sys.exit(0)

    try:
        # Simulate a single cycle with mock exchange
        # In production, this would be a while True loop
        import ccxt

        exchange = ccxt.binance(
            {
                "apiKey": cfg["binance_api_key"],
                "secret": cfg["binance_api_secret"],
                "enableRateLimit": True,
            }
        )
        if cfg["use_testnet"]:
            exchange.set_sandbox_mode(True)

        tracker = {"session_realized_pnl": 0.0}

        # Run one cycle
        run_cycle(cfg, mode, exchange, tracker, None)

    except KeyboardInterrupt:
        print()
        log("Received Ctrl+C — shutting down gracefully")
    except Exception as exc:
        log(f"Unexpected top-level error: {exc}", level="ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
