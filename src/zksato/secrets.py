import json
import logging
import os
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

logger = logging.getLogger(__name__)

try:
    import boto3  # type: ignore[import-not-found]
    from botocore.exceptions import ClientError  # type: ignore[import-not-found]

    _AWS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None  # type: ignore[assignment]
    ClientError = Exception  # type: ignore[assignment,misc]
    _AWS_AVAILABLE = False


class AWSSecretManagerSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], secret_id: str = "zksato/secrets"):
        super().__init__(settings_cls)
        self.secret_id = os.environ.get("ZKSATO_AWS_SECRET_ID", secret_id)
        self.region_name = os.environ.get("AWS_REGION", "ap-southeast-1")
        self.secrets_cache: dict[str, Any] = {}
        self._load_secrets()

    def _load_secrets(self) -> None:
        if not _AWS_AVAILABLE:
            logger.debug("boto3 not installed; AWS Secrets Manager disabled, using env vars")
            return
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name="secretsmanager",
                region_name=self.region_name
            )
            response = client.get_secret_value(SecretId=self.secret_id)
            if "SecretString" in response:
                self.secrets_cache = json.loads(response["SecretString"])
        except ClientError as e:
            logger.warning(
                f"Failed to fetch from AWS Secrets Manager: {e}. Falling back to env vars."
            )
        except Exception as e:
            logger.warning(
                f"Error fetching from AWS Secrets Manager: {e}. Falling back to env vars."
            )

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Try AWS Secrets Manager first
        if self.secrets_cache and field_name in self.secrets_cache:
            return self.secrets_cache[field_name], field_name, False
        
        # Fallback to env var
        env_val = os.environ.get(f"ZKSATO_{field_name.upper()}")
        if env_val is not None:
            return env_val, field_name, False
            
        return None, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            field_value = self.prepare_field_value(
                field_name, field, field_value, value_is_complex
            )
            if field_value is not None:
                d[field_key] = field_value
        return d
