import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    owner_id: int
    bot_username: str
    ping_chat_id: int       # Канал (для бэкапов)
    
    # Основные группы
    admin_group_id: int     # SYNTH Admin (менеджеры + бот, режим форума)
    support_group_id: int   # SYNTH Support (хелперы + бот)
    ceo_group_id: int       # SYNTH CEO (только ты + бот, режим форума)
    
    # Командные группы (разработчики)
    team_heavy_id: int      # SYNTH Team Heavy
    team_medium1_id: int    # SYNTH Team Medium 1
    team_medium2_id: int    # SYNTH Team Medium 2
    team_fast1_id: int      # SYNTH Team Fast 1
    team_fast2_id: int      # SYNTH Team Fast 2
    team_fast3_id: int      # SYNTH Team Fast 3
    
    db_path: str


def _load() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан")

    owner_id_raw = os.getenv("OWNER_ID", "").strip()
    if not owner_id_raw:
        raise RuntimeError("OWNER_ID не задан")
    owner_id = int(owner_id_raw)

    bot_username = os.getenv("BOT_USERNAME", "").strip()
    if not bot_username:
        raise RuntimeError("BOT_USERNAME не задан")

    ping_chat_id_raw = os.getenv("PING_CHAT_ID", "").strip()
    if not ping_chat_id_raw:
        raise RuntimeError("PING_CHAT_ID не задан")
    ping_chat_id = int(ping_chat_id_raw)

    # Заглушки. Реальные ID добавим в Railway в самом конце.
    admin_group_id = int(os.getenv("ADMIN_GROUP_ID", "-1009999999999"))
    support_group_id = int(os.getenv("SUPPORT_GROUP_ID", "-1009999999999"))
    ceo_group_id = int(os.getenv("CEO_GROUP_ID", "-1009999999999"))
    
    team_heavy_id = int(os.getenv("TEAM_HEAVY_ID", "-1009999999999"))
    team_medium1_id = int(os.getenv("TEAM_MEDIUM1_ID", "-1009999999999"))
    team_medium2_id = int(os.getenv("TEAM_MEDIUM2_ID", "-1009999999999"))
    team_fast1_id = int(os.getenv("TEAM_FAST1_ID", "-1009999999999"))
    team_fast2_id = int(os.getenv("TEAM_FAST2_ID", "-1009999999999"))
    team_fast3_id = int(os.getenv("TEAM_FAST3_ID", "-1009999999999"))

    data_dir = os.getenv("DATA_DIR", "data").strip()
    db_path = os.path.join(data_dir, "bot.db")

    return Config(
        bot_token=bot_token,
        owner_id=owner_id,
        bot_username=bot_username,
        ping_chat_id=ping_chat_id,
        admin_group_id=admin_group_id,
        support_group_id=support_group_id,
        ceo_group_id=ceo_group_id,
        team_heavy_id=team_heavy_id,
        team_medium1_id=team_medium1_id,
        team_medium2_id=team_medium2_id,
        team_fast1_id=team_fast1_id,
        team_fast2_id=team_fast2_id,
        team_fast3_id=team_fast3_id,
        db_path=db_path,
    )


config = _load()
