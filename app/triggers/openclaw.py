"""OpenClaw trigger."""
import json

import httpx

from app.config import (
    OPENCLAW_HOST,
    OPENCLAW_OPERATOR_TOKEN,
    OPENCLAW_WEBHOOK_SECRET,
    OPENCLAW_GENERAL_PROMPT,
)
from app.triggers.base import BaseTrigger


class OpenClawTrigger(BaseTrigger):
    """Triggers an OpenClaw webhook endpoint."""

    def __init__(
        self,
        host: str = OPENCLAW_HOST,
        operator_token: str = OPENCLAW_OPERATOR_TOKEN,
        webhook_secret: str = OPENCLAW_WEBHOOK_SECRET,
        general_prompt: str = OPENCLAW_GENERAL_PROMPT,
    ):
        self._url = host.rstrip("/") + "/plugins/webhooks/trigger"
        self._operator_token = operator_token
        self._webhook_secret = webhook_secret
        self._general_prompt = general_prompt

    async def fire(
        self,
        project_id: int,
        ref: str,
        trigger_token: str | None,
        flow_context: dict,
        ai_flow_input: str,
        input_event: str,
    ) -> dict:
        message = self._general_prompt
        if flow_context:
            message = f"{message}\n\n{json.dumps(flow_context, indent=2)}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._operator_token}",
            "X-OpenClaw-Webhook-Secret": self._webhook_secret,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._url,
                    headers=headers,
                    json={"message": message},
                )
                response.raise_for_status()
                print(f"[OpenClawTrigger] Triggered for project {project_id}")
                try:
                    return response.json()
                except Exception:
                    return {"status": "ok", "status_code": response.status_code}
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"[OpenClawTrigger] HTTP error: "
                f"{e.response.status_code} {e.response.reason_phrase}"
            )
            try:
                body = e.response.text
                if body:
                    error_msg += f" - {body}"
            except Exception:
                pass
            print(error_msg)
            return {"error": error_msg}
        except Exception as e:
            print(f"[OpenClawTrigger] Error: {e}")
            return {"error": str(e)}
