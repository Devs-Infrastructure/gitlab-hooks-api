"""Abstract base class for all pipeline triggers."""
import abc

from app.config import CODE_PHRASE


class BaseTrigger(abc.ABC):
    def matches(self, note: str) -> bool:
        return CODE_PHRASE in (note or "")

    async def on_merge_request_opened(self, project_id: int, flow_context: dict) -> dict | None:
        """Handle a newly opened MR. Returns None when the trigger ignores it."""
        return None

    @abc.abstractmethod
    async def fire(
        self,
        project_id: int,
        ref: str,
        trigger_token: str | None,
        flow_context: dict,
        ai_flow_input: str,
        input_event: str,
    ) -> dict:
        """Execute the trigger.

        Args:
            project_id:    GitLab project ID.
            ref:           Branch or tag name.
            trigger_token: GitLab pipeline trigger token (None for triggers that don't need it).
            flow_context:  Structured dict with event/user/project/MR/note/commit.
            ai_flow_input: Raw note text.
            input_event:   Event name string.

        Returns:
            Arbitrary dict from the downstream system.
        """
