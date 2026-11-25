import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    bot_username: str = os.getenv("BOT_USERNAME", "Synthmanager_bot")
    owner_id: int = int(os.getenv("OWNER_ID", 0))
    ceo_group_id: int = int(os.getenv("CEO_GROUP_ID", 0))
    vk_token: str = os.getenv("VK_TOKEN", "")
    vk_group_id: int = int(os.getenv("VK_GROUP_ID", 0))
    db_path: str = os.getenv("DB_PATH", "/app/data/bot.db")

def load_config() -> Config:
    return Config()

config = load_config()
