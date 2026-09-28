"""Trigger registry.

TRIGGER_TYPE env var controls which triggers are active.
Accepts comma-separated values: "gitlab_pipeline", "openclaw", "opencode".
Example: TRIGGER_TYPE=gitlab_pipeline,openclaw
"""
from app.config import TRIGGER_TYPE
from app.triggers.base import BaseTrigger
from app.triggers.gitlab_pipeline import GitLabPipelineTrigger
from app.triggers.openclaw import OpenClawTrigger
from app.triggers.opencode import OpenCodeTrigger

_REGISTRY: dict[str, type[BaseTrigger]] = {
    "gitlab_pipeline": GitLabPipelineTrigger,
    "openclaw": OpenClawTrigger,
    "opencode": OpenCodeTrigger,
}


def get_triggers() -> list[BaseTrigger]:
    """Return instantiated trigger objects for the configured TRIGGER_TYPE."""
    names = [t.strip() for t in TRIGGER_TYPE.split(",") if t.strip()]
    triggers: list[BaseTrigger] = []
    for name in names:
        cls = _REGISTRY.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown trigger type '{name}'. "
                f"Valid values: {', '.join(_REGISTRY)}"
            )
        triggers.append(cls())
    return triggers
