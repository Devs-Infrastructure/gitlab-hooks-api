"""MongoDB connection using Motor (async MongoDB driver)."""
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["gitlab"]
webhooks_collection = db["webhooks"]

