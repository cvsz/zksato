from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)

TERMINAL_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline' https://s3.tradingview.com; "
    "connect-src 'self' https://api.binance.com https://api.kucoin.com "
    "wss://stream.binance.com:9443 wss://*.kucoin.com; "
    "img-src 'self' data: https:; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self'"
)

TERMINAL_ROUTES = {"/v1/market/terminal", "/v1/market/tradingview"}

router = APIRouter()


@router.get("/v1/market/terminal", response_class=HTMLResponse, include_in_schema=False)
async def market_terminal(request: Request) -> HTMLResponse:
    response = HTMLResponse(content=_TERMINAL_HTML, media_type="text/html")
    response.headers["Content-Security-Policy"] = TERMINAL_CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/v1/market/tradingview", response_class=HTMLResponse, include_in_schema=False)
async def tradingview_widget(request: Request) -> HTMLResponse:
    response = HTMLResponse(content=_TRADINGVIEW_HTML, media_type="text/html")
    response.headers["Content-Security-Policy"] = TERMINAL_CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/v1/market/health-bridge", include_in_schema=False)
async def health_bridge() -> JSONResponse:
    try:
        import zksato
        from zksato.api import _health_payload

        payload = await _health_payload()
        ver = getattr(zksato, "__version__", "1.0.0")
    except Exception:
        ver = "1.0.0"
        payload = {"status": "degraded", "version": ver}
    return JSONResponse({"status": payload.get("status", "degraded"), "version": ver})


@router.get("/v1/market/ccxt/status", include_in_schema=False)
async def ccxt_status() -> JSONResponse:
    try:
        from zksato.api import ccxt_feed

        if ccxt_feed is None:
            return JSONResponse({"running": False, "connected": False, "error": "not initialized"})
        return JSONResponse(ccxt_feed.status())
    except Exception as exc:
        return JSONResponse({"running": False, "connected": False, "error": str(exc)})


@router.get("/v1/market/prediction/status", include_in_schema=False)
async def prediction_status() -> JSONResponse:
    try:
        from zksato.api import prediction_feed

        if prediction_feed is None:
            return JSONResponse({"running": False, "connected": False, "error": "not initialized"})
        return JSONResponse(prediction_feed.status())
    except Exception as exc:
        return JSONResponse({"running": False, "connected": False, "error": str(exc)})


_TERMINAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>zksato Market Terminal</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #131722;
            font-family: system-ui, -apple-system, sans-serif;
            color: #d1d4dc;
        }
        header {
            padding: 12px 16px;
            background: #1e222d;
            border-bottom: 1px solid #2a2e39;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        h1 { font-size: 16px; margin: 0; font-weight: 600; }
        .badge {
            font-size: 11px;
            background: #2962ff;
            color: #fff;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .readonly { font-size: 11px; color: #787b86; }
        #tradingview_widget { height: calc(100vh - 48px); }
    </style>
</head>
<body>
    <header>
        <h1>zksato Market Terminal <span class="badge">READ-ONLY</span></h1>
        <span class="readonly">No order submission</span>
    </header>
    <div id="tradingview_widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
        new TradingView.widget({
            "width": "100%",
            "height": "100%",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "15",
            "timezone": "Asia/Bangkok",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#131722",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_widget"
        });
    </script>
</body>
</html>
"""

_TRADINGVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>zksato TradingView</title>
    <style>
        body { margin: 0; padding: 0; background: #131722; }
        #tradingview_widget { height: 100vh; }
    </style>
</head>
<body>
    <div id="tradingview_widget"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <script type="text/javascript">
        new TradingView.widget({
            "width": "100%",
            "height": "100%",
            "symbol": "BINANCE:BTCUSDT",
            "interval": "15",
            "timezone": "Asia/Bangkok",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#131722",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_widget"
        });
    </script>
</body>
</html>
"""
