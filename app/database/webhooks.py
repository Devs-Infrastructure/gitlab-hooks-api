"""Database operations for webhooks."""
from app.connectors import webhooks_collection


async def save_or_update_webhook(group_id: int, webhook_name: str, data: dict):
    """Save or update webhook data in MongoDB.
    
    Args:
        group_id: GitLab group ID
        webhook_name: Name of the webhook (e.g., 'autowebhook')
        data: Dictionary containing webhook data to save
    """
    key = f"{group_id}:{webhook_name}"
    await webhooks_collection.update_one(
        {"_id": key},
        {"$set": {"data": data}},
        upsert=True,
    )

