import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    bot_token: str
    owner_id: int
    bot_username: str
    ping_chat_id: int       # Канал для отчетов раз в 3 дня и бэкапов
    admin_group_id: int     # Группа SYNTH Admin для менеджеров и общих заявок
    ceo_group_id: int       # Группа SYNTH CEO только для тебя (финансы, опасные действия, партнеры)
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

    admin_group_id_raw = os.getenv("ADMIN_GROUP_ID", "").strip()
    if not admin_group_id_raw:
        raise RuntimeError("ADMIN_GROUP_ID не задан")
    admin_group_id = int(admin_group_id_raw)

    ceo_group_id_raw = os.getenv("CEO_GROUP_ID", "").strip()
    if not ceo_group_id_raw:
        raise RuntimeError("CEO_GROUP_ID не задан")
    ceo_group_id = int(ceo_group_id_raw)

    data_dir = os.getenv("DATA_DIR", "data").strip()
    db_path = os.path.join(data_dir, "bot.db")

    return Config(
        bot_token=bot_token,
        owner_id=owner_id,
        bot_username=bot_username,
        ping_chat_id=ping_chat_id,
        admin_group_id=admin_group_id,
        ceo_group_id=ceo_group_id,
        db_path=db_path,
    )

config = _load()
