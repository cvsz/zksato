from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    if old not in text:
        raise SystemExit(f"{path}: expected patch target not found: {old!r}")
    file.write_text(text.replace(old, new, 1))


replace_once(
    "src/zksato/tradingview.py",
    "    def parse(self, payload: dict) -> Signal | None:\n",
    "    def parse(self, payload: object) -> Signal | None:\n",
)

Path("src/zksato/secrets.py").write_text('''import json\nimport logging\nimport os\nfrom importlib import import_module\nfrom typing import Any\n\nfrom pydantic.fields import FieldInfo\nfrom pydantic_settings import BaseSettings, PydanticBaseSettingsSource\n\nlogger = logging.getLogger(__name__)\n\n\nclass AWSSecretManagerSettingsSource(PydanticBaseSettingsSource):\n    def __init__(self, settings_cls: type[BaseSettings], secret_id: str = "zksato/secrets"):\n        super().__init__(settings_cls)\n        self.secret_id = os.environ.get("ZKSATO_AWS_SECRET_ID", secret_id)\n        self.region_name = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")\n        use_aws = os.environ.get("ZKSATO_USE_AWS_SECRETS", "false").lower()\n        self.enabled = use_aws in ("true", "1", "yes")\n        self.secrets_cache: dict[str, Any] = {}\n        if self.enabled:\n            self._load_secrets()\n\n    def _load_secrets(self) -> None:\n        try:\n            boto3: Any = import_module("boto3")\n        except ImportError:  # pragma: no cover - optional dependency\n            logger.debug("boto3 not installed; AWS Secrets Manager disabled, using env vars")\n            return\n        try:\n            session = boto3.session.Session()\n            client = session.client(service_name="secretsmanager", region_name=self.region_name)\n            response = client.get_secret_value(SecretId=self.secret_id)\n            if "SecretString" in response:\n                self.secrets_cache = json.loads(response["SecretString"])\n        except Exception as exc:  # pragma: no cover - provider-specific failures\n            logger.warning(\n                "Failed to fetch from AWS Secrets Manager: %s. Falling back to env vars.",\n                exc,\n            )\n\n    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:\n        if self.secrets_cache and field_name in self.secrets_cache:\n            return self.secrets_cache[field_name], field_name, False\n\n        env_val = os.environ.get(f"ZKSATO_{field_name.upper()}")\n        if env_val is not None:\n            return env_val, field_name, False\n\n        return None, field_name, False\n\n    def prepare_field_value(\n        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool\n    ) -> Any:\n        return value\n\n    def __call__(self) -> dict[str, Any]:\n        data: dict[str, Any] = {}\n        for field_name, field in self.settings_cls.model_fields.items():\n            value, key, value_is_complex = self.get_field_value(field, field_name)\n            if value is not None:\n                data[key] = self.prepare_field_value(field_name, field, value, value_is_complex)\n        return data\n''')

for _ in range(2):
    replace_once(
        "src/zksato/prediction/live.py",
        "    async def get_market_quote(self, market_id: str) -> dict[str, float]:\n",
        "    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:\n",
    )

replace_once(
    "src/zksato/broker/ccxt.py",
    "            import ccxt  # type: ignore[import-not-found]\n",
    "            import ccxt\n",
)

replace_once(
    "src/zksato/broker/prediction.py",
    "        self, market_id: str, side: str, amount_usd: float\n",
    "        self, market_id: str, side: str, amount_usd: float, price: float\n",
)
replace_once(
    "src/zksato/broker/prediction.py",
    "            response = await self._client.create_order(market_id, side_str, amount_usd)\n",
    "            response = await self._client.create_order(\n                market_id, side_str, amount_usd, float(intent.price)\n            )\n",
)

replace_once(
    "src/zksato/prediction/broker.py",
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass\nfrom typing import Any\n",
)
replace_once(
    "src/zksato/prediction/broker.py",
    "        self.fills: list[Fill] = []\n",
    "        self.fills: list[Fill] = []\n        self._orders: dict[str, dict[str, Any]] = {}\n",
)
replace_once(
    "src/zksato/prediction/broker.py",
    "    def settle(self, winner: Side) -> float:\n",
    '''    async def create_order(\n        self, market_id: str, side: str, amount_usd: float, price: float\n    ) -> dict[str, Any]:\n        try:\n            normalized_side = Side(side.lower())\n        except ValueError as exc:\n            raise ValueError(f"unsupported prediction side: {side}") from exc\n        if normalized_side not in {Side.UP, Side.DOWN}:\n            raise ValueError(f"unsupported prediction side: {side}")\n        fill = self.execute(normalized_side, price, amount_usd)\n        order_id = f"paper-{len(self.fills)}"\n        payload: dict[str, Any] = {\n            "id": order_id,\n            "market_id": market_id,\n            "side": fill.side.value,\n            "amount": amount_usd / price,\n            "price": fill.price,\n            "status": "filled",\n        }\n        self._orders[order_id] = payload\n        return dict(payload)\n\n    async def cancel_order(self, order_id: str) -> dict[str, Any]:\n        payload = self._orders.get(order_id)\n        if payload is None:\n            raise ValueError("paper prediction order not found")\n        cancelled = dict(payload)\n        cancelled["status"] = "canceled"\n        return cancelled\n\n    async def fetch_open_orders(self, market_id: str) -> list[dict[str, Any]]:\n        return [\n            dict(payload)\n            for payload in self._orders.values()\n            if payload.get("market_id") == market_id and payload.get("status") == "open"\n        ]\n\n    async def fetch_balance(self) -> dict[str, Any]:\n        return {"cash": self.cash}\n\n    def settle(self, winner: Side) -> float:\n''',
)

replace_once(
    "tests/test_prediction.py",
    "    async def create_order(self, market_id: str, side: str, amount_usd: float) -> dict[str, object]:\n",
    "    async def create_order(\n        self, market_id: str, side: str, amount_usd: float, price: float\n    ) -> dict[str, object]:\n",
)
replace_once(
    "tests/test_prediction.py",
    '            "price": 0.5,\n',
    '            "price": price,\n',
)

engine = Path("src/zksato/agent_os/engine.py")
text = engine.read_text()
old = '''            history = self.trading_service.store.get_history(symbol)\n            if not history or len(history) < period:\n                count = len(history) if history else 0\n                return {\n                    "success": False,\n                    "error": f"Insufficient price history for {symbol} (have {count})",\n                }\n            prices = [h.close for h in history]\n            ind_lower = indicator.lower()\n            if ind_lower == "rsi":\n                from zksato.indicators import calculate_rsi\n\n                val = calculate_rsi(prices, period=period)\n                return {"success": True, "indicator": "rsi", "symbol": symbol, "value": val}\n            elif ind_lower == "ema":\n                from zksato.indicators import calculate_ema\n\n                val = calculate_ema(prices, period=period)\n                return {"success": True, "indicator": "ema", "symbol": symbol, "value": val}\n            else:\n                return {"success": False, "error": f"Unsupported indicator: {indicator}"}\n'''
new = '''            prices = self.trading_service.store.get_prices(symbol)\n            ind_lower = indicator.lower()\n            if ind_lower == "rsi":\n                from zksato.indicators import rsi\n\n                val = rsi(prices, period=period)\n            elif ind_lower == "ema":\n                from zksato.indicators import ema\n\n                val = ema(prices, period=period)\n            else:\n                return {"success": False, "error": f"Unsupported indicator: {indicator}"}\n            if val is None:\n                return {\n                    "success": False,\n                    "error": f"Insufficient price history for {symbol} (have {len(prices)})",\n                }\n            return {\n                "success": True,\n                "indicator": ind_lower,\n                "symbol": symbol,\n                "value": val,\n            }\n'''
if old not in text:
    raise SystemExit("src/zksato/agent_os/engine.py: indicator block not found")
text = text.replace(old, new, 1)
old_cancel = '''                cancelled = await self.trading_service.cancel_order(\n                    order_id, actor=f"agent:{acc.agent_name}"\n                )\n'''
if old_cancel not in text:
    raise SystemExit("src/zksato/agent_os/engine.py: cancel block not found")
engine.write_text(text.replace(old_cancel, "                cancelled = await self.trading_service.cancel_order(order_id)\n", 1))

api = Path("src/zksato/api.py")
text = api.read_text()
old = '''    agent_name = str(payload.get("agent_name", "agent"))\n    collateral = float(payload.get("collateral_usd", 1000.0))\n    account = agent_subaccounts.create_subaccount(agent_name=agent_name, collateral_usd=collateral)\n'''
new = '''    agent_name = str(payload.get("agent_name", "agent"))\n    raw_collateral = payload.get("collateral_usd", 1000.0)\n    if isinstance(raw_collateral, bool) or not isinstance(raw_collateral, (str, int, float)):\n        raise HTTPException(status_code=422, detail="collateral_usd must be numeric")\n    try:\n        collateral = float(raw_collateral)\n    except ValueError as exc:\n        raise HTTPException(status_code=422, detail="collateral_usd must be numeric") from exc\n    account = agent_subaccounts.create_subaccount(agent_name=agent_name, collateral_usd=collateral)\n'''
if old not in text:
    raise SystemExit("src/zksato/api.py: collateral block not found")
text = text.replace(old, new, 1)
old = '''    if text.startswith("/"):\n        resp = await notifier.handle_telegram_command(\n            text,\n            chat_id,\n            system_status={\n                "environment": settings.environment,\n                "execution_mode": settings.trading_mode,\n                "kill_switch_active": service.kill_switch_active,\n            },\n            portfolio_summary={\n                "total": float(store.get_portfolio_pnl()),\n                "currency": "USDT",\n            },\n            quotes=[{"symbol": q.symbol, "price": q.last} for q in store.list_quotes()],\n        )\n'''
new = '''    if text.startswith("/"):\n        portfolio_summary: dict[str, Any] | None = None\n        command_name = text.split("@", 1)[0].strip().lower()\n        if command_name == "/pnl":\n            snapshot = await service.portfolio(record_snapshot=False)\n            portfolio_summary = {\n                "total": snapshot.realized_pnl + snapshot.unrealized_pnl,\n                "currency": "USDT",\n            }\n        resp = await notifier.handle_telegram_command(\n            text,\n            chat_id,\n            system_status={\n                "environment": settings.environment,\n                "execution_mode": settings.trading_mode,\n                "kill_switch_active": settings.kill_switch,\n            },\n            portfolio_summary=portfolio_summary,\n            quotes=[{"symbol": q.symbol, "price": q.last} for q in store.list_quotes()],\n        )\n'''
if old not in text:
    raise SystemExit("src/zksato/api.py: telegram status block not found")
api.write_text(text.replace(old, new, 1))
