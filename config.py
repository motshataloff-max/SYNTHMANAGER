import os
from dataclasses import dataclass

@dataclass
class Config:
    # Telegram
    bot_token: str
    owner_id: int
    bot_username: str
    
    # ВКонтакте
    vk_token: str
    vk_group_id: int
    
    # ID групп
    admin_group_id: int
    support_group_id: int
    ceo_group_id: int
    ping_chat_id: int
    
    # Команды
    team_heavy_id: int
    team_medium1_id: int
    team_medium2_id: int
    team_fast1_id: int
    team_fast2_id: int
    team_fast3_id: int
    
    # База данных
    db_path: str

def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения"""
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        owner_id=int(os.getenv("OWNER_ID", "0")),
        bot_username=os.getenv("BOT_USERNAME", ""),
        
        vk_token=os.getenv("VK_TOKEN", ""),
        vk_group_id=int(os.getenv("VK_GROUP_ID", "0")),
        
        admin_group_id=int(os.getenv("ADMIN_GROUP_ID", "0")),
        support_group_id=int(os.getenv("SUPPORT_GROUP_ID", "0")),
        ceo_group_id=int(os.getenv("CEO_GROUP_ID", "0")),
        ping_chat_id=int(os.getenv("PING_CHAT_ID", "0")),
        
        team_heavy_id=int(os.getenv("TEAM_HEAVY_ID", "0")),
        team_medium1_id=int(os.getenv("TEAM_MEDIUM1_ID", "0")),
        team_medium2_id=int(os.getenv("TEAM_MEDIUM2_ID", "0")),
        team_fast1_id=int(os.getenv("TEAM_FAST1_ID", "0")),
        team_fast2_id=int(os.getenv("TEAM_FAST2_ID", "0")),
        team_fast3_id=int(os.getenv("TEAM_FAST3_ID", "0")),
        
        db_path=os.getenv("DB_PATH", "data/bot.db")
    )

config = load_config()
