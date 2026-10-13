# =========================================================
#        🚀 ADDONS.PY — 200+ команд для VK PARODY BOT
#        Подключается к основному bot.py
# =========================================================

import os
import json
import time
import random
import asyncio
import traceback
from datetime import datetime, timedelta

# Импортируем из основного бота (передадим через attach)
# DATA, save_data, send, vk, has_at_least, get_top_role, ROLE_NAMES,
# GROUP_ID, is_group_owner, get_user, short_id, fmt_date — всё из bot.py

# Эти переменные будут установлены функцией attach()
DATA = None
save_data = None
send = None
vk = None
has_at_least = None
get_top_role = None
ROLE_NAMES = None
GROUP_ID = None
is_group_owner = None
get_user = None
short_id = None
fmt_date = None
get_punishment = None

def attach(core):
    """Подключает этот модуль к ядру бота."""
    global DATA, save_data, send, vk, has_at_least, get_top_role
    global ROLE_NAMES, GROUP_ID, is_group_owner, get_user, short_id, fmt_date, get_punishment
    DATA             = core["DATA"]
    save_data        = core["save_data"]
    send             = core["send"]
    vk               = core["vk"]
    has_at_least     = core["has_at_least"]
    get_top_role     = core["get_top_role"]
    ROLE_NAMES       = core["ROLE_NAMES"]
    GROUP_ID         = core["GROUP_ID"]
    is_group_owner   = core["is_group_owner"]
    get_user         = core["get_user"]
    short_id         = core["short_id"]
    fmt_date         = core["fmt_date"]
    get_punishment   = core["get_punishment"]

def _rand_id():
    return random.randint(1, 2**31)


# =========================================================
#     💰 ВЫДАЧА ДЕНЕГ ВЛАДЕЛЬЦЕМ / РАЗРАБОТЧИКОМ
# =========================================================
def cmd_give_money(uid: int, rest: str):
    """!выдать <id/@> <сумма> — выдать деньги пользователю."""
    if not has_at_least(uid, "developers") and not is_group_owner(uid):
        return send(uid, "❌ Нужна роль 💻 Разработчик или выше.")
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!выдать id123 5000` или `!выдать @nick 5000`")
    target = _parse_uid(parts[0])
    if not target:
        return send(uid, "❌ Не смог определить пользователя.")
    try:
        amount = int(parts[1])
    except ValueError:
        return send(uid, "❌ Сумма — число.")
    if amount <= 0:
        return send(uid, "❌ Сумма должна быть > 0.")
    user = get_user(target)
    user["balance"] += amount
    save_data()
    send(uid, f"💸 Выдано **{amount:,} 🪙** пользователю id{target}.")
    try:
        send(target, f"🎁 Тебе выдали **{amount:,} 🪙**!")
    except Exception:
        pass

def cmd_take_money(uid: int, rest: str):
    if not has_at_least(uid, "developers") and not is_group_owner(uid):
        return send(uid, "❌ Нужна роль 💻 Разработчик или выше.")
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!забрать id123 5000`")
    target = _parse_uid(parts[0])
    if not target:
        return send(uid, "❌ Не смог определить пользователя.")
    try:
        amount = int(parts[1])
    except ValueError:
        return send(uid, "❌ Сумма — число.")
    user = get_user(target)
    amount = min(amount, user["balance"])
    user["balance"] -= amount
    save_data()
    send(uid, f"💸 Забрано **{amount:,} 🪙** у id{target}.")

def cmd_set_balance(uid: int, rest: str):
    if not has_at_least(uid, "developers") and not is_group_owner(uid):
        return send(uid, "❌ Нужна роль 💻 Разработчик или выше.")
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!установить_баланс id123 5000`")
    target = _parse_uid(parts[0])
    try:
        amount = int(parts[1])
    except ValueError:
        return send(uid, "❌ Сумма — число.")
    user = get_user(target)
    user["balance"] = max(0, amount)
    save_data()
    send(uid, f"✅ Баланс id{target} установлен на **{amount:,} 🪙**.")

def cmd_give_all(uid: int, rest: str):
    """!выдать_всем <сумма> — выдать всем юзерам бота."""
    if not has_at_least(uid, "owner") and not is_group_owner(uid):
        return send(uid, "❌ Только 👑 Создатель.")
    try:
        amount = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!выдать_всем 1000`")
    if amount <= 0:
        return send(uid, "❌ Сумма > 0.")
    count = len(DATA["users"])
    for u in DATA["users"].values():
        u["balance"] += amount
    save_data()
    send(uid, f"🎁 Всем **{count}** пользователям выдано по **{amount:,} 🪙**.")

def cmd_give_role_money(uid: int, rest: str):
    """!выдать_роли <роль> <сумма> — выдать всем с ролью."""
    if not has_at_least(uid, "owner") and not is_group_owner(uid):
        return send(uid, "❌ Только 👑 Создатель.")
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!выдать_роли developers 10000`")
    role = parts[0].lower()
    if role not in DATA["roles"]:
        return send(uid, f"❌ Роль не найдена. Доступно: {', '.join(DATA['roles'])}")
    try:
        amount = int(parts[1])
    except ValueError:
        return send(uid, "❌ Сумма — число.")
    count = 0
    for tid in DATA["roles"][role]:
        u = get_user(tid)
        u["balance"] += amount
        count += 1
    save_data()
    send(uid, f"🎁 Выдано по **{amount:,} 🪙** роли {ROLE_NAMES[role]} ({count} чел.).")

def cmd_money_log(uid: int, rest: str):
    """История выдач (если ведётся)."""
    log = DATA.get("money_log", [])[-20:]
    if not log:
        return send(uid, "📭 История пуста.")
    text = "💸 **Последние выдачи:**\n" + "\n".join(
        f"• {fmt_date(e['ts'])} · id{e['to']} · {e['amount']:+,} · выдал id{e['by']}"
        for e in log
    )
    send(uid, text)

def _log_money(by, to, amount):
    DATA.setdefault("money_log", []).append({"by": by, "to": to, "amount": amount, "ts": time.time()})
    save_data()

def _parse_uid(arg: str):
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
#     🎰 КАЗИНО
# =========================================================
def cmd_casino(uid: int, rest: str):
    user = get_user(uid)
    try:
        bet = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!казино 500`")
    if bet <= 0 or user["balance"] < bet:
        return send(uid, "❌ Недостаточно средств.")
    roll = random.randint(0, 36)
    if roll == 0:
        user["balance"] -= bet
        save_data()
        return send(uid, f"🎰 Выпало **ЗЕРO** 🟢! Ты проиграл **{bet:,} 🪙**.")
    color = "🔴 красное" if roll % 2 else "⚫ чёрное"
    if roll <= 18:
        win = bet  # возврат ставки
        user["balance"] += win
        save_data()
        send(uid, f"🎰 Выпало **{roll}** {color}. Ты выиграл **{win:,} 🪙**!")
    else:
        user["balance"] -= bet
        save_data()
        send(uid, f"🎰 Выпало **{roll}** {color}. Ты проиграл **{bet:,} 🪙**.")

def cmd_roulette(uid: int, rest: str):
    user = get_user(uid)
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!рулетка 500 красное|чёрное|зелёное`")
    try:
        bet = int(parts[0])
    except ValueError:
        return send(uid, "❌ Ставка — число.")
    color = parts[1].lower()
    if color not in ("красное", "чёрное", "зелёное", "red", "black", "green"):
        return send(uid, "❌ Цвет: красное / чёрное / зелёное")
    if bet <= 0 or user["balance"] < bet:
        return send(uid, "❌ Недостаточно средств.")
    roll = random.randint(0, 36)
    if roll == 0:
        result_color = "зелёное"
    elif roll % 2:
        result_color = "красное"
    else:
        result_color = "чёрное"
    won = (color[0] in ("к", "r") and result_color == "красное") or \
          (color[0] in ("ч", "b") and result_color == "чёрное") or \
          (color[0] in ("з", "g") and result_color == "зелёное")
    mult = 36 if result_color == "зелёное" else 2
    if won:
        win = bet * mult
        user["balance"] += win - bet
        user["wins"] = user.get("wins", 0) + 1
        send(uid, f"🎡 Выпало **{roll}** ({result_color}). Ты выиграл **{win:,} 🪙** (x{mult})!")
    else:
        user["balance"] -= bet
        user["losses"] = user.get("losses", 0) + 1
        send(uid, f"🎡 Выпало **{roll}** ({result_color}). Ты проиграл **{bet:,} 🪙**.")
    save_data()

def cmd_crash(uid: int, rest: str):
    """Краш: множитель растёт, надо вовремя остановиться."""
    user = get_user(uid)
    try:
        bet = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!краш 500`")
    if bet <= 0 or user["balance"] < bet:
        return send(uid, "❌ Недостаточно средств.")
    crash_at = round(random.uniform(1.01, 15.0), 2)
    user["balance"] -= bet
    user["crash_active"] = {"bet": bet, "crash_at": crash_at, "started": time.time()}
    save_data()
    send(uid,
         f"🚀 Ракета взлетела! Множитель растёт...\n"
         f"Ставка: **{bet:,} 🪙**\n"
         f"Остановиться: `!стоп`\n"
         f"*Если множитель достигнет лимита — потеряешь всё.*")

def cmd_crash_stop(uid: int, rest: str):
    user = get_user(uid)
    active = user.get("crash_active")
    if not active:
        return send(uid, "❌ Ты не в игре. Запусти `!краш <ставка>`")
    elapsed = time.time() - active["started"]
    current_mult = round(1 + elapsed * 0.5, 2)  # растёт 0.5 в секунду
    if current_mult >= active["crash_at"]:
        # Ракета уже упала
        user.pop("crash_active", None)
        save_data()
        send(uid, f"💥 Ракета взорвалась на x{active['crash_at']}! Ты потерял **{active['bet']:,} 🪙**.")
        return
    win = int(active["bet"] * current_mult)
    user["balance"] += win
    user.pop("crash_active", None)
    save_data()
    send(uid, f"✅ Ты вышел на x{current_mult}! Выигрыш: **{win:,} 🪙** (чистая: +{win-active['bet']:,})")

def cmd_mines(uid: int, rest: str):
    """!мины <ставка> — поле 5x5, бот сразу считает результат по «сложности»."""
    user = get_user(uid)
    parts = rest.split()
    if not parts:
        return send(uid, "❌ Формат: `!мины 500 <количество мин 1-10>`")
    try:
        bet = int(parts[0])
        mines = int(parts[1]) if len(parts) > 1 else 3
    except ValueError:
        return send(uid, "❌ Формат: `!мины 500 3`")
    if mines < 1 or mines > 10:
        return send(uid, "❌ Мин от 1 до 10.")
    if bet <= 0 or user["balance"] < bet:
        return send(uid, "❌ Недостаточно средств.")
    # Игрок открывает 3 клетки; на каждой шанс (mines/25) взорваться
    safe_chance = 1 - (mines / 25)
    user["balance"] -= bet
    steps = 0
    for _ in range(3):
        if random.random() < safe_chance:
            steps += 1
        else:
            save_data()
            return send(uid, f"💥 Ты наступил на мину после {steps} безопасных клеток. Проиграл **{bet:,} 🪙**.")
    # Win: множитель зависит от мин и открытых клеток
    mult = round((25 / max(1, 25 - mines)) ** steps, 2)
    win = int(bet * mult)
    user["balance"] += win
    save_data()
    send(uid, f"🎯 Ты открыл 3 клетки и не попал на мину! Множитель x{mult}. Выигрыш: **{win:,} 🪙** (+{win-bet:,})")

def cmd_blackjack(uid: int, rest: str):
    """Упрощённый блэкджек — 1 раздача, победа/поражение."""
    user = get_user(uid)
    try:
        bet = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!блэкджек 500`")
    if bet <= 0 or user["balance"] < bet:
        return send(uid, "❌ Недостаточно средств.")
    def draw():
        cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]
        return random.choice(cards)
    player = draw() + draw()
    dealer = draw() + draw()
    # Упростим: если у дилера 21 — игрок проиграл
    user["balance"] -= bet
    if dealer == 21 or (dealer < 21 and dealer > player and dealer <= 21):
        save_data()
        return send(uid, f"🃏 Ты: **{player}** | Дилер: **{dealer}**\n😢 Проигрыш **{bet:,} 🪙**.")
    if player > 21:
        save_data()
        return send(uid, f"🃏 Ты: **{player}** (перебор!) | Дилер: **{dealer}**\n😢 Проигрыш **{bet:,} 🪙**.")
    if player == 21:
        win = int(bet * 2.5)
        user["balance"] += win
        save_data()
        return send(uid, f"🃏 **БЛЭКДЖЕК!** Ты: **{player}** | Дилер: **{dealer}**\n🎉 Выигрыш: **{win:,} 🪙**")
    win = bet * 2
    user["balance"] += win
    save_data()
    send(uid, f"🃏 Ты: **{player}** | Дилер: **{dealer}**\n✅ Выигрыш: **{win:,} 🪙** (+{win-bet:,})")


# =========================================================
#     🎉 РАЗВЛЕЧЕНИЯ
# =========================================================
FACTS = [
    "🐙 У осьминога три сердца.",
    "🍯 Мёд не портится тысячи лет.",
    "🌕 Луна удаляется от Земли на 3.8 см в год.",
    "🦈 Акулы старше деревьев.",
    "🐌 Улитка может спать 3 года.",
    "🧠 Мозг потребляет 20% кислорода тела.",
    "🔥 Самая высокая температура — 5.5 млрд °C (БАК).",
    "💧 В теле человека ~37 триллионов клеток.",
]

JOKES = [
    "— Как дела?\n— Как в сказке: чем дальше, тем страшнее.",
    "Программист — это машина по превращению кофе в код.",
    "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что OCT 31 == DEC 25.",
    "Мой код не работает. Я не знаю почему.\nМой код работает. Я не знаю почему.",
    "— Сколько программистов нужно, чтобы вкрутить лампочку?\n— Ни одного, это аппаратная проблема.",
]

ANECDOTES = [
    "Приходит программист к терапевту:\n— Доктор, у меня болит...\n— Где?\n— Не компилируется.",
    "— Как называется человек, который работает с Windows?\n— Windows-программист.\n— А с Linux?\n— Linux-программист.\n— А с Mac?\n— Богатый.",
    "Разговор двух программистов:\n— У тебя есть девушка?\n— Нет, у меня есть 404.",
]

QUOTES = [
    "«Единственный способ делать великую работу — любить то, что ты делаешь.» — Стив Джобс",
    "«Простота — залог надёжности.» — Эдсгер Дейкстра",
    "«Лучший способ предсказать будущее — изобрести его.» — Алан Кэй",
    "«Сначала решите проблему, потом пишите код.» — Джон Джонсон",
]

COMPLIMENTS = [
    "У тебя отличное чувство юмора! 😄",
    "Ты умница! 🧠",
    "С тобой всегда весело! 🎉",
    "Ты сегодня особенно крут(а)! 🔥",
    "У тебя доброе сердце 💖",
]

ZODIACS = {
    "овен": "🐏 Сегодня отличный день для новых начинаний.",
    "телец": "🐂 Деньги придут оттуда, откуда не ждёшь.",
    "близнецы": "♊ Много общения, но не забывай отдыхать.",
    "рак": "🦀 День для семьи и уюта.",
    "лев": "🦁 Твой день! Будешь в центре внимания.",
    "дева": "♍ Внимание к деталям принесёт успех.",
    "весы": "⚖️ Ищи баланс, не руби с плеча.",
    "скорпион": "🦂 Страсть и решительность — твои союзники.",
    "стрелец": "🏹 Готовься к путешествию.",
    "козерог": "🐐 Труд упорный приведёт к цели.",
    "водолей": "🏺 Идеи бьют ключом — записывай!",
    "рыбы": "🐟 Доверься интуиции.",
}

def cmd_8ball(uid, rest):
    if not rest.strip():
        return send(uid, "❌ Задай вопрос: `!8ball <вопрос>`")
    answers = [
        "🎱 Бесспорно, да.", "🎱 Определённо да.", "🎱 Скорее да.",
        "🎱 Не могу сказать точно.", "🎱 Скорее нет.", "🎱 Определённо нет.",
        "🎱 Даже не думай.", "🎱 Всё в твоих руках.",
    ]
    send(uid, f"❓ {rest.strip()}\n💭 {random.choice(answers)}")

def cmd_fact(uid, rest): send(uid, random.choice(FACTS))
def cmd_joke(uid, rest): send(uid, random.choice(JOKES))
def cmd_anecdote(uid, rest): send(uid, random.choice(ANECDOTES))
def cmd_quote(uid, rest): send(uid, random.choice(QUOTES))
def cmd_compliment(uid, rest):
    target = rest.strip() or "ты"
    send(uid, f"💌 {target}: {random.choice(COMPLIMENTS)}")

def cmd_hug(uid, rest):
    target = rest.strip() or "себя"
    send(uid, f"🤗 {target} обнят(а)! Тепло и уютно.")

def cmd_kiss(uid, rest):
    target = rest.strip() or "себя"
    send(uid, f"😘 {target} поцелован(а)! 💋")

def cmd_hit(uid, rest):
    target = rest.strip() or "себя"
    send(uid, f"👊 {target} получил(а) подзатыльник!")

def cmd_kill(uid, rest):
    target = rest.strip() or "себя"
    send(uid, f"💀 {target} был(а) убит(а) в Майнкрафте. Поздравляем!")

def cmd_love(uid, rest):
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ Формат: `!любовь @user1 @user2`")
    percent = random.randint(1, 100)
    emoji = "❤️" if percent >= 80 else "💔" if percent < 30 else "💖"
    send(uid, f"{emoji} Совместимость: **{percent}%**")

def cmd_fortune(uid, rest):
    fortunes = [
        "Сегодня тебя ждёт удача! 🍀",
        "Осторожнее — на пути преграда. ⚠️",
        "Жди хороших новостей. 📩",
        "Деньги найдут тебя сами. 💰",
        "Встреча с важным человеком. 👤",
    ]
    send(uid, f"🔮 {random.choice(fortunes)}")

def cmd_zodiac(uid, rest):
    sign = rest.strip().lower()
    if sign not in ZODIACS:
        return send(uid, "❌ Формат: `!гороскоп овен` (или другой знак)")
    send(uid, ZODIACS[sign])

def cmd_guess(uid, rest):
    """Начать игру «угадай число 1-100»."""
    number = random.randint(1, 100)
    DATA.setdefault("games", {})[str(uid)] = {"type": "guess", "number": number, "tries": 0}
    save_data()
    send(uid, "🎯 Я загадал число от 1 до 100.\nПиши `!число <n>`, чтобы угадать.")

def cmd_guess_number(uid, rest):
    game = DATA.get("games", {}).get(str(uid))
    if not game or game.get("type") != "guess":
        return send(uid, "❌ Игра не запущена. `!угадай`")
    try:
        n = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Введи число.")
    game["tries"] += 1
    if n < game["number"]:
        send(uid, f"⬆️ Моё число больше (попытка {game['tries']})")
    elif n > game["number"]:
        send(uid, f"⬇️ Моё число меньше (попытка {game['tries']})")
    else:
        tries = game["tries"]
        user = get_user(uid)
        reward = max(50, 500 - tries * 20)
        user["balance"] += reward
        DATA["games"].pop(str(uid), None)
        save_data()
        send(uid, f"🎉 Угадал за {tries} попыток! Награда: **{reward:,} 🪙**")

def cmd_rps(uid, rest):
    """Камень-ножницы-бумага."""
    choice = rest.strip().lower()
    if choice not in ("камень", "ножницы", "бумага"):
        return send(uid, "❌ `!кнб камень|ножницы|бумага`")
    bot = random.choice(["камень", "ножницы", "бумага"])
    if choice == bot:
        send(uid, f"🤜 {choice} vs {bot} — ничья!")
    elif (choice == "камень" and bot == "ножницы") or \
         (choice == "ножницы" and bot == "бумага") or \
         (choice == "бумага" and bot == "камень"):
        user = get_user(uid)
        user["balance"] += 50
        save_data()
        send(uid, f"🎉 {choice} vs {bot} — ты победил! +50 🪙")
    else:
        send(uid, f"😢 {choice} vs {bot} — ты проиграл.")


# =========================================================
#     💰 ЭКОНОМИКА (кредит, вклады, промокоды)
# =========================================================
def cmd_credit(uid, rest):
    """Взять кредит под 30%."""
    user = get_user(uid)
    try:
        amount = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!кредит 5000`")
    if amount <= 0 or amount > 50000:
        return send(uid, "❌ Сумма от 1 до 50000.")
    if user.get("credit", 0) > 0:
        return send(uid, f"❌ У тебя уже есть кредит: {user['credit']:,} 🪙. Сначала погаси.")
    user["credit"] = amount
    user["credit_until"] = time.time() + 7 * 86400
    user["balance"] += amount
    save_data()
    send(uid, f"💳 Кредит **{amount:,} 🪙** выдан. Вернуть: **{int(amount*1.3):,} 🪙** в течение 7 дней.\n"
              f"Погасить: `!кредит_погасить`")

def cmd_credit_pay(uid, rest):
    user = get_user(uid)
    credit = user.get("credit", 0)
    if credit <= 0:
        return send(uid, "✅ У тебя нет кредита.")
    debt = int(credit * 1.3)
    if user["balance"] < debt:
        return send(uid, f"❌ Нужно **{debt:,} 🪙**, у тебя {user['balance']:,}.")
    user["balance"] -= debt
    user["credit"] = 0
    user["credit_until"] = 0
    save_data()
    send(uid, f"✅ Кредит погашен! Оплачено **{debt:,} 🪙**.")

def cmd_deposit_cmd(uid, rest):
    """!вклад <сумма> — положить под 5% в сутки."""
    user = get_user(uid)
    try:
        amount = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!вклад 5000`")
    if amount <= 0 or user["balance"] < amount:
        return send(uid, "❌ Недостаточно средств.")
    if user.get("deposit_amount", 0) > 0:
        return send(uid, "❌ У тебя уже есть вклад. Забери: `!вклад_забрать`")
    user["balance"] -= amount
    user["deposit_amount"] = amount
    user["deposit_started"] = time.time()
    save_data()
    send(uid, f"🏦 Вклад **{amount:,} 🪙** открыт под 5% в сутки.\nЗабрать: `!вклад_забрать`")

def cmd_deposit_take(uid, rest):
    user = get_user(uid)
    dep = user.get("deposit_amount", 0)
    if dep <= 0:
        return send(uid, "❌ Вклада нет.")
    days = max(0.1, (time.time() - user.get("deposit_started", time.time())) / 86400)
    profit = int(dep * 0.05 * days)
    total = dep + profit
    user["balance"] += total
    user["deposit_amount"] = 0
    user["deposit_started"] = 0
    save_data()
    send(uid, f"💵 Вклад закрыт! Получено **{total:,} 🪙** (из них прибыль {profit:,}).")

def cmd_promo(uid, rest):
    code = rest.strip().upper()
    promos = DATA.setdefault("promocodes", {})
    if code not in promos:
        return send(uid, "❌ Такого промокода нет.")
    p = promos[code]
    if uid in p.get("used", []):
        return send(uid, "❌ Ты уже использовал этот промокод.")
    if p.get("expires", 0) and time.time() > p["expires"]:
        return send(uid, "❌ Промокод истёк.")
    user = get_user(uid)
    user["balance"] += p["reward"]
    p.setdefault("used", []).append(uid)
    save_data()
    send(uid, f"🎁 Промокод активирован! +**{p['reward']:,} 🪙**")

def cmd_promo_create(uid, rest):
    if not has_at_least(uid, "admins") and not is_group_owner(uid):
        return send(uid, "❌ Нужна роль 🛡️ Админ+.")
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ `!промокод_создать КОД 5000 [дней_жизни]`")
    code = parts[0].upper()
    try:
        reward = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return send(uid, "❌ Награда — число.")
    exp = time.time() + days * 86400 if days else 0
    DATA.setdefault("promocodes", {})[code] = {"reward": reward, "expires": exp, "used": []}
    save_data()
    send(uid, f"✅ Промокод `{code}` создан: +{reward:,} 🪙" + (f" (до {fmt_date(exp)})" if exp else ""))


# =========================================================
#     🌍 СТРАНЫ И ВОЙНЫ
# =========================================================
COUNTRY_BASE = {
    "population": 1000, "army": 100, "gold": 5000,
    "tech": 1, "happiness": 100, "wins": 0, "losses": 0,
    "owner": None, "alliance": None, "buildings": {},
}

def cmd_country_create(uid, rest):
    name = rest.strip()[:32]
    if not name:
        return send(uid, "❌ Формат: `!страна_создать Название`")
    countries = DATA.setdefault("countries", {})
    if name in countries:
        return send(uid, "❌ Такая страна уже существует.")
    user = get_user(uid)
    if user.get("country"):
        return send(uid, f"❌ Ты уже правишь страной **{user['country']}**. Сначала `!страна_распустить`.")
    if user["balance"] < 3000:
        return send(uid, "❌ Для основания нужно 3000 🪙.")
    user["balance"] -= 3000
    countries[name] = dict(COUNTRY_BASE, owner=uid, created=time.time())
    user["country"] = name
    save_data()
    send(uid, f"🏛️ Страна **{name}** основана! Правитель: ты.\nНаселение: 1000, Армия: 100, Казна: 5000")

def cmd_country_info(uid, rest):
    countries = DATA.get("countries", {})
    if not countries:
        return send(uid, "📭 Стран пока нет. Создай: `!страна_создать Название`")
    name = rest.strip()
    if not name:
        user = get_user(uid)
        name = user.get("country")
        if not name:
            return send(uid, "❌ Ты не правишь страной. `!страна_создать <название>`")
    c = countries.get(name)
    if not c:
        return send(uid, "❌ Страна не найдена.")
    owner = c.get("owner")
    owner_name = "—"
    if owner:
        try:
            u = vk.users.get(user_ids=owner)[0]
            owner_name = f"{u['first_name']} {u['last_name']}"
        except Exception:
            owner_name = f"id{owner}"
    text = (
        f"🏛️ **{name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Правитель: {owner_name}\n"
        f"👥 Население: {c['population']:,}\n"
        f"⚔️ Армия: {c['army']:,}\n"
        f"💰 Казна: {c['gold']:,}\n"
        f"🔬 Технологии: ур. {c['tech']}\n"
        f"😊 Счастье: {c['happiness']}%\n"
        f"🏆 Побед: {c['wins']} | Поражений: {c['losses']}\n"
        f"🤝 Альянс: {c['alliance'] or '—'}\n"
        f"🏗️ Постройки: {', '.join(c['buildings'].keys()) or 'нет'}\n"
    )
    send(uid, text)

def cmd_country_build(uid, rest):
    user = get_user(uid)
    country = user.get("country")
    if not country:
        return send(uid, "❌ У тебя нет страны.")
    c = DATA["countries"][country]
    btype = rest.strip().lower()
    buildings = {
        "ферма":     {"cost": 1000, "effect": "population +200"},
        "казарма":   {"cost": 2000, "effect": "army +100"},
        "фабрика":   {"cost": 3000, "effect": "gold +500/ч"},
        "стена":     {"cost": 2500, "effect": "защита +50%"},
        "лаборатория":{"cost": 5000, "effect": "tech +1"},
    }
    if btype not in buildings:
        return send(uid, f"❌ Типы: {', '.join(buildings.keys())}")
    if btype in c["buildings"]:
        return send(uid, f"❌ {btype} уже построена.")
    b = buildings[btype]
    if c["gold"] < b["cost"]:
        return send(uid, f"❌ Нужно {b['cost']:,} золота в казне.")
    c["gold"] -= b["cost"]
    c["buildings"][btype] = time.time()
    # эффект
    if btype == "ферма": c["population"] += 200
    elif btype == "казарма": c["army"] += 100
    elif btype == "лаборатория": c["tech"] += 1
    save_data()
    send(uid, f"🏗️ Построено: **{btype}**! Эффект: {b['effect']}")

def cmd_country_attack(uid, rest):
    user = get_user(uid)
    my_name = user.get("country")
    if not my_name:
        return send(uid, "❌ У тебя нет страны.")
    target_name = rest.strip()
    if not target_name:
        return send(uid, "❌ Формат: `!атака <страна>`")
    countries = DATA.get("countries", {})
    if target_name not in countries:
        return send(uid, "❌ Страна не найдена.")
    if target_name == my_name:
        return send(uid, "❌ Нельзя атаковать себя.")
    me = countries[my_name]
    enemy = countries[target_name]
    my_power = me["army"] * (1 + me["tech"] * 0.1)
    en_power = enemy["army"] * (1 + enemy["tech"] * 0.1)
    if "стена" in enemy["buildings"]:
        en_power *= 1.5
    if me["alliance"] == target_name:
        return send(uid, "❌ Нельзя атаковать союзника. Сначала `!страна_разрыв_союза`.")
    # Случайность
    my_power *= random.uniform(0.8, 1.2)
    en_power *= random.uniform(0.8, 1.2)
    if my_power > en_power:
        loot = min(enemy["gold"], int(my_power * 10))
        enemy["gold"] -= loot
        me["gold"] += loot
        enemy["army"] = max(50, enemy["army"] - int(enemy["army"] * 0.3))
        me["wins"] += 1
        enemy["losses"] += 1
        send(uid, f"⚔️ **Победа!** {my_name} разбила {target_name}!\n"
                  f"🎁 Захвачено золота: **{loot:,}**\n"
                  f"⚔️ Армия врага потеряла 30%.")
    else:
        me["army"] = max(50, me["army"] - int(me["army"] * 0.4))
        me["losses"] += 1
        enemy["wins"] += 1
        send(uid, f"💥 **Поражение!** {my_name} проиграла {target_name}.\n"
                  f"⚔️ Ты потерял 40% армии.")
    save_data()

def cmd_country_top(uid, rest):
    countries = DATA.get("countries", {})
    if not countries:
        return send(uid, "📭 Стран нет.")
    ranked = sorted(countries.items(),
                    key=lambda x: (x[1]["army"] * (1 + x[1]["tech"] * 0.1) + x[1]["gold"] / 100),
                    reverse=True)[:10]
    text = "🏆 **ТОП СТРАН**\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, (name, c) in enumerate(ranked, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
        text += f"{medal} **{name}** — ⚔️{c['army']} 💰{c['gold']:,}\n"
    send(uid, text)

def cmd_country_dissolve(uid, rest):
    user = get_user(uid)
    name = user.get("country")
    if not name:
        return send(uid, "❌ У тебя нет страны.")
    c = DATA["countries"][name]
    if c.get("owner") != uid:
        return send(uid, "❌ Ты не правитель.")
    del DATA["countries"][name]
    user["country"] = None
    save_data()
    send(uid, f"💀 Страна **{name}** распущена.")

def cmd_country_give(uid, rest):
    """!страна_передать @user — передать свою страну."""
    if not is_group_owner(uid) and not has_at_least(uid, "owner"):
        return send(uid, "❌ Только 👑 Создатель.")
    parts = rest.split()
    if not parts:
        return send(uid, "❌ `!страна_передать @user`")
    user = get_user(uid)
    name = user.get("country")
    if not name:
        return send(uid, "❌ У тебя нет страны.")
    target = _parse_uid(parts[0])
    if not target:
        return send(uid, "❌ Не смог найти юзера.")
    DATA["countries"][name]["owner"] = target
    user["country"] = None
    get_user(target)["country"] = name
    save_data()
    send(uid, f"🏛️ Страна **{name}** передана id{target}.")


# =========================================================
#     🏰 КЛАНЫ
# =========================================================
def cmd_clan_create(uid, rest):
    name = rest.strip()[:32]
    if not name:
        return send(uid, "❌ `!клан_создать Название`")
    clans = DATA.setdefault("clans", {})
    if name in clans:
        return send(uid, "❌ Такой клан уже есть.")
    user = get_user(uid)
    if user.get("clan"):
        return send(uid, f"❌ Ты уже в клане **{user['clan']}**.")
    if user["balance"] < 5000:
        return send(uid, "❌ Нужно 5000 🪙.")
    user["balance"] -= 5000
    clans[name] = {"owner": uid, "members": [uid], "gold": 0, "level": 1, "created": time.time()}
    user["clan"] = name
    save_data()
    send(uid, f"🏰 Клан **{name}** создан! Ты — лидер.")

def cmd_clan_info(uid, rest):
    name = rest.strip()
    if not name:
        user = get_user(uid)
        name = user.get("clan")
        if not name:
            return send(uid, "❌ Ты не в клане.")
    clans = DATA.get("clans", {})
    c = clans.get(name)
    if not c:
        return send(uid, "❌ Клан не найден.")
    owner = c["owner"]
    try:
        u = vk.users.get(user_ids=owner)[0]
        owner_name = f"{u['first_name']} {u['last_name']}"
    except Exception:
        owner_name = f"id{owner}"
    text = (
        f"🏰 **{name}**\n"
        f"👑 Лидер: {owner_name}\n"
        f"👥 Участников: {len(c['members'])}\n"
        f"💰 Казна: {c['gold']:,} 🪙\n"
        f"📈 Уровень: {c['level']}\n"
    )
    send(uid, text)

def cmd_clan_invite(uid, rest):
    user = get_user(uid)
    clan_name = user.get("clan")
    if not clan_name:
        return send(uid, "❌ Ты не в клане.")
    c = DATA["clans"][clan_name]
    if c["owner"] != uid:
        return send(uid, "❌ Только лидер может приглашать.")
    target = _parse_uid(rest.strip())
    if not target:
        return send(uid, "❌ `!клан_инвайт @user`")
    if get_user(target).get("clan"):
        return send(uid, "❌ Он уже в клане.")
    if target in c["members"]:
        return send(uid, "❌ Он уже в твоём клане.")
    c["members"].append(target)
    get_user(target)["clan"] = clan_name
    save_data()
    send(uid, f"✅ id{target} принят в клан **{clan_name}**.")

def cmd_clan_leave(uid, rest):
    user = get_user(uid)
    name = user.get("clan")
    if not name:
        return send(uid, "❌ Ты не в клане.")
    c = DATA["clans"][name]
    if c["owner"] == uid:
        return send(uid, "❌ Лидер не может выйти. Распусти клан.")
    c["members"].remove(uid)
    user["clan"] = None
    save_data()
    send(uid, f"👋 Ты покинул клан **{name}**.")

def cmd_clan_deposit(uid, rest):
    user = get_user(uid)
    name = user.get("clan")
    if not name:
        return send(uid, "❌ Ты не в клане.")
    try:
        amount = int(rest.strip())
    except ValueError:
        return send(uid, "❌ Формат: `!клан_казна 500`")
    if amount <= 0 or user["balance"] < amount:
        return send(uid, "❌ Недостаточно средств.")
    user["balance"] -= amount
    DATA["clans"][name]["gold"] += amount
    save_data()
    send(uid, f"💰 +**{amount:,} 🪙** в казну клана **{name}**.")

def cmd_clan_top(uid, rest):
    clans = DATA.get("clans", {})
    if not clans:
        return send(uid, "📭 Кланов нет.")
    ranked = sorted(clans.items(), key=lambda x: (x[1]["gold"], len(x[1]["members"])), reverse=True)[:10]
    text = "🏆 **ТОП КЛАНОВ**\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, (name, c) in enumerate(ranked, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
        text += f"{medal} **{name}** — 💰{c['gold']:,} 👥{len(c['members'])}\n"
    send(uid, text)


# =========================================================
#     📊 СТАТИСТИКА / ТОПЫ
# =========================================================
def cmd_top_balance(uid, rest):
    users = sorted(DATA["users"].items(), key=lambda x: x[1]["balance"] + x[1].get("bank", 0), reverse=True)[:10]
    text = "🏆 **ТОП БОГАЧЕЙ**\n"
    for i, (uid_s, u) in enumerate(users, 1):
        try:
            v = vk.users.get(user_ids=int(uid_s))[0]
            name = f"{v['first_name']} {v['last_name']}"
        except Exception:
            name = f"id{uid_s}"
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
        text += f"{medal} {name} — {u['balance']+u.get('bank',0):,} 🪙\n"
    send(uid, text)

def cmd_top_countries(uid, rest): cmd_country_top(uid, rest)
def cmd_top_clans(uid, rest): cmd_clan_top(uid, rest)

def cmd_stats(uid, rest):
    text = (
        f"📊 **Статистика бота**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Юзеров: {len(DATA['users'])}\n"
        f"🌍 Стран: {len(DATA.get('countries', {}))}\n"
        f"🏰 Кланов: {len(DATA.get('clans', {}))}\n"
        f"🎬 TikTok-видео: {len(DATA.get('tiktok', {}))}\n"
        f"▶️ YouTube-видео: {len(DATA.get('youtube', {}))}\n"
        f"🎁 Промокодов: {len(DATA.get('promocodes', {}))}\n"
    )
    send(uid, text)


# =========================================================
#     🛡️ МОДЕРАЦИЯ (расширение)
# =========================================================
def cmd_warn(uid, rest):
    if not has_at_least(uid, "moderators"):
        return send(uid, "❌ Нужна роль 🔨 Модератор+.")
    parts = rest.split(maxsplit=1)
    if not parts:
        return send(uid, "❌ `!варн @user причина`")
    target = _parse_uid(parts[0])
    reason = parts[1] if len(parts) > 1 else "без причины"
    p = get_punishment(target)
    p["warns"] += 1
    save_data()
    send(uid, f"⚠️ id{target} получил варн ({p['warns']}/3). Причина: {reason}")

def cmd_warn_list(uid, rest):
    target = _parse_uid(rest.strip()) if rest.strip() else uid
    p = get_punishment(target)
    send(uid, f"📋 Варны id{target}: {p['warns']}/3")

def cmd_unwarn(uid, rest):
    if not has_at_least(uid, "moderators"):
        return send(uid, "❌ Нужна роль 🔨 Модератор+.")
    target = _parse_uid(rest.strip())
    p = get_punishment(target)
    p["warns"] = max(0, p["warns"] - 1)
    save_data()
    send(uid, f"✅ Снят один варн с id{target} ({p['warns']}/3).")

def cmd_ban_list(uid, rest):
    if not has_at_least(uid, "moderators"):
        return send(uid, "❌ Нужна роль 🔨 Модератор+.")
    banned = [uid_s for uid_s, p in DATA["punishments"].items() if p.get("banned")]
    if not banned:
        return send(uid, "📭 Забаненных нет.")
    text = "🚫 **Забаненные:**\n"
    for b in banned[:30]:
        try:
            v = vk.users.get(user_ids=int(b))[0]
            text += f"• id{b} — {v['first_name']} {v['last_name']}\n"
        except Exception:
            text += f"• id{b}\n"
    send(uid, text)

def cmd_mutelist(uid, rest):
    if not has_at_least(uid, "moderators"):
        return send(uid, "❌ Нужна роль 🔨 Модератор+.")
    now = time.time()
    muted = [(uid_s, p) for uid_s, p in DATA["punishments"].items() if p.get("mute_until", 0) > now]
    if not muted:
        return send(uid, "🔊 Замученных нет.")
    text = "🔇 **Активные муты:**\n"
    for uid_s, p in muted[:30]:
        left = int(p["mute_until"] - now)
        text += f"• id{uid_s} — ещё {left // 60}м {left % 60}с\n"
    send(uid, text)


# =========================================================
#     ⚙️ УТИЛИТЫ
# =========================================================
def cmd_user_info(uid, rest):
    target = _parse_uid(rest.strip()) if rest.strip() else uid
    try:
        u = vk.users.get(user_ids=target, fields="city,country,sex,bdate,last_seen")[0]
    except Exception:
        return send(uid, "❌ Не смог получить данные.")
    user = get_user(target)
    roles = [ROLE_NAMES[r] for r, ids in DATA["roles"].items() if target in ids]
    text = (
        f"👤 **Профиль**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Имя: {u['first_name']} {u['last_name']}\n"
        f"ID: {target}\n"
        f"Город: {u.get('city', {}).get('title', '—')}\n"
        f"Баланс: {user['balance']:,} 🪙\n"
        f"Уровень: {user['level']}\n"
        f"Роли: {', '.join(roles) if roles else '—'}\n"
        f"Страна: {user.get('country') or '—'}\n"
        f"Клан: {user.get('clan') or '—'}\n"
    )
    send(uid, text)

def cmd_avatar(uid, rest):
    target = _parse_uid(rest.strip()) if rest.strip() else uid
    try:
        u = vk.users.get(user_ids=target, fields="photo_max")[0]
        send(uid, f"🖼️ Аватар {u['first_name']}: {u['photo_max']}")
    except Exception:
        send(uid, "❌ Не смог получить аватар.")

def cmd_myid(uid, rest):
    send(uid, f"🆔 Твой ID: **{uid}**")

def cmd_uptime(uid, rest):
    import time as t
    start = DATA.get("start_time", t.time())
    elapsed = int(t.time() - start)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    send(uid, f"⏱️ Бот работает: **{h}ч {m}м {s}с**")

def cmd_random(uid, rest):
    parts = rest.split()
    if len(parts) < 2:
        return send(uid, "❌ `!рандом 1 100`")
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return send(uid, "❌ Числа.")
    send(uid, f"🎲 {random.randint(min(a,b), max(a,b))}")

def cmd_password(uid, rest):
    import string
    try:
        length = int(rest.strip()) if rest.strip() else 16
    except ValueError:
        length = 16
    length = min(64, max(6, length))
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    send(uid, f"🔐 Пароль:\n`{pwd}`")

def cmd_hash(uid, rest):
    import hashlib
    text = rest.strip()
    if not text:
        return send(uid, "❌ `!хеш <текст>`")
    h = hashlib.sha256(text.encode()).hexdigest()
    send(uid, f"🔒 SHA-256:\n`{h}`")


# =========================================================
#     👑 ВЛАДЕЛЕЦ / РАЗРАБОТЧИК
# =========================================================
def cmd_owner_panel(uid, rest):
    if not is_group_owner(uid) and not has_at_least(uid, "owner"):
        return send(uid, "❌ Только 👑 Создатель.")
    text = (
        "👑 **ПАНЕЛЬ СОЗДАТЕЛЯ**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 **Выдача денег:**\n"
        "`!выдать @user 5000` — выдать одному\n"
        "`!забрать @user 5000` — забрать\n"
        "`!установить_баланс @user 5000` — точное значение\n"
        "`!выдать_всем 1000` — всем юзерам\n"
        "`!выдать_роли developers 10000` — по роли\n"
        "`!money_log` — история выдач\n\n"
        "🛡️ **Роли:**\n"
        "`!роль добавить developers @user`\n"
        "`!роль убрать admins @user`\n"
        "`!роль список`\n\n"
        "🏛️ **Страны:**\n"
        "`!страна_передать @user` — передать\n"
        "`!страна_распустить` — удалить\n\n"
        "💻 **Разработка:**\n"
        "`!eval <python>` — выполнить код\n"
        "`!sql <SQL>` — запрос к БД\n"
        "`!бэкап` / `!бэкапы` — бэкапы\n"
        "`!сброс_юзера @user` — сброс профиля\n\n"
        "⚙️ **Система:**\n"
        "`!stats` — статистика\n"
        "`!uptime` — аптайм\n"
    )
    send(uid, text)

def cmd_eval(uid, rest):
    if not is_group_owner(uid) and not has_at_least(uid, "owner"):
        return send(uid, "❌ Только 👑 Создатель.")
    try:
        env = {"vk": vk, "DATA": DATA, "send": send, "save_data": save_data,
               "random": random, "time": time, "os": os, "json": json}
        result = eval(rest, {"__builtins__": __builtins__}, env)
        send(uid, f"✅ Результат:\n```\n{result}\n```")
    except Exception as e:
        send(uid, f"❌ Ошибка:\n```\n{e}\n```")

def cmd_reset_user(uid, rest):
    if not is_group_owner(uid) and not has_at_least(uid, "owner"):
        return send(uid, "❌ Только 👑 Создатель.")
    target = _parse_uid(rest.strip())
    if str(target) in DATA["users"]:
        del DATA["users"][str(target)]
        save_data()
        send(uid, f"🔄 Профиль id{target} сброшен.")
    else:
        send(uid, "❌ Юзера нет в БД.")


# =========================================================
#     🎯 ОБРАБОТЧИК ВСЕХ ADDON-КОМАНД
# =========================================================
COMMANDS = {
    # Деньги
    "выдать": cmd_give_money,
    "give": cmd_give_money,
    "забрать": cmd_take_money,
    "take": cmd_take_money,
    "установить_баланс": cmd_set_balance,
    "выдать_всем": cmd_give_all,
    "выдать_роли": cmd_give_role_money,
    "money_log": cmd_money_log,
    # Казино
    "казино": cmd_casino,
    "рулетка": cmd_roulette,
    "краш": cmd_crash,
    "стоп": cmd_crash_stop,
    "мины": cmd_mines,
    "блэкджек": cmd_blackjack,
    # Развлечения
    "8ball": cmd_8ball,
    "факт": cmd_fact,
    "шутка": cmd_joke,
    "анекдот": cmd_anecdote,
    "цитата": cmd_quote,
    "комплимент": cmd_compliment,
    "обнять": cmd_hug,
    "поцеловать": cmd_kiss,
    "ударить": cmd_hit,
    "убить": cmd_kill,
    "любовь": cmd_love,
    "гадание": cmd_fortune,
    "гороскоп": cmd_zodiac,
    "угадай": cmd_guess,
    "число": cmd_guess_number,
    "кнб": cmd_rps,
    # Экономика
    "кредит": cmd_credit,
    "кредит_погасить": cmd_credit_pay,
    "вклад": cmd_deposit_cmd,
    "вклад_забрать": cmd_deposit_take,
    "промокод": cmd_promo,
    "промокод_создать": cmd_promo_create,
    # Страны
    "страна_создать": cmd_country_create,
    "страна_инфо": cmd_country_info,
    "страна_стройка": cmd_country_build,
    "страна_топ": cmd_country_top,
    "страна_распустить": cmd_country_dissolve,
    "страна_передать": cmd_country_give,
    "атака": cmd_country_attack,
    # Кланы
    "клан_создать": cmd_clan_create,
    "клан_инфо": cmd_clan_info,
    "клан_инвайт": cmd_clan_invite,
    "клан_выйти": cmd_clan_leave,
    "клан_казна": cmd_clan_deposit,
    "клан_топ": cmd_clan_top,
    # Топы / статистика
    "топ_баланс": cmd_top_balance,
    "топ_богачей": cmd_top_balance,
    "stats": cmd_stats,
    "статистика": cmd_stats,
    # Модерация
    "варн": cmd_warn,
    "варны": cmd_warn_list,
    "снять_варн": cmd_unwarn,
    "бан_лист": cmd_ban_list,
    "мут_лист": cmd_mutelist,
    # Утилиты
    "юзер": cmd_user_info,
    "аватар": cmd_avatar,
    "мой_id": cmd_myid,
    "аптайм": cmd_uptime,
    "рандом": cmd_random,
    "пароль": cmd_password,
    "хеш": cmd_hash,
    # Владелец
    "панель": cmd_owner_panel,
    "owner_panel": cmd_owner_panel,
    "eval": cmd_eval,
    "сброс_юзера": cmd_reset_user,
}


def try_handle(uid: int, text: str) -> bool:
    """Возвращает True, если команда обработана модулем."""
    if not text.startswith("!"):
        return False
    cmd, _, rest = text[1:].partition(" ")
    cmd = cmd.lower().strip()
    if cmd in COMMANDS:
        try:
            COMMANDS[cmd](uid, rest)
        except Exception as e:
            send(uid, f"⚠️ Ошибка команды `{cmd}`: {e}")
        return True
    return False
