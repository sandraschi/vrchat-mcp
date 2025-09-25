"""
Secrets management for VRChat MCP.

This module provides secure handling of sensitive configuration data,
environment variables, and encrypted configuration files.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import hashlib
import secrets

try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages sensitive configuration data securely."""

    def __init__(self, secrets_dir: Optional[Union[str, Path]] = None):
        """Initialize the secrets manager.

        Args:
            secrets_dir: Directory to store encrypted secrets files
        """
        self.secrets_dir = Path(secrets_dir) if secrets_dir else Path.home() / ".vrchat_mcp" / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

        # Generate or load encryption key
        self.key_file = self.secrets_dir / ".key"
        self.encryption_key = self._get_or_create_key()

        # Initialize cipher if cryptography is available
        self.cipher = Fernet(self.encryption_key) if HAS_CRYPTOGRAPHY else None

    def _get_or_create_key(self) -> bytes:
        """Get existing encryption key or create a new one."""
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read encryption key: {e}")

        # Generate new key
        key = Fernet.generate_key() if HAS_CRYPTOGRAPHY else secrets.token_bytes(32)
        try:
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
        except Exception as e:
            logger.warning(f"Failed to save encryption key: {e}")

        return key

    def get_secret(self, key: str, default: Any = None, encrypted: bool = False) -> Any:
        """Get a secret value from environment or encrypted storage.

        Args:
            key: Secret key name
            default: Default value if not found
            encrypted: Whether to look in encrypted storage

        Returns:
            Secret value or default
        """
        # First check environment variables
        env_key = f"VRCHAT_MCP_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Then check encrypted storage if available
        if encrypted and self.cipher:
            try:
                secret_file = self.secrets_dir / f"{key}.enc"
                if secret_file.exists():
                    with open(secret_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    return json.loads(decrypted_data.decode())
            except Exception as e:
                logger.error(f"Failed to decrypt secret {key}: {e}")

        return default

    def set_secret(self, key: str, value: Any, encrypted: bool = False) -> bool:
        """Store a secret value.

        Args:
            key: Secret key name
            value: Value to store
            encrypted: Whether to encrypt the value

        Returns:
            True if successful, False otherwise
        """
        try:
            if encrypted and self.cipher:
                # Store encrypted
                secret_file = self.secrets_dir / f"{key}.enc"
                data = json.dumps(value).encode()
                encrypted_data = self.cipher.encrypt(data)

                with open(secret_file, 'wb') as f:
                    f.write(encrypted_data)
                os.chmod(secret_file, 0o600)
            else:
                # Store as environment variable (not persistent)
                env_key = f"VRCHAT_MCP_{key.upper()}"
                os.environ[env_key] = str(value)

            return True
        except Exception as e:
            logger.error(f"Failed to set secret {key}: {e}")
            return False

    def load_config_with_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration with secrets resolved.

        Args:
            config: Configuration dictionary that may contain secret references

        Returns:
            Configuration with secrets resolved
        """
        resolved_config = {}

        for key, value in config.items():
            if isinstance(value, dict):
                resolved_config[key] = self.load_config_with_secrets(value)
            elif isinstance(value, str) and value.startswith("secret://"):
                # Reference to a secret
                secret_key = value[9:]  # Remove "secret://" prefix
                resolved_config[key] = self.get_secret(secret_key)
            else:
                resolved_config[key] = value

        return resolved_config

    def get_available_secrets(self) -> Dict[str, bool]:
        """Get list of available secrets and their encryption status.

        Returns:
            Dictionary mapping secret names to encryption status
        """
        available = {}

        # Check environment variables
        for env_key, env_value in os.environ.items():
            if env_key.startswith("VRCHAT_MCP_"):
                secret_key = env_key[12:].lower()  # Remove prefix and lowercase
                available[secret_key] = False  # Not encrypted

        # Check encrypted files
        if self.secrets_dir.exists():
            for secret_file in self.secrets_dir.glob("*.enc"):
                secret_key = secret_file.stem
                available[secret_key] = True  # Encrypted

        return available

    def validate_secrets_access(self) -> Dict[str, Any]:
        """Validate that secrets can be accessed properly.

        Returns:
            Dictionary with validation results
        """
        results = {
            "cryptography_available": HAS_CRYPTOGRAPHY,
            "secrets_dir_exists": self.secrets_dir.exists(),
            "key_file_exists": self.key_file.exists(),
            "secrets_dir_writable": False,
            "available_secrets": self.get_available_secrets()
        }

        # Test write access
        try:
            test_file = self.secrets_dir / ".test"
            with open(test_file, 'w') as f:
                f.write("test")
            test_file.unlink()
            results["secrets_dir_writable"] = True
        except Exception:
            pass

        return results


# Global secrets manager instance
secrets_manager = SecretsManager()


def get_secret(key: str, default: Any = None, encrypted: bool = False) -> Any:
    """Convenience function to get a secret."""
    return secrets_manager.get_secret(key, default, encrypted)


def set_secret(key: str, value: Any, encrypted: bool = False) -> bool:
    """Convenience function to set a secret."""
    return secrets_manager.set_secret(key, value, encrypted)

