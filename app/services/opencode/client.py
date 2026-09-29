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

    async def wait_until_busy(
        self,
        session_id: str,
        directory: Optional[str] = None,
        timeout: float = 30,
        poll_interval: float = 1,
    ) -> bool:
        """Poll until the session starts running. Returns False if it never did within timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if await self.is_busy(session_id, directory):
                return True
            await asyncio.sleep(poll_interval)
        return False
