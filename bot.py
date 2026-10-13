# =========================================================
#    🎭 VK PARODY BOT v2.0
#    TikTok + YouTube + Яндекс + Музыка + Роли
#    Автор проекта: Владелец сообщества 242268679
# =========================================================

import os
import json
import time
import random
import logging
import requests
import traceback
import subprocess
from datetime import datetime

from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.upload import VkUpload
from youtubesearchpython import VideosSearch
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# =========================================================
#                    НАСТРОЙКИ
# =========================================================
load_dotenv()

VK_TOKEN       = os.getenv("VK_TOKEN", "").strip()
GROUP_ID       = int(os.getenv("GROUP_ID", "242268679"))
OWNER_ID_ENV   = os.getenv("OWNER_ID", "").strip()
LOG_CHAT_ID    = os.getenv("LOG_CHAT_ID", "").strip()

DATA_FILE      = "data.json"
DOWNLOAD_DIR   = "downloads"
MUSIC_DIR      = "music"
MAX_FEED       = 10

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("PARODY")

# =========================================================
#                    ПРОВЕРКА ТОКЕНА (BotHost-совместимая)
# =========================================================
def verify_token() -> bool:
    """
    Проверяет токен ВК: наличие, валидность, права.
    Совместимо с BotHost — там переменные окружения
    подставляются автоматически.
    """
    print("=" * 60)
    print("🔐  ПРОВЕРКА ТОКЕНА VK (BotHost)")
    print("=" * 60)

    # 1. Наличие переменной
    if not VK_TOKEN:
        # BotHost может передавать через другие имена
        for alt in ("VK_BOT_TOKEN", "TOKEN", "BOT_TOKEN", "VK_GROUP_TOKEN"):
            val = os.getenv(alt, "").strip()
            if val:
                print(f"ℹ️  Найден токен в переменной {alt}, использую его.")
                globals()["VK_TOKEN"] = val
                return verify_token()
        print("❌ VK_TOKEN не найден ни в одной переменной окружения!")
        print("   Добавь VK_TOKEN в .env или в Environment на BotHost.")
        return False

    print(f"✅ VK_TOKEN найден (длина: {len(VK_TOKEN)} символов)")

    # 2. Проверяем соединение с API
    try:
        test_session = VkApi(token=VK_TOKEN)
        test_api = test_session.get_api()

        me = test_api.groups.getById(group_id=GROUP_ID)
        if me and isinstance(me, list):
            me = me[0]
        group_name = me.get("name", "?")
        print(f"✅ Подключён к сообществу: «{group_name}» (ID {GROUP_ID})")

        # 3. Проверяем права
        try:
            test_api.messages.getConversations(count=1)
            print("✅ Права на сообщения: ОК")
        except Exception as e:
            print(f"⚠️  Нет прав на сообщения: {e}")

        try:
            test_api.messages.getLongPollServer()
            print("✅ Long Poll API: включён")
        except Exception as e:
            print(f"❌ Long Poll не работает: {e}")
            print("   Включи Long Poll в настройках сообщества!")
            return False

        print("=" * 60)
        print("🚀  ВСЁ ГОТОВО К ЗАПУСКУ")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        return False


if not verify_token():
    raise SystemExit("❌ Проверка токена не пройдена. Исправь .env и попробуй снова.")

# =========================================================
#                    РАБОТА С ДАННЫМИ
# =========================================================
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "tiktok": {},
            "youtube": {},
            "roles": {
                "owner": [],         # главный владелец (группа 242268679)
                "developers": [],    # разработчики
                "admins": [],        # администраторы
                "moderators": [],    # модераторы
                "techs": [],         # тех. специалисты
            },
            "punishments": {},   # uid -> {"warns": 0, "mute_until": 0, "banned": False}
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # совместимость со старыми данными
    data.setdefault("roles", {"owner": [], "developers": [], "admins": [], "moderators": [], "techs": []})
    for r in ("owner", "developers", "admins", "moderators", "techs"):
        data["roles"].setdefault(r, [])
    data.setdefault("punishments", {})
    return data

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)

DATA = load_data()

# =========================================================
#                    РОЛИ
# =========================================================
ROLE_NAMES = {
    "owner":      "👑 Создатель",
    "developers": "💻 Разработчик",
    "admins":     "🛡️ Администратор",
    "moderators": "🔨 Модератор",
    "techs":      "🔧 Тех. специалист",
}

# Иерархия — кто выше кого
ROLE_POWER = {
    "owner":      5,
    "developers": 4,
    "admins":     3,
    "moderators": 2,
    "techs":      1,
    None:         0,
}

def get_user_roles(uid: int) -> list[str]:
    """Все роли пользователя."""
    return [r for r, ids in DATA["roles"].items() if uid in ids]

def get_top_role(uid: int) -> str | None:
    """Главная (высшая) роль пользователя."""
    roles = get_user_roles(uid)
    if not roles:
        return None
    return max(roles, key=lambda r: ROLE_POWER[r])

def has_role(uid: int, role: str) -> bool:
    return uid in DATA["roles"].get(role, [])

def has_at_least(uid: int, role: str) -> bool:
    """У пользователя есть роль не ниже указанной."""
    top = get_top_role(uid)
    return ROLE_POWER.get(top, 0) >= ROLE_POWER[role]

def is_staff(uid: int) -> bool:
    return get_top_role(uid) is not None

def is_group_owner(uid: int) -> bool:
    """Проверка: является ли пользователь создателем сообщества GROUP_ID."""
    try:
        # Кэшируем владельца группы на 10 минут
        global _GROUP_OWNER_CACHE
        try:
            cached_id, cached_ts = _GROUP_OWNER_CACHE
            if time.time() - cached_ts < 600:
                return cached_id == uid
        except Exception:
            pass

        # Получаем админов группы
        managers = vk.groups.getMembers(group_id=GROUP_ID, filter="managers")
        items = managers.get("items", [])
        owner_id = None
        for m in items:
            if m.get("role") == "creator":
                owner_id = m.get("id")
                break
        _GROUP_OWNER_CACHE = (owner_id, time.time())
        return owner_id == uid
    except Exception as e:
        log.warning(f"Не удалось получить владельца группы: {e}")
        return False

_GROUP_OWNER_CACHE = (None, 0)

def init_owner_from_env():
    """Если в .env указан OWNER_ID — добавляем его как создателя."""
    if OWNER_ID_ENV and OWNER_ID_ENV.isdigit():
        oid = int(OWNER_ID_ENV)
        if oid not in DATA["roles"]["owner"]:
            DATA["roles"]["owner"].append(oid)
            save_data()
            log.info(f"👑 Владелец из .env зарегистрирован: {oid}")

init_owner_from_env()

# =========================================================
#                    ИНИЦИАЛИЗАЦИЯ VK
# =========================================================
vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)
upload = VkUpload(vk_session)

# =========================================================
#                    ВСПОМОГАТЕЛЬНЫЕ
# =========================================================
def send(uid: int, text: str, attachment: str = None, keyboard: str = None, peer_id: int = None):
    try:
        vk.messages.send(
            user_id=uid if not peer_id else None,
            peer_id=peer_id,
            message=text[:4000],
            attachment=attachment,
            keyboard=keyboard,
            random_id=random.randint(1, 2**31),
        )
    except Exception as e:
        log.error(f"send error: {e}")

def log_event(text: str):
    """Пишет в лог-чат, если он настроен."""
    if not LOG_CHAT_ID:
        return
    try:
        vk.messages.send(
            peer_id=int(LOG_CHAT_ID),
            message=f"📝 {text}",
            random_id=random.randint(1, 2**31),
        )
    except Exception as e:
        log.warning(f"log_event error: {e}")

def short_id(prefix: str) -> str:
    return f"{prefix}{int(time.time()) % 100000}{random.randint(10, 99)}"

def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")

def get_user(uid: int) -> dict:
    uid_s = str(uid)
    if uid_s not in DATA["users"]:
        DATA["users"][uid_s] = {
            "tiktok": {
                "nick": f"user{random.randint(1000, 9999)}",
                "bio": "Люблю снимать видео 🎬",
                "subs": [], "videos": [],
            },
            "youtube": {
                "nick": f"channel{random.randint(1000, 9999)}",
                "bio": "Мой канал на YouTube ▶️",
                "subs": [], "videos": [],
            },
        }
        save_data()
    return DATA["users"][uid_s]

def get_punishment(uid: int) -> dict:
    uid_s = str(uid)
    if uid_s not in DATA["punishments"]:
        DATA["punishments"][uid_s] = {"warns": 0, "mute_until": 0, "banned": False}
        save_data()
    return DATA["punishments"][uid_s]

def parse_user_arg(arg: str) -> int | None:
    """Парсит id123, @nick или просто цифры."""
    arg = arg.strip()
    if arg.startswith("id"):
        arg = arg[2:]
    if arg.startswith("@"):
        try:
            r = vk.utils.resolveScreenName(screen_name=arg[1:])
            if r and r.get("type") == "user":
                return r["object_id"]
        except Exception:
            return None
    if arg.isdigit():
        return int(arg)
    return None

# =========================================================
#          СКАЧИВАНИЕ ВИДЕО / АУДИО
# =========================================================
def download_video(url: str) -> str | None:
    try:
        opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "quiet": True, "no_warnings": True,
            "format": "mp4/best[ext=mp4]/best",
            "noplaylist": True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if not os.path.exists(path):
                base, _ = os.path.splitext(path)
                for ext in (".mp4", ".mkv", ".webm", ".mov"):
                    if os.path.exists(base + ext):
                        return base + ext
            return path
    except Exception as e:
        log.error(f"download_video: {e}")
        return None

def download_music(query_or_url: str) -> tuple[str | None, str]:
    """Скачивает mp3 из YouTube. Возвращает (путь, название)."""
    try:
        opts = {
            "outtmpl": os.path.join(MUSIC_DIR, "%(id)s.%(ext)s"),
            "quiet": True, "no_warnings": True,
            "format": "bestaudio/best",
            "noplaylist": True,
            "default_search": "ytsearch1",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query_or_url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            base = os.path.join(MUSIC_DIR, info["id"])
            path = base + ".mp3"
            title = info.get("title", "Без названия")
            artist = info.get("uploader", "")
            return (path if os.path.exists(path) else None, f"{artist} — {title}" if artist else title)
    except Exception as e:
        log.error(f"download_music: {e}")
        return None, ""

def upload_video(video_path: str) -> str | None:
    try:
        v = upload.video(video_file=video_path, name="parody_clip")
        return f"video{v['owner_id']}_{v['video_id']}"
    except Exception as e:
        log.error(f"upload_video: {e}")
        return None

def upload_audio(mp3_path: str, title: str) -> str | None:
    """Загружает mp3 как документ (VK показывает его как аудио-файл)."""
    try:
        doc = upload.document(
            doc=mp3_path,
            title=title[:100],
            tags="music,bothmot",
        )
        if isinstance(doc, list):
            doc = doc[0]
        d = doc["doc"] if "doc" in doc else doc
        return f"doc{d['owner_id']}_{d['id']}"
    except Exception as e:
        log.error(f"upload_audio: {e}")
        return None

# =========================================================
#          ПОИСК YOUTUBE / ЯНДЕКС
# =========================================================
def real_youtube_search(query: str, limit: int = 5) -> list[dict]:
    try:
        return VideosSearch(query, limit=limit).result().get("result", [])
    except Exception as e:
        log.error(f"YT search: {e}")
        return []

def render_yt_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"😔 По запросу **{query}** ничего не найдено."
    text = f"🔎 **YouTube · «{query}»**\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, v in enumerate(results, 1):
        text += (
            f"{i}. **{v.get('title')}**\n"
            f"   ⏱️ {v.get('duration')} | 👁️ {v.get('viewCount', {}).get('short','—')}\n"
            f"   👤 {v.get('channel', {}).get('name','—')}\n"
            f"   🔗 {v.get('link')}\n\n"
        )
    return text

def yandex_search_parody(query: str) -> str:
    q = query.replace(" ", "+")
    tips = [
        "🤖 Яндекс думает... найдено 1 248 391 результатов за 0.032 сек.",
        "🔍 Яндекс нашёл кое-что интересное:",
        "📡 Яндекс просканировал интернет:",
        "🌐 Яндекс выдал топ-результаты:",
    ]
    return (
        f"{random.choice(tips)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔎 **Запрос:** {query}\n\n"
        f"1️⃣ **Поиск** → https://yandex.ru/search/?text={q}\n"
        f"2️⃣ **Картинки** → https://yandex.ru/images/search?text={q}\n"
        f"3️⃣ **Видео** → https://yandex.ru/video/search?text={q}\n"
        f"4️⃣ **Новости** → https://yandex.ru/news/search?text={q}\n"
        f"5️⃣ **Переводчик** → https://translate.yandex.ru/?text={q}\n\n"
        f"💡 *Яндекс — найдётся всё!*"
    )

# =========================================================
#          КАРТОЧКИ ВИДЕО / ЛЕНТА
# =========================================================
def render_video_card(platform: str, vid: str, viewer_id: int) -> tuple[str, str | None]:
    store = DATA[platform]
    if vid not in store:
        return "❌ Видео не найдено.", None
    v = store[vid]
    author = get_user(int(v["author_id"]))
    nick = author[platform]["nick"]
    liked = viewer_id in v["likes"]
    emoji = "🎵" if platform == "tiktok" else "▶️"
    name = "TikTok" if platform == "tiktok" else "YouTube"

    text = (
        f"{emoji} **{name} · {nick}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 **{v['title']}**\n"
        f"📅 {fmt_date(v['date'])}\n"
        f"👁️ {v['views']} | ❤️ {len(v['likes'])} {'(ты лайкнул)' if liked else ''} | 💬 {len(v['comments'])}\n"
        f"🆔 `{vid}`\n\n"
    )
    if v["comments"]:
        text += "💬 **Последние:**\n"
        for c in v["comments"][-3:]:
            ca = get_user(int(c["uid"]))[platform]["nick"]
            text += f"  • **{ca}**: {c['text']}\n"
    text += (
        f"\n`!{platform} лайк {vid}` · `!{platform} коммент {vid} <текст>` · `!{platform} лента`"
    )
    return text, v.get("attachment")

def render_feed(platform: str, page: int = 0) -> str:
    store = DATA[platform]
    if not store:
        return f"📭 Лента {platform} пуста. Залей первое видео: `!{platform} залить <ссылка> | <название>`"
    items = sorted(store.items(), key=lambda x: x[1]["date"], reverse=True)
    start = page * MAX_FEED
    chunk = items[start:start + MAX_FEED]
    emoji = "🎵" if platform == "tiktok" else "▶️"
    text = f"{emoji} **ЛЕНТА {'TikTok' if platform=='tiktok' else 'YouTube'}** (стр. {page+1})\n━━━━━━━━━━━━━━━━━━━━\n"
    for vid, v in chunk:
        a = get_user(int(v["author_id"]))[platform]["nick"]
        text += f"🆔 `{vid}` — **{v['title']}**\n   👤 {a} | ❤️ {len(v['likes'])} | 💬 {len(v['comments'])} | 👁️ {v['views']}\n"
    text += f"\nСмотреть: `!{platform} видео <id>` · Дальше: `!{platform} лента {page+1}`"
    return text

# =========================================================
#                    СПРАВКА
# =========================================================
HELP_TEXT = """🎭 **VK PARODY BOT v2.0 — TikTok + YouTube + Яндекс + Музыка**

━━━━━━━━━━━━━━━━━━━━
🎵 **TikTok**
`!тикток профиль [@ник]` — профиль
`!тикток ник <ник>` · `!тикток био <текст>`
`!тикток залить <ссылка> | <название>` — опубликовать
`!тикток лента [стр]` · `!тикток видео <id>`
`!тикток лайк <id>` · `!тикток коммент <id> <текст>`
`!тикток подписаться @ник` · `!тикток скачать <ссылка>`

▶️ **YouTube** — всё то же: `!ютуб ...`
`!ютуб поиск <запрос>` — реальный поиск на YouTube

🎼 **Музыка**
`!музыка <запрос>` — найти трек
`!музыка скачать <номер>` — скачать (из последних результатов)
`!мскачать <ссылка>` — скачать по ссылке

🔍 **Яндекс**
`!яндекс <запрос>` · `!яндекс картинки <запрос>` · `!яндекс видео <запрос>`

━━━━━━━━━━━━━━━━━━━━
🛡️ **Команды по ролям**

👑 **Создатель (owner)**
`!роль добавить <роль> <id/@>` · `!роль убрать <роль> <id/@>`
`!роль список` · `!создатель` (инфа)

💻 **Разработчик (dev)**
`!разраб exec <код>` — выполнить Python
`!разраб статус` — состояние бота
`!разраб save` · `!разраб load`

🛡️ **Админ**
`!админ кик <id>` · `!админ бан <id>` · `!админ разбан <id>`
`!админ роль <id> <роль>` — выдать роль (ниже своей)

🔨 **Модератор**
`!модер мут <id> <минуты>` · `!модер анмут <id>`
`!модер варн <id> <причина>` · `!модер варны <id>`
`!модер снять <id>` — снять все наказания

🔧 **Тех. специалист**
`!тех статус` — статус системы
`!тех логи` — последние логи
`!тех бэкап` — создать бэкап data.json
`!тех бэкапы` — список бэкапов
`!тех рестарт` — мягкий рестарт

🎲 **Для всех**
`!помощь` · `!пинг` · `!моя_роль` · `!мои_права`
"""

# =========================================================
#                    МУЗЫКА (сессия поиска)
# =========================================================
MUSIC_SESSIONS = {}  # uid -> {"query": str, "results": [ {title, url, duration} ], "ts": float}

def music_search(uid: int, query: str):
    send(uid, f"🎼 Ищу музыку: **{query}**...")
    results = real_youtube_search(query, limit=5)
    if not results:
        send(uid, "😔 Ничего не нашёл.")
        return
    MUSIC_SESSIONS[uid] = {"query": query, "results": results, "ts": time.time()}
    text = f"🎼 **Результаты по «{query}»**\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, v in enumerate(results, 1):
        text += f"{i}. **{v.get('title')}** — {v.get('duration')}\n"
    text += "\nСкачать: `!музыка скачать <номер>` (1-5)"
    send(uid, text)

def music_download_by_number(uid: int, num: int):
    sess = MUSIC_SESSIONS.get(uid)
    if not sess or time.time() - sess["ts"] > 1800:
        send(uid, "❌ Сначала найди трек: `!музыка <запрос>`")
        return
    if not (1 <= num <= len(sess["results"])):
        send(uid, "❌ Неверный номер.")
        return
    item = sess["results"][num - 1]
    url = item.get("link")
    send(uid, f"⏳ Скачиваю: **{item.get('title')}**...")
    path, title = download_music(url)
    if not path:
        send(uid, "❌ Не удалось скачать.")
        return
    att = upload_audio(path, title)
    try:
        os.remove(path)
    except Exception:
        pass
    if att:
        send(uid, f"🎵 **{title}**", attachment=att)
    else:
        send(uid, "❌ Не удалось загрузить в ВК.")

def music_download_url(uid: int, url: str):
    send(uid, "⏳ Скачиваю трек по ссылке...")
    path, title = download_music(url)
    if not path:
        send(uid, "❌ Не удалось скачать.")
        return
    att = upload_audio(path, title)
    try:
        os.remove(path)
    except Exception:
        pass
    if att:
        send(uid, f"🎵 **{title}**", attachment=att)
    else:
        send(uid, "❌ Не удалось загрузить в ВК.")

# =========================================================
#                    ОБРАБОТКА РОЛЕЙ
# =========================================================
def handle_role(uid: int, rest: str):
    top = get_top_role(uid)
    if not has_at_least(uid, "owner") and not is_group_owner(uid):
        send(uid, "❌ Только Создатель может управлять ролями.")
        return

    parts = rest.split()
    if not parts:
        send(uid, "Использование: `!роль добавить|убрать|список <роль> <id/@>`")
        return
    sub = parts[0].lower()

    if sub == "список":
        text = "👥 **СПИСОК РОЛЕЙ**\n━━━━━━━━━━━━━━━━━━━━\n"
        for r, ids in DATA["roles"].items():
            text += f"\n{ROLE_NAMES[r]} ({len(ids)}):\n"
            if not ids:
                text += "  • пусто\n"
            else:
                for i in ids[:10]:
                    try:
                        u = vk.users.get(user_ids=i)[0]
                        text += f"  • {u['first_name']} {u['last_name']} (id{i})\n"
                    except Exception:
                        text += f"  • id{i}\n"
        send(uid, text)
        return

    if len(parts) < 3:
        send(uid, "❌ Формат: `!роль добавить <роль> <id/@>`")
        return

    action, role = sub, parts[1].lower()
    target = parse_user_arg(parts[2])
    if target is None:
        send(uid, "❌ Не смог определить пользователя. Используй `id123` или `@nick`.")
        return
    if role not in DATA["roles"]:
        send(uid, f"❌ Роль `{role}` не существует. Доступные: {', '.join(DATA['roles'].keys())}")
        return

    if action in ("добавить", "add"):
        if target in DATA["roles"][role]:
            send(uid, f"ℹ️ Пользователь уже имеет роль {ROLE_NAMES[role]}.")
            return
        DATA["roles"][role].append(target)
        save_data()
        send(uid, f"✅ Пользователю id{target} выдана роль {ROLE_NAMES[role]}.")
        log_event(f"Владелец {uid} выдал {ROLE_NAMES[role]} пользователю id{target}")
        try:
            vk.messages.send(user_id=target, message=f"🎉 Тебе выдана роль: {ROLE_NAMES[role]}",
                             random_id=random.randint(1, 2**31))
        except Exception:
            pass
    elif action in ("убрать", "remove", "del"):
        if target not in DATA["roles"][role]:
            send(uid, f"ℹ️ У пользователя нет роли {ROLE_NAMES[role]}.")
            return
        DATA["roles"][role].remove(target)
        save_data()
        send(uid, f"✅ У id{target} убрана роль {ROLE_NAMES[role]}.")
        log_event(f"Владелец {uid} снял {ROLE_NAMES[role]} с id{target}")
    else:
        send(uid, "❌ Действие: добавить / убрать / список")

# =========================================================
#                    КОМАНДЫ ПО РОЛЯМ
# =========================================================
def handle_admin(uid: int, rest: str):
    if not has_at_least(uid, "admins"):
        send(uid, "❌ Нужна роль 🛡️ Администратор или выше.")
        return
    parts = rest.split(maxsplit=2)
    if not parts:
        send(uid, "Команды: `кик <id>` · `бан <id>` · `разбан <id>` · `роль <id> <роль>`")
        return
    sub = parts[0].lower()
    if sub == "кик" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid:
            send(uid, "❌ Укажи id/@."); return
        p = get_punishment(tid); p["kicked"] = True; save_data()
        send(uid, f"👢 «Кик» для id{tid} (в личке — просто пометка).")
        log_event(f"Админ {uid} кикнул id{tid}")
    elif sub == "бан" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid:
            send(uid, "❌ Укажи id/@."); return
        p = get_punishment(tid); p["banned"] = True; save_data()
        send(uid, f"🚫 id{tid} забанен в боте.")
        log_event(f"Админ {uid} забанил id{tid}")
    elif sub == "разбан" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid:
            send(uid, "❌ Укажи id/@."); return
        p = get_punishment(tid); p["banned"] = False; save_data()
        send(uid, f"✅ id{tid} разбанен.")
    elif sub == "роль" and len(parts) >= 3:
        tid = parse_user_arg(parts[1])
        role = parts[2].lower()
        if not tid or role not in DATA["roles"]:
            send(uid, "❌ Формат: `!админ роль id123 admins`")
            return
        if ROLE_POWER[role] >= ROLE_POWER[get_top_role(uid) or "techs"]:
            send(uid, "❌ Нельзя выдать роль, равную или выше своей.")
            return
        if tid not in DATA["roles"][role]:
            DATA["roles"][role].append(tid); save_data()
        send(uid, f"✅ id{tid} → {ROLE_NAMES[role]}")
    else:
        send(uid, "❌ Неизвестная команда.")


def handle_moder(uid: int, rest: str):
    if not has_at_least(uid, "moderators"):
        send(uid, "❌ Нужна роль 🔨 Модератор или выше.")
        return
    parts = rest.split(maxsplit=2)
    if not parts:
        send(uid, "Команды: `мут <id> <мин>` · `анмут <id>` · `варн <id> <причина>` · `варны <id>` · `снять <id>`")
        return
    sub = parts[0].lower()
    if sub == "мут" and len(parts) >= 3:
        tid = parse_user_arg(parts[1])
        try: minutes = int(parts[2])
        except: send(uid, "❌ Минуты — число."); return
        if not tid:
            send(uid, "❌ Укажи id/@."); return
        p = get_punishment(tid)
        p["mute_until"] = time.time() + minutes * 60
        save_data()
        send(uid, f"🔇 id{tid} замьючен на {minutes} мин.")
        log_event(f"Модер {uid} замутил id{tid} на {minutes}м")
    elif sub == "анмут" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid: send(uid, "❌ id/@"); return
        p = get_punishment(tid); p["mute_until"] = 0; save_data()
        send(uid, f"🔊 id{tid} размьючен.")
    elif sub == "варн" and len(parts) >= 3:
        tid = parse_user_arg(parts[1])
        reason = parts[2]
        if not tid: send(uid, "❌ id/@"); return
        p = get_punishment(tid); p["warns"] += 1; save_data()
        send(uid, f"⚠️ id{tid} получил предупреждение ({p['warns']}/3). Причина: {reason}")
        log_event(f"Модер {uid} выдал варн id{tid}: {reason}")
    elif sub == "варны" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid: send(uid, "❌ id/@"); return
        p = get_punishment(tid)
        send(uid, f"⚠️ id{tid}: варнов {p['warns']}/3, мут до {fmt_date(p['mute_until']) if p['mute_until']>time.time() else '—'}, бан: {'да' if p['banned'] else 'нет'}")
    elif sub == "снять" and len(parts) >= 2:
        tid = parse_user_arg(parts[1])
        if not tid: send(uid, "❌ id/@"); return
        DATA["punishments"][str(tid)] = {"warns": 0, "mute_until": 0, "banned": False}
        save_data()
        send(uid, f"🧹 С id{tid} сняты все наказания.")
    else:
        send(uid, "❌ Неизвестная команда.")


def handle_tech(uid: int, rest: str):
    if not has_at_least(uid, "techs"):
        send(uid, "❌ Нужна роль 🔧 Тех. специалист или выше.")
        return
    sub = rest.strip().lower()
    if sub == "статус":
        import platform, sys
        text = (
            "🔧 **СИСТЕМА**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🐍 Python: {sys.version.split()[0]}\n"
            f"💻 ОС: {platform.system()} {platform.release()}\n"
            f"⏱️ Аптайм процесса: {int(time.time() - START_TIME)} сек\n"
            f"👥 Пользователей: {len(DATA['users'])}\n"
            f"🎬 Видео TikTok/YT: {len(DATA['tiktok'])}/{len(DATA['youtube'])}\n"
            f"💾 Файл данных: {os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0} байт\n"
        )
        send(uid, text)
    elif sub == "логи":
        if os.path.exists("bot.log"):
            with open("bot.log", "r", encoding="utf-8") as f:
                tail = f.readlines()[-15:]
            send(uid, "📋 **Последние логи:**\n```\n" + "".join(tail)[-3500:] + "\n```")
        else:
            send(uid, "ℹ️ Лог-файл не ведётся. Включи: logging.FileHandler('bot.log')")
    elif sub == "бэкап":
        name = f"backup_{int(time.time())}.json"
        try:
            with open(name, "w", encoding="utf-8") as f:
                json.dump(DATA, f, ensure_ascii=False, indent=2)
            send(uid, f"💾 Бэкап создан: `{name}`")
        except Exception as e:
            send(uid, f"❌ Ошибка: {e}")
    elif sub == "бэкапы":
        files = sorted([f for f in os.listdir(".") if f.startswith("backup_") and f.endswith(".json")])
        if not files:
            send(uid, "📁 Бэкапов нет.")
        else:
            send(uid, "📁 **Бэкапы:**\n" + "\n".join(f"• `{f}`" for f in files[-10:]))
    elif sub == "рестарт":
        send(uid, "♻️ Мягкий рестарт... (в реальности на BotHost нужно перезапустить контейнер)")
    else:
        send(uid, "Команды: `статус` · `логи` · `бэкап` · `бэкапы` · `рестарт`")


def handle_dev(uid: int, rest: str):
    if not has_at_least(uid, "developers"):
        send(uid, "❌ Нужна роль 💻 Разработчик или выше.")
        return
    parts = rest.split(maxsplit=1)
    if not parts:
        send(uid, "Команды: `exec <код>` · `статус` · `save` · `load` · `ping_vk`")
        return
    sub = parts[0].lower()
    if sub == "exec" and len(parts) == 2:
        code = parts[1]
        # ⚠️ Безопасность: выполняем только владельцу
        if not has_at_least(uid, "owner"):
            send(uid, "❌ Только Создатель может запускать exec.")
            return
        try:
            # Разрешённые модули
            env = {"vk": vk, "DATA": DATA, "send": send, "save_data": save_data,
                   "random": random, "time": time, "os": os, "json": json}
            result = eval(code, {"__builtins__": __builtins__}, env)
            send(uid, f"✅ Результат:\n```\n{result}\n```")
        except Exception as e:
            send(uid, f"❌ Ошибка:\n```\n{e}\n```")
    elif sub == "статус":
        send(uid, f"💻 Разработчик-панель:\nДанные: {len(DATA['users'])} юзеров, "
                  f"{len(DATA['tiktok'])} TikTok, {len(DATA['youtube'])} YouTube.")
    elif sub == "save":
        save_data(); send(uid, "💾 Данные сохранены.")
    elif sub == "load":
        global DATA
        DATA = load_data()
        send(uid, "📥 Данные перезагружены.")
    elif sub == "ping_vk":
        t0 = time.time()
        try:
            vk.users.get(user_ids=1)
            send(uid, f"🏓 VK API: {int((time.time()-t0)*1000)} мс")
        except Exception as e:
            send(uid, f"❌ VK API: {e}")
    else:
        send(uid, "❌ Неизвестная команда.")


# =========================================================
#                    ОБРАБОТЧИК ПЛАТФОРМ
# =========================================================
def handle_platform(uid: int, platform: str, rest: str):
    user = get_user(uid)
    acc = user[platform]
    name = "TikTok" if platform == "tiktok" else "YouTube"
    emoji = "🎵" if platform == "tiktok" else "▶️"

    if not rest:
        send(uid, f"{emoji} Команды: `лента`, `залить`, `профиль`, `видео <id>`, `лайк <id>`, `коммент <id> текст`")
        return

    action, _, args = rest.partition(" ")
    action = action.lower()
    args = args.strip()

    if action in ("профиль", "profile", "я"):
        target_uid = uid
        if args:
            nick = args.lstrip("@").lower()
            for u_id, u in DATA["users"].items():
                if u[platform]["nick"].lower() == nick:
                    target_uid = int(u_id); break
            else:
                send(uid, f"❌ Автор `{args}` не найден."); return
        t = get_user(target_uid)[platform]
        text = (f"{emoji} **{name} · Профиль**\n"
                f"👤 Ник: **{t['nick']}**\n"
                f"📝 Био: {t['bio']}\n"
                f"👥 Подписчиков: {len(t['subs'])}\n"
                f"🎬 Видео: {len(t['videos'])}\n")
        if target_uid == uid:
            text += f"\n`!{platform} ник <ник>` · `!{platform} био <текст>`"
        send(uid, text); return

    if action in ("ник", "nick"):
        if not args:
            send(uid, "❌ Пример: `!тикток ник coolguy`"); return
        new_nick = args.replace(" ", "")[:20]
        for u_id, u in DATA["users"].items():
            if u[platform]["nick"].lower() == new_nick.lower() and int(u_id) != uid:
                send(uid, f"❌ Ник занят."); return
        acc["nick"] = new_nick; save_data()
        send(uid, f"✅ Ник: **{new_nick}**"); return

    if action in ("био", "bio", "описание"):
        if not args:
            send(uid, "❌ Пример: `!тикток био Я снимаю`"); return
        acc["bio"] = args[:150]; save_data()
        send(uid, "✅ Био обновлено."); return

    if action in ("залить", "upload", "выложить", "опубликовать"):
        if not args:
            send(uid, f"❌ Формат: `!{platform} залить <ссылка> | <название>`"); return
        if "|" in args:
            url, title = [x.strip() for x in args.split("|", 1)]
        else:
            url, title = args.strip(), "Без названия"
        if not url.startswith("http"):
            send(uid, "❌ URL должен начинаться с http."); return
        send(uid, f"⏳ Скачиваю для {name}...")
        path = download_video(url)
        attachment = None
        if path:
            send(uid, "📤 Загружаю в ВК...")
            attachment = upload_video(path)
            try: os.remove(path)
            except: pass
        vid = short_id("v")
        DATA[platform][vid] = {
            "author_id": str(uid), "title": title[:100], "url": url,
            "likes": [], "comments": [], "views": 0,
            "date": time.time(), "attachment": attachment,
        }
        acc["videos"].append(vid); save_data()
        send(uid, f"✅ Опубликовано! `{vid}` — **{title}**", attachment=attachment)
        return

    if action in ("лента", "feed", "топ"):
        page = int(args) if args.isdigit() else 0
        send(uid, render_feed(platform, page)); return

    if action in ("видео", "смотреть", "watch"):
        if not args:
            send(uid, f"❌ Пример: `!{platform} видео v123`"); return
        vid = args.strip()
        if vid not in DATA[platform]:
            send(uid, "❌ Не найдено."); return
        DATA[platform][vid]["views"] += 1; save_data()
        text, att = render_video_card(platform, vid, uid)
        send(uid, text, attachment=att); return

    if action in ("лайк", "like", "❤️"):
        if not args:
            send(uid, f"❌ `!{platform} лайк <id>`"); return
        vid = args.strip()
        if vid not in DATA[platform]:
            send(uid, "❌ Не найдено."); return
        likes = DATA[platform][vid]["likes"]
        if uid in likes:
            likes.remove(uid); send(uid, f"💔 Лайк снят с `{vid}`")
        else:
            likes.append(uid); send(uid, f"❤️ Лайк `{vid}`")
        save_data(); return

    if action in ("коммент", "комментарий", "comment"):
        if " " not in args:
            send(uid, f"❌ `!{platform} коммент <id> <текст>`"); return
        vid, _, ctext = args.partition(" ")
        vid = vid.strip(); ctext = ctext.strip()
        if not ctext or vid not in DATA[platform]:
            send(uid, "❌ Неверные данные."); return
        DATA[platform][vid]["comments"].append({"uid": str(uid), "text": ctext[:200], "date": time.time()})
        save_data(); send(uid, f"💬 Комментарий добавлен к `{vid}`"); return

    if action in ("подписаться", "sub", "подписка"):
        if not args:
            send(uid, f"❌ `!{platform} подписаться @ник`"); return
        nick = args.lstrip("@").lower()
        for u_id, u in DATA["users"].items():
            if u[platform]["nick"].lower() == nick:
                target = int(u_id); break
        else:
            send(uid, f"❌ Автор не найден."); return
        if target == uid:
            send(uid, "❌ Нельзя на себя."); return
        t = get_user(target)[platform]
        if uid in t["subs"]:
            t["subs"].remove(uid); send(uid, f"➖ Отписался от **{t['nick']}**")
        else:
            t["subs"].append(uid); send(uid, f"➕ Подписан на **{t['nick']}**!")
        save_data(); return

    if action in ("скачать", "download"):
        if not args or not args.startswith("http"):
            send(uid, f"❌ `!{platform} скачать https://...`"); return
        send(uid, "⏳ Скачиваю...")
        path = download_video(args.strip())
        if not path:
            send(uid, "❌ Не удалось."); return
        att = upload_video(path)
        try: os.remove(path)
        except: pass
        send(uid, "✅ Держи!" if att else "❌ Ошибка загрузки.", attachment=att); return

    if platform == "youtube" and action in ("поиск", "search", "найти"):
        if not args:
            send(uid, "❌ `!ютуб поиск <запрос>`"); return
        send(uid, f"🔎 Ищу: **{args}**...")
        send(uid, render_yt_results(args, real_youtube_search(args, limit=5))); return

    send(uid, f"🤔 Неизвестное действие `{action}` для {name}.")


# =========================================================
#                    ГЛАВНЫЙ ОБРАБОТЧИК
# =========================================================
START_TIME = time.time()

def handle(uid: int, text: str):
    text = text.strip()
    if not text:
        return

    # Проверка на бан
    p = DATA["punishments"].get(str(uid))
    if p and p.get("banned"):
        send(uid, "🚫 Ты забанен в боте. Обратись к администрации.")
        return

    user = get_user(uid)
    low = text.lower()

    # ---------- Общие ----------
    if low in ("!помощь", "!help", "!start", "начать", "привет", "/start"):
        send(uid, HELP_TEXT); return
    if low in ("!пинг", "пинг"):
        send(uid, "🏓 Понг! Бот жив."); return

    if low in ("!моя_роль", "!мояроль", "!myrole"):
        roles = get_user_roles(uid)
        if not roles:
            send(uid, "👤 Ты обычный пользователь.")
        else:
            send(uid, "🎖️ Твои роли:\n" + "\n".join(f"• {ROLE_NAMES[r]}" for r in roles))
        return

    if low in ("!мои_права", "!права"):
        top = get_top_role(uid)
        send(uid, f"🎖️ Твоя высшая роль: {ROLE_NAMES.get(top, '👤 Пользователь')}")
        return

    if low in ("!создатель", "!owner"):
        owner_ids = DATA["roles"]["owner"]
        text_out = f"👑 Создатель: группа https://vk.com/club{GROUP_ID}\n"
        if owner_ids:
            try:
                u = vk.users.get(user_ids=owner_ids[0])[0]
                text_out += f"Пользователь: {u['first_name']} {u['last_name']} (id{owner_ids[0]})"
            except Exception:
                text_out += f"id{owner_ids[0]}"
        send(uid, text_out); return

    # ---------- Роли ----------
    if low.startswith("!роль ") or low == "!роль":
        handle_role(uid, text.split(" ", 1)[1] if " " in text else "")
        return

    if low.startswith("!админ ") or low == "!админ":
        handle_admin(uid, text.split(" ", 1)[1] if " " in text else "")
        return

    if low.startswith("!модер ") or low == "!модер":
        handle_moder(uid, text.split(" ", 1)[1] if " " in text else "")
        return

    if low.startswith("!тех ") or low == "!тех":
        handle_tech(uid, text.split(" ", 1)[1] if " " in text else "")
        return

    if low.startswith("!разраб ") or low == "!разраб":
        handle_dev(uid, text.split(" ", 1)[1] if " " in text else "")
        return

    # ---------- Музыка ----------
    if low.startswith("!музыка"):
        parts = text.split(" ", 2)
        if len(parts) == 1:
            send(uid, "🎼 `!музыка <запрос>` — найти трек\n`!музыка скачать <номер>` — скачать")
            return
        if parts[1].lower() == "скачать":
            if len(parts) < 3 or not parts[2].strip().isdigit():
                send(uid, "❌ `!музыка скачать <номер 1-5>`"); return
            music_download_by_number(uid, int(parts[2])); return
        music_search(uid, " ".join(parts[1:])); return

    if low.startswith("!мскачать"):
        url = text[len("!мскачать"):].strip()
        if not url.startswith("http"):
            send(uid, "❌ `!мскачать <ссылка>`"); return
        music_download_url(uid, url); return

    # ---------- Платформы ----------
    platforms = {"тикток": "tiktok", "tiktok": "tiktok", "тт": "tiktok",
                 "ютуб": "youtube", "youtube": "youtube", "yt": "youtube"}
    cmd, _, rest = text.partition(" ")
    cmd_low = cmd.lower().lstrip("!")
    if cmd_low in platforms:
        handle_platform(uid, platforms[cmd_low], rest.strip()); return

    # ---------- Яндекс ----------
    if low.startswith("!яндекс") or low.startswith("яндекс"):
        query = text.split(" ", 1)[1] if " " in text else ""
        if not query:
            send(uid, "❌ `!яндекс <запрос>`"); return
        if query.lower().startswith("картинки"):
            q = query[8:].strip().replace(" ", "+")
            send(uid, f"🖼️ https://yandex.ru/images/search?text={q}"); return
        if query.lower().startswith("видео"):
            q = query[5:].strip().replace(" ", "+")
            send(uid, f"📹 https://yandex.ru/video/search?text={q}"); return
        send(uid, yandex_search_parody(query)); return

    send(uid, "🤔 Не понял. Напиши `!помощь`.")


# =========================================================
#                    ЗАПУСК
# =========================================================
def main():
    log.info("🎭 VK PARODY BOT v2.0 запущен. Слушаю сообщения...")
    log.info(f"👑 Создатель группы: https://vk.com/club{GROUP_ID}")
    for event in longpoll.listen():
        if event.type != VkEventType.MESSAGE_NEW or not event.to_me:
            continue
        uid = event.user_id
        text = event.text or ""
        if not text.strip():
            continue
        try:
            handle(uid, text)
        except Exception as e:
            log.error(f"handle error: {e}\n{traceback.format_exc()}")
            send(uid, "⚠️ Ошибка. Попробуй позже.")


if __name__ == "__main__":
    main()
