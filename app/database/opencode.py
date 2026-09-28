"""Database operations for the OpenCode trigger."""
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.connectors import opencode_events_collection, opencode_sessions_collection


def _mr_key(project_id: int, mr_iid: int) -> str:
    return f"{project_id}:{mr_iid}"


async def claim_event(event_key: str) -> bool:
    """Atomically record a webhook event. Returns False if it was already seen (retry)."""
    try:
        await opencode_events_collection.insert_one(
            {"_id": event_key, "received_at": datetime.now(timezone.utc)}
        )
        return True
    except DuplicateKeyError:
        return False


async def get_mr_session(project_id: int, mr_iid: int) -> dict | None:
    """Return the stored OpenCode session mapping for an MR, if any."""
    return await opencode_sessions_collection.find_one({"_id": _mr_key(project_id, mr_iid)})


async def save_mr_session(project_id: int, mr_iid: int, data: dict):
    """Store project_id + mr_iid -> OpenCode session mapping."""
    await opencode_sessions_collection.update_one(
        {"_id": _mr_key(project_id, mr_iid)},
        {"$set": {**data, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
