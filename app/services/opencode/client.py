"""OpenCode server HTTP API client (`opencode serve`)."""
import asyncio
import time
from typing import Optional

import httpx

from app.config import OPENCODE_HOST, OPENCODE_USERNAME, OPENCODE_PASSWORD


class OpenCodeAPIError(Exception):
    """Raised when the OpenCode server returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class OpenCodeClient:
    """Minimal client for the OpenCode session API. `directory` selects the project instance."""

    def __init__(
        self,
        base_url: str = OPENCODE_HOST,
        username: str = OPENCODE_USERNAME,
        password: str = OPENCODE_PASSWORD,
    ):
        self.base_url = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(username, password) if password else None

    async def _request(
        self,
        method: str,
        path: str,
        directory: Optional[str] = None,
        json: Optional[dict] = None,
    ) -> httpx.Response:
        params = {"directory": directory} if directory else None
        async with httpx.AsyncClient(auth=self._auth, timeout=30.0) as client:
            response = await client.request(
                method, f"{self.base_url}{path}", params=params, json=json
            )
        if response.is_error:
            raise OpenCodeAPIError(
                f"{method} {path} failed: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        return response

    async def create_session(self, title: str, directory: Optional[str] = None) -> dict:
        """Create a new session. Returns the session object (with `id`)."""
        response = await self._request("POST", "/session", directory, json={"title": title})
        return response.json()

    async def session_exists(self, session_id: str, directory: Optional[str] = None) -> bool:
        try:
            await self._request("GET", f"/session/{session_id}", directory)
            return True
        except OpenCodeAPIError as e:
            if e.status_code == 404:
                return False
            raise

    async def prompt_async(
        self,
        session_id: str,
        text: str,
        directory: Optional[str] = None,
        agent: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Send a prompt without waiting for the reply (`POST /session/:id/prompt_async`)."""
        body: dict = {"parts": [{"type": "text", "text": text}]}
        if agent:
            body["agent"] = agent
        if model:
            provider_id, _, model_id = model.partition("/")
            body["model"] = {"providerID": provider_id, "modelID": model_id}
        await self._request("POST", f"/session/{session_id}/prompt_async", directory, json=body)

    async def is_busy(self, session_id: str, directory: Optional[str] = None) -> bool:
        """True while the session is running (`busy` or `retry`)."""
        response = await self._request("GET", "/session/status", directory)
        status = response.json().get(session_id) or {}
        return status.get("type", "idle") != "idle"

    async def wait_until_idle(
        self,
        session_id: str,
        directory: Optional[str] = None,
        timeout: float = 3600,
        poll_interval: float = 5,
    ) -> bool:
        """Poll until the session is idle. Returns False on timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not await self.is_busy(session_id, directory):
                return True
            await asyncio.sleep(poll_interval)
        return False

    async def list_messages(self, session_id: str, directory: Optional[str] = None) -> list[dict]:
        """Session messages as `[{"info": {...}, "parts": [...]}]`, oldest first."""
        response = await self._request("GET", f"/session/{session_id}/message", directory)
        return response.json()

    async def message_ids(self, session_id: str, directory: Optional[str] = None) -> set[str]:
        return {m["info"]["id"] for m in await self.list_messages(session_id, directory)}

    async def last_error(self, session_id: str, directory: Optional[str] = None) -> Optional[str]:
        """Error of the latest assistant message, if that run failed."""
        messages = await self.list_messages(session_id, directory)
        assistant = [m["info"] for m in messages if m["info"].get("role") == "assistant"]
        return _error_text(assistant[-1]) if assistant else None

    async def wait_until_started(
        self,
        session_id: str,
        known_message_ids: set[str],
        directory: Optional[str] = None,
        timeout: float = 60,
        poll_interval: float = 1,
    ) -> Optional[str]:
        """Poll until the prompt sent after `known_message_ids` starts running.

        Returns None once the session is busy or produced a reply, the error text if
        the reply failed, or a timeout message if nothing happened.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.is_busy(session_id, directory):
                return None
            replies = [
                m["info"] for m in await self.list_messages(session_id, directory)
                if m["info"]["id"] not in known_message_ids and m["info"].get("role") == "assistant"
            ]
            if replies:
                return _error_text(replies[-1])
            await asyncio.sleep(poll_interval)
        return f"session did not start running within {int(timeout)}s (check agent/model/provider config)"


def _error_text(message_info: dict) -> Optional[str]:
    error = message_info.get("error")
    if not error:
        return None
    return (error.get("data") or {}).get("message") or error.get("name") or str(error)
