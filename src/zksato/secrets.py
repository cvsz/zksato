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
        except Exception as exc:  # pragma: no cover - provider-specific failures
            logger.warning(
                "Failed to fetch from AWS Secrets Manager: %s. Falling back to env vars.",
                exc,
            )

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
