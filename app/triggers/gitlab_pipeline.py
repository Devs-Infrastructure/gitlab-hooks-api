"""GitLab pipeline trigger."""
import json

import httpx

from app.config import GITLAB_HOST
from app.triggers.base import BaseTrigger


class GitLabPipelineTrigger(BaseTrigger):
    """Triggers a GitLab CI pipeline via the pipeline trigger API."""

    def __init__(self, gitlab_host: str = GITLAB_HOST):
        self._api_base = gitlab_host.rstrip("/") + "/api/v4"

    async def fire(
        self,
        project_id: int,
        ref: str,
        trigger_token: str | None,
        flow_context: dict,
        ai_flow_input: str,
        input_event: str,
    ) -> dict:
        if not trigger_token:
            print(f"[GitLabPipelineTrigger] No trigger token for project {project_id}.")
            return {"error": "no_trigger_token"}

        trigger_url = f"{self._api_base}/projects/{project_id}/trigger/pipeline"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    trigger_url,
                    data={
                        "token": trigger_token,
                        "ref": ref,
                        "variables[AI_FLOW_EVENT]": input_event,
                        "variables[AI_FLOW_CONTEXT]": json.dumps(flow_context),
                        "variables[AI_FLOW_INPUT]": ai_flow_input,
                    },
                )
                response.raise_for_status()
                print(f"[GitLabPipelineTrigger] Pipeline triggered for {project_id} on {ref}")
                return response.json()
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"[GitLabPipelineTrigger] HTTP error: "
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
            print(f"[GitLabPipelineTrigger] Error: {e}")
            return {"error": str(e)}
