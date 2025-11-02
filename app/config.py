"""Application configuration."""
from decouple import config

GITLAB_HOST = config("GITLAB_HOST", default="https://git.the-devs.com")

MONGO_URL = config(
    "MONGO_URL",
    default="mongodb://root:example@localhost:27017/"
)

CODE_PHRASE = config("CODE_PHRASE", default="trigger-bot")