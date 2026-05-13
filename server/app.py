"""FastAPI application for CodeGuardian GitHub webhook receiver.

Verifies webhook signatures with HMAC-SHA256, dispatches PR review
tasks to the background worker, and returns 202 immediately.
"""

import asyncio
import hashlib
import hmac
import logging

from fastapi import FastAPI, Request, Response

from server import config_server
from server.worker import process_pr_event

logging.basicConfig(level=getattr(logging, config_server.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="CodeGuardian", version="0.2.0")


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _verify_signature(body: bytes, signature_header: str | None) -> bool:
    """Verify the HMAC-SHA256 signature of a GitHub webhook payload."""
    if not config_server.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return True

    if not signature_header:
        return False

    expected = hmac.new(
        config_server.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    expected_full = f"sha256={expected}"
    return hmac.compare_digest(expected_full, signature_header)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Receive and process GitHub webhook events.

    Only ``pull_request`` events with action ``opened`` or ``synchronize``
    are processed. All other events return 200 (acknowledged but ignored).
    """
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(body, signature):
        return Response(status_code=401, content="Invalid signature")

    payload = await request.json()

    event = request.headers.get("X-GitHub-Event", "")
    action = payload.get("action", "")

    if event != "pull_request" or action not in ("opened", "synchronize"):
        return {"status": "ignored", "event": event, "action": action}

    asyncio.create_task(process_pr_event(payload))
    return Response(status_code=202, content="Review queued")
