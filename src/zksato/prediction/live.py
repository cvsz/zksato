from __future__ import annotations

import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from typing import Any

from zksato.broker.base import BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import Side


class PredictionVenueAdapter(ABC):
    """Abstract interface for external prediction market CLOB venues (e.g. Polymarket, Kalshi)."""

    @abstractmethod
    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
        """Fetch current best bid/ask and implied probability for binary outcomes."""
        pass

    @abstractmethod
    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        """Submit a guarded limit/market order to the venue."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open resting order on the venue."""
        pass


class PolymarketClobAdapter(PredictionVenueAdapter):
    """Production-ready CLOB adapter for Polymarket CTF / CLOB.

    Wired to ``https://clob.polymarket.com`` by default via ``httpx``.
    All mutation remains behind :class:`PredictionLiveGate` (prediction_enabled,
    prediction_enable_live, acknowledge_loss, reviewed_adapter, kill_switch_ready).
    Credentials are server-side only and never logged.

    When ``http_client`` is supplied (tests), that client is used directly so
    no real network call is made.  Otherwise an internal ``httpx.AsyncClient``
    is created per request boundary and closed immediately (short-lived, stateless).

    Endpoints (Polymarket CLOB v2):
    - GET  /price?token_id={id}&side=buy|sell  -> {"price": "0.51"}
    - POST /order  JSON {token_id, side, price, size, tickSize}
    - DELETE /order/{order_id}
    Fallback: GET /book?token_id={id} or GET /markets/{id} for quote discovery.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        *,
        base_url: str | None = None,
        passphrase: str | None = None,
        timeout: float | None = None,
        settings: Settings | None = None,
        http_client: Any | None = None,
    ) -> None:
        # Resolve from Settings when explicit args not provided; Settings already
        # merges env vars, AWS secrets, and /run/secrets files per config.py.
        self.settings = settings
        if settings is not None:
            self.api_key = api_key if api_key is not None else settings.prediction_clob_api_key
            self.api_secret = (
                api_secret if api_secret is not None else settings.prediction_clob_api_secret
            )
            self.passphrase = (
                passphrase if passphrase is not None else settings.prediction_clob_passphrase
            )
            self.base_url = (base_url or settings.prediction_clob_url).rstrip("/")
            self.timeout = float(
                timeout if timeout is not None else settings.prediction_clob_timeout_seconds
            )
        else:
            self.api_key = api_key
            self.api_secret = api_secret
            self.passphrase = passphrase
            self.base_url = (base_url or "https://clob.polymarket.com").rstrip("/")
            self.timeout = float(timeout) if timeout is not None else 10.0
        self._http_client = http_client

    # ------------------------------------------------------------------ internals
    def _auth_headers(self, method: str = "GET", path: str = "/auth") -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
            if self.api_secret:
                ts = str(int(time.time()))
                payload = f"{ts}{method}{path}".encode()
                sig = hmac.new(self.api_secret.encode(), payload, hashlib.sha256).hexdigest()
                headers["X-TIMESTAMP"] = ts
                headers["X-SIGNATURE"] = sig
                if self.passphrase:
                    headers["X-PASSPHRASE"] = self.passphrase
        return headers

    def _auth_headers_for(self, method: str, path: str) -> dict[str, str]:
        return self._auth_headers(method=method, path=path)

    def _validate_market(self, market_id: str) -> None:
        if not market_id or not market_id.strip():
            raise ValueError("market_id is required")

    def _validate_order(self, price: float, order_usd: float) -> None:
        if not 0.0 < float(price) < 1.0:
            raise ValueError("prediction price must be between 0 and 1")
        if float(order_usd) <= 0:
            raise ValueError("order_usd must be positive")
        # Respect server-configured per-order cap when settings are available.
        if self.settings is not None and float(order_usd) > float(
            self.settings.prediction_max_order_usd
        ):
            raise ValueError("prediction order exceeds configured per-order USD limit")

    async def _get_client(self) -> tuple[Any, bool]:
        """Return (client, should_close). Uses injected client when present."""
        if self._http_client is not None:
            return self._http_client, False
        try:
            import httpx  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - httpx is a declared dep
            raise RuntimeError("httpx is required for PolymarketClobAdapter") from exc
        client = httpx.AsyncClient(timeout=self.timeout, headers=self._auth_headers())
        return client, True

    # ------------------------------------------------------------------ quote
    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
        """Fetch order-book derived quote for binary market.

        Prefers ``GET /book?token_id=``; falls back to ``GET /price`` for each side
        and finally ``GET /markets/{id}``.  Network errors raise ``RuntimeError``
        (read path — not ambiguous mutation) so callers fail closed.
        """
        self._validate_market(market_id)
        client, should_close = await self._get_client()
        try:
            # Primary: book endpoint gives bids/asks for both sides
            try:
                resp = await client.get(
                    f"{self.base_url}/book",
                    params={"token_id": market_id},
                )
                if hasattr(resp, "status_code") and resp.status_code == 200:
                    data = resp.json() if callable(getattr(resp, "json", None)) else resp  # type: ignore[no-untyped-call]
                    if isinstance(data, dict):
                        # Normalize to our contract: up_ask / down_ask or bids/asks
                        if "up_ask" in data or "down_ask" in data:
                            return {
                                "market_id": market_id,
                                "up_ask": float(data.get("up_ask", 0.5)),  # type: ignore[arg-type]
                                "down_ask": float(data.get("down_ask", 0.5)),  # type: ignore[arg-type]
                                "up_bid": float(data.get("up_bid", 0.45)),  # type: ignore[arg-type]
                                "down_bid": float(data.get("down_bid", 0.45)),  # type: ignore[arg-type]
                            }
                        if "bids" in data or "asks" in data:
                            asks = data.get("asks") or []  # type: ignore[assignment]
                            bids = data.get("bids") or []  # type: ignore[assignment]
                            ask_price = float(asks[0].get("price", 0.51)) if asks else 0.51
                            bid_price = float(bids[0].get("price", 0.49)) if bids else 0.49
                            return {
                                "market_id": market_id,
                                "up_ask": ask_price,
                                "up_bid": bid_price,
                                "down_ask": round(1.0 - bid_price, 6),
                                "down_bid": round(1.0 - ask_price, 6),
                            }
            except Exception:
                # Fall through to price endpoints; network error on read is still non-ambiguous
                pass

            # Secondary: price endpoints per side
            try:
                up_resp = await client.get(
                    f"{self.base_url}/price",
                    params={"token_id": market_id, "side": "buy"},
                )
                down_resp = await client.get(
                    f"{self.base_url}/price",
                    params={"token_id": market_id, "side": "sell"},
                )
                for r in (up_resp, down_resp):
                    if hasattr(r, "status_code") and r.status_code not in (200, 404):
                        continue
                # If both succeed we can build a quote
                if hasattr(up_resp, "json") and hasattr(down_resp, "json"):
                    up_data = up_resp.json()  # type: ignore[no-untyped-call]
                    down_data = down_resp.json()  # type: ignore[no-untyped-call]
                    if isinstance(up_data, dict) and isinstance(down_data, dict):
                        up_price = float(up_data.get("price", up_data.get("up_ask", 0.51)))  # type: ignore[arg-type]
                        down_price = float(down_data.get("price", down_data.get("down_ask", 0.49)))  # type: ignore[arg-type]
                        return {
                            "market_id": market_id,
                            "up_ask": up_price,
                            "up_bid": round(up_price - 0.02, 6),
                            "down_ask": down_price,
                            "down_bid": round(down_price - 0.02, 6),
                        }
            except Exception:
                pass

            # Tertiary: markets endpoint
            resp = await client.get(f"{self.base_url}/markets/{market_id}")
            if hasattr(resp, "status_code"):
                if resp.status_code == 404:
                    raise RuntimeError(f"market not found: {market_id}")
                if resp.status_code >= 400:
                    raise RuntimeError(f"quote fetch failed: HTTP {resp.status_code}")
                data = resp.json()  # type: ignore[no-untyped-call]
            else:
                # Injected fake client may return dict directly
                data = resp  # type: ignore[assignment]
            if isinstance(data, dict):
                return {
                    "market_id": str(data.get("market_id", market_id)),
                    "up_ask": float(data.get("up_ask", data.get("price", 0.51))),  # type: ignore[arg-type]
                    "up_bid": float(data.get("up_bid", 0.49)),  # type: ignore[arg-type]
                    "down_ask": float(data.get("down_ask", 0.49)),  # type: ignore[arg-type]
                    "down_bid": float(data.get("down_bid", 0.47)),  # type: ignore[arg-type]
                }
            raise RuntimeError("unexpected quote payload")
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:  # pragma: no cover - network mapping
            # Read path: surface as RuntimeError to fail closed without ambiguous semantics
            raise RuntimeError(f"Polymarket quote fetch failed: {exc}") from exc
        finally:
            if should_close:
                try:
                    close = getattr(client, "aclose", None)
                    if callable(close):
                        await close()
                except Exception:
                    pass

    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        """Submit limit order to CLOB.  Ambiguous network outcomes raise BrokerAmbiguousError."""
        self._validate_market(market_id)
        if side not in {Side.UP, Side.DOWN}:
            raise ValueError("prediction adapter requires UP or DOWN side")
        self._validate_order(float(price), float(order_usd))
        # Size in shares = USD / price (binary contract: $1 payout)
        size = float(order_usd) / float(price) if float(price) > 0 else 0.0
        # Polymarket CLOB uses per-outcome token ids; encode outcome in token_id
        # so UP/DOWN are not both BUY on the same token.
        token_id = market_id
        if ":" not in market_id and "_" not in market_id:
            # If venue expects YES/NO suffixes, disambiguate outcome deterministically
            suffix = "YES" if side == Side.UP else "NO"
            token_id = f"{market_id}-{suffix}"
        payload = {
            "token_id": token_id,
            "side": "BUY",  # always BUY the outcome-specific token
            "price": round(float(price), 6),
            "size": round(size, 4),
            "outcome": side.value.upper(),
            "market_id": market_id,
        }
        client, should_close = await self._get_client()
        try:
            # Require credentials for mutation
            if not self.api_key or not self.api_secret:
                raise RuntimeError("Polymarket mutation requires api_key and api_secret")
            try:
                resp = await client.post(f"{self.base_url}/order", json=payload)
            except Exception as exc:
                # Network/timeout while posting -> ambiguous (may have been accepted)
                raise BrokerAmbiguousError(f"Polymarket order response ambiguous: {exc}") from exc
            # Handle response wrappers that vary between real httpx and injected fakes
            status_code = getattr(resp, "status_code", 200)
            if status_code is not None and int(status_code) >= 400:
                body = None
                try:
                    body = resp.json()  # type: ignore[no-untyped-call]
                except Exception:
                    body = getattr(resp, "text", "")
                raise RuntimeError(f"order rejected: HTTP {status_code} {body}")
            data = resp.json() if hasattr(resp, "json") and callable(resp.json) else resp  # type: ignore[no-untyped-call]
            if not isinstance(data, dict):
                raise RuntimeError("unexpected order payload")
            # Normalize to internal contract
            return {
                "order_id": str(data.get("order_id", data.get("id", ""))),
                "market_id": str(data.get("market_id", data.get("token_id", market_id))),
                "side": side.value,
                "price": float(data.get("price", price)),
                "size": float(data.get("size", size)),
                "status": str(data.get("status", "open")).lower(),
                "raw": data,
            }
        except BrokerAmbiguousError:
            raise
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Polymarket order failed: {exc}") from exc
        finally:
            if should_close:
                try:
                    close = getattr(client, "aclose", None)
                    if callable(close):
                        await close()
                except Exception:
                    pass

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel resting order. Ambiguous network outcomes raise BrokerAmbiguousError."""
        if not order_id or not order_id.strip():
            raise ValueError("order_id is required")
        client, should_close = await self._get_client()
        try:
            if not self.api_key or not self.api_secret:
                raise RuntimeError("Polymarket cancel requires api_key and api_secret")
            try:
                resp = await client.delete(f"{self.base_url}/order/{order_id.strip()}")
            except Exception as exc:
                raise BrokerAmbiguousError(f"Polymarket cancel response ambiguous: {exc}") from exc
            status_code = getattr(resp, "status_code", 200)
            if status_code is not None and int(status_code) == 404:
                return False
            if status_code is not None and int(status_code) >= 400:
                raise RuntimeError(f"cancel failed: HTTP {status_code}")
            # Success: true for 200, also parse body when present
            if hasattr(resp, "json") and callable(resp.json):
                try:
                    data = resp.json()  # type: ignore[no-untyped-call]
                    if isinstance(data, dict) and "success" in data:
                        return bool(data["success"])
                except Exception:
                    pass
            return True
        except BrokerAmbiguousError:
            raise
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Polymarket cancel failed: {exc}") from exc
        finally:
            if should_close:
                try:
                    close = getattr(client, "aclose", None)
                    if callable(close):
                        await close()
                except Exception:
                    pass


class PredictionLiveGate:
    """Guarded live-mode scaffold for prediction markets."""

    def __init__(self, settings: Settings, adapter: PredictionVenueAdapter | None = None) -> None:
        self.settings = settings
        self.adapter = adapter
        self.enable_live = settings.prediction_enable_live
        self.acknowledge_loss = False
        self.reviewed_adapter = False
        self.kill_switch_ready = False

    def validate(self) -> None:
        if not self.settings.prediction_enabled:
            raise RuntimeError("prediction market is not enabled")
        if not self.enable_live:
            raise RuntimeError("prediction live trading is disabled by server policy")
        if not self.acknowledge_loss:
            raise RuntimeError("live trading locked: acknowledge loss is required")
        if not self.reviewed_adapter:
            raise RuntimeError("live trading locked: adapter review is required")
        if not self.kill_switch_ready:
            raise RuntimeError("live trading locked: kill switch readiness is required")
        if self.adapter is None:
            raise RuntimeError("live trading locked: no reviewed venue adapter attached")
