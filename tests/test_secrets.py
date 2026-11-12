"""Tests for secrets module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zksato.secrets import AWSSecretManagerSettingsSource, validate_env_file


class TestAWSSecretManagerSettingsSource:
    def test_init_disabled_by_default(self) -> None:
        os.environ.pop("ZKSATO_USE_AWS_SECRETS", None)
        source = AWSSecretManagerSettingsSource(MagicMock())
        assert source.enabled is False
        assert source.secrets_cache == {}

    def test_init_enabled_with_env_var(self) -> None:
        os.environ["ZKSATO_USE_AWS_SECRETS"] = "true"
        try:
            with patch("zksato.secrets.import_module") as mock_import:
                mock_boto3 = MagicMock()
                mock_session = MagicMock()
                mock_client = MagicMock()
                mock_session.client.return_value = mock_client
                mock_boto3.session.Session.return_value = mock_session
                mock_import.return_value = mock_boto3

                source = AWSSecretManagerSettingsSource(MagicMock())
                assert source.enabled is True
        finally:
            os.environ.pop("ZKSATO_USE_AWS_SECRETS", None)

    def test_load_secrets_success(self) -> None:
        with patch("zksato.secrets.import_module") as mock_import:
            mock_boto3 = MagicMock()
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_client.get_secret_value.return_value = {
                "SecretString": json.dumps({"key1": "value1", "key2": "value2"})
            }
            mock_session.client.return_value = mock_client
            mock_boto3.session.Session.return_value = mock_session
            mock_import.return_value = mock_boto3

            source = AWSSecretManagerSettingsSource(MagicMock(), secret_id="test/secret")
            # Manually trigger load since it's called in __init__ only when enabled
            source.enabled = True
            source._load_secrets()

            assert source.secrets_cache == {"key1": "value1", "key2": "value2"}
            mock_client.get_secret_value.assert_called_once_with(SecretId="test/secret")

    def test_load_secrets_boto3_not_installed(self) -> None:
        with patch("zksato.secrets.import_module", side_effect=ImportError):
            source = AWSSecretManagerSettingsSource(MagicMock())
            source.enabled = True
            source._load_secrets()  # Should not raise
            assert source.secrets_cache == {}

    def test_load_secrets_client_error(self) -> None:
        with patch("zksato.secrets.import_module") as mock_import:
            mock_boto3 = MagicMock()
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_client.get_secret_value.side_effect = Exception("Access denied")
            mock_session.client.return_value = mock_client
            mock_boto3.session.Session.return_value = mock_session
            mock_import.return_value = mock_boto3

            source = AWSSecretManagerSettingsSource(MagicMock())
            source.enabled = True
            source._load_secrets()  # Should not raise, just log warning
            assert source.secrets_cache == {}

    def test_get_field_value_from_cache(self) -> None:
        source = AWSSecretManagerSettingsSource(MagicMock())
        source.enabled = True
        source.secrets_cache = {"test_field": "cached_value"}

        field = MagicMock()
        value, key, is_complex = source.get_field_value(field, "test_field")
        assert value == "cached_value"
        assert key == "test_field"
        assert is_complex is False

    def test_get_field_value_from_env(self) -> None:
        source = AWSSecretManagerSettingsSource(MagicMock())
        source.enabled = True
        source.secrets_cache = {}
        os.environ["ZKSATO_TEST_FIELD"] = "env_value"

        try:
            field = MagicMock()
            value, key, is_complex = source.get_field_value(field, "test_field")
            assert value == "env_value"
            assert key == "test_field"
            assert is_complex is False
        finally:
            os.environ.pop("ZKSATO_TEST_FIELD", None)

    def test_get_field_value_returns_none_when_not_found(self) -> None:
        source = AWSSecretManagerSettingsSource(MagicMock())
        source.enabled = True
        source.secrets_cache = {}

        field = MagicMock()
        value, key, is_complex = source.get_field_value(field, "nonexistent")
        assert value is None
        assert key == "nonexistent"
        assert is_complex is False

    def test_prepare_field_value_returns_value(self) -> None:
        source = AWSSecretManagerSettingsSource(MagicMock())
        field = MagicMock()
        result = source.prepare_field_value("test", field, "test_value", False)
        assert result == "test_value"

    def test_call_returns_merged_dict(self) -> None:
        source = AWSSecretManagerSettingsSource(MagicMock())
        source.enabled = True
        source.secrets_cache = {"field1": "cache_value"}
        os.environ["ZKSATO_FIELD2"] = "env_value"

        try:
            settings_cls = MagicMock()
            settings_cls.model_fields = {
                "field1": MagicMock(),
                "field2": MagicMock(),
                "field3": MagicMock(),
            }
            source.settings_cls = settings_cls

            result = source()
            assert result == {"field1": "cache_value", "field2": "env_value"}
        finally:
            os.environ.pop("ZKSATO_FIELD2", None)


class TestValidateEnvFile:
    def test_valid_env_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Comment\n")
            f.write("KEY1=value1\n")
            f.write("KEY2=PLACEHOLDER_VALUE\n")
            f.write("ANOTHER_KEY=another_value\n")
            temp_path = f.name

        try:
            validate_env_file(temp_path)  # Should not raise
        finally:
            Path(temp_path).unlink()

    def test_env_file_not_found(self) -> None:
        with pytest.raises(ValueError, match="Environment file not found"):
            validate_env_file("/nonexistent/path/.env")

    def test_invalid_line_missing_equals(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("INVALID_LINE\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="missing '=' in line"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_invalid_key_format(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("123INVALID=value\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="invalid environment variable name"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_invalid_key_with_special_chars(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY-WITH-DASH=value\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="invalid environment variable name"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_shell_metacharacters_in_value(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("KEY=value;rm -rf /\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="contains shell metacharacters"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_shell_metacharacters_various(self) -> None:
        for meta in ["&", "|", "`", "$", "(", ")", "{", "}", "[", "]", "<", ">"]:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
                f.write(f"KEY=value{meta}test\n")
                temp_path = f.name

            try:
                with pytest.raises(ValueError, match="contains shell metacharacters"):
                    validate_env_file(temp_path)
            finally:
                Path(temp_path).unlink()

    def test_secret_key_without_placeholder(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("API_KEY=actual_secret_value\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="secret key.*must use a placeholder"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_secret_key_with_placeholder_allowed(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("API_KEY=${API_KEY}\n")
            temp_path = f.name

        try:
            validate_env_file(temp_path)  # Should not raise
        finally:
            Path(temp_path).unlink()

    def test_password_key_without_placeholder(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DB_PASSWORD=secret123\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="secret key.*must use a placeholder"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_token_key_without_placeholder(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("AUTH_TOKEN=Bearer abc123\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="secret key.*must use a placeholder"):
                validate_env_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_empty_lines_and_comments_ignored(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("\n")
            f.write("# This is a comment\n")
            f.write("   \n")
            f.write("VALID_KEY=value\n")
            temp_path = f.name

        try:
            validate_env_file(temp_path)  # Should not raise
        finally:
            Path(temp_path).unlink()

    def test_case_insensitive_secret_detection(self) -> None:
        for key in ["PASSWORD", "SECRET", "API_KEY", "PRIVATE_KEY", "PIN", "CREDENTIAL"]:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
                f.write(f"{key}=value\n")
                temp_path = f.name

            try:
                with pytest.raises(ValueError, match="secret key.*must use a placeholder"):
                    validate_env_file(temp_path)
            finally:
                Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
