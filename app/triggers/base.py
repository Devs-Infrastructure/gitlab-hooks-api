"""Abstract base class for all pipeline triggers."""
import abc


class BaseTrigger(abc.ABC):
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
