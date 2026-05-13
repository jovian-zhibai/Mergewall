"""Server configuration for CodeGuardian SaaS.

All settings are read from environment variables with sensible defaults
for local development. In production, set at least GITHUB_WEBHOOK_SECRET.
"""

import os

# ---------------------------------------------------------------------------
# GitHub App credentials
# ---------------------------------------------------------------------------
GITHUB_APP_ID: str = os.getenv("GITHUB_APP_ID", "3661209")
GITHUB_PRIVATE_KEY: str = os.getenv("GITHUB_PRIVATE_KEY", "")
GITHUB_PRIVATE_KEY_PATH: str = os.getenv(
    "GITHUB_PRIVATE_KEY_PATH", "mergewall-bot.private-key.pem"
)
GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_API_BASE: str = "https://api.github.com"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# LLM settings (forwarded to CodeReviewWorkflow)
# ---------------------------------------------------------------------------
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://platform.xiaomimimo.com/api/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "mimo-v2.5-pro")

# ---------------------------------------------------------------------------
# Private key (loaded lazily, cached after first read)
# ---------------------------------------------------------------------------
_private_key: str | None = None


def get_private_key() -> str:
    """Return the GitHub App private key.

    Priority: ``GITHUB_PRIVATE_KEY`` env var (PEM string) →
    ``GITHUB_PRIVATE_KEY_PATH`` file (local dev fallback).
    """
    global _private_key
    if _private_key is None:
        if GITHUB_PRIVATE_KEY:
            _private_key = GITHUB_PRIVATE_KEY
        else:
            path = os.path.expanduser(GITHUB_PRIVATE_KEY_PATH)
            with open(path) as f:
                _private_key = f.read()
    return _private_key
