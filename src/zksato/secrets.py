import json
import logging
import os
from importlib import import_module
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

logger = logging.getLogger(__name__)


class AWSSecretManagerSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], secret_id: str = "zksato/secrets"):
        super().__init__(settings_cls)
        self.secret_id = os.environ.get("ZKSATO_AWS_SECRET_ID", secret_id)
        self.region_name = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        use_aws = os.environ.get("ZKSATO_USE_AWS_SECRETS", "false").lower()
        self.enabled = use_aws in ("true", "1", "yes")
        self.secrets_cache: dict[str, Any] = {}
        if self.enabled:
            self._load_secrets()

    def _load_secrets(self) -> None:
        try:
            boto3: Any = import_module("boto3")
        except ImportError:  # pragma: no cover - optional dependency
            logger.debug("boto3 not installed; AWS Secrets Manager disabled, using env vars")
            return
        try:
            session = boto3.session.Session()
            client = session.client(service_name="secretsmanager", region_name=self.region_name)
            response = client.get_secret_value(SecretId=self.secret_id)
            if "SecretString" in response:
                self.secrets_cache = json.loads(response["SecretString"])
        except Exception:  # pragma: no cover - provider-specific failures
            logger.warning("Failed to fetch from AWS Secrets Manager. Falling back to env vars.")

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        if self.secrets_cache and field_name in self.secrets_cache:
            return self.secrets_cache[field_name], field_name, False

        env_val = os.environ.get(f"ZKSATO_{field_name.upper()}")
        if env_val is not None:
            return env_val, field_name, False

        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            value, key, value_is_complex = self.get_field_value(field, field_name)
            if value is not None:
                data[key] = self.prepare_field_value(field_name, field, value, value_is_complex)
        return data


def validate_env_file(env_path: str = ".env") -> None:
    """Validate an .env file for safe formatting and no embedded secrets.

    Checks:
      - File exists and is readable
      - Each non-comment line is valid KEY=VALUE
      - Keys match [A-Z_][A-Z0-9_]*
      - Values contain no shell metacharacters (injection prevention)
      - No literal secret-looking values (placeholders only)

    Raises ValueError with a descriptive message on any violation.
    """
    import re
    from pathlib import Path

    path = Path(env_path)
    if not path.exists():
        raise ValueError(f"Environment file not found: {env_path}")

    text = path.read_text(encoding="utf-8")
    key_re = re.compile(r"^[A-Z_][A-Z0-9_]*$")
    shell_meta = re.compile(r"[;&|`$(){}[\]<>]")

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{env_path}:{lineno}: missing '=' in line: {raw!r}")
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key_re.match(key):
            raise ValueError(f"{env_path}:{lineno}: invalid environment variable name '{key}'")
        # Allow ${...} placeholder syntax for secret values
        is_placeholder = val.startswith("${") and val.endswith("}")
        if not is_placeholder and shell_meta.search(val):
            raise ValueError(
                f"{env_path}:{lineno}: value for '{key}' contains shell metacharacters"
            )
        # คีย์ที่เป็นหรือลงท้ายด้วยคำว่าลับจริง (ค่าที่ไม่ควรเขียนตรงใน .env) เท่านั้นที่ต้องใช้ placeholder
        is_secret_key = bool(
            re.search(r"(?:^|_)(SECRET|API_KEY|PRIVATE_KEY|PASSWORD|PIN|CREDENTIAL|TOKEN)$", key)
        )
        if is_secret_key and val and not is_placeholder:
            raise ValueError(f"{env_path}:{lineno}: secret key '{key}' must use a placeholder")
