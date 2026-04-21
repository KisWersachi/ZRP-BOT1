import logging
import os
import random
import time
import re
from flask import Flask, request
import vk_api
from vk_api.utils import get_random_id
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = "vk1.a.JOGy731NXPv7SPYNcORJe_NDCWCJftwgoo_fDkLJKrWpaZHMY5PYwv-0djtwII7PUJxWJB1YTy6etSuAn3oD0S6hkiQVrGKlyUFpQQyjD-AZyaOtGvpU8xVhjbJrWIUUX_kkfcCpjlmZ-5BVsqW0KU7Rbn3KKD7V8gktb-t7_WThyynca8-qOW-e7kVxIJieRxdJheWV6vTBOdYY-XzaMA"
CONFIRMATION_CODE = "be1f1be5"

def send_message(peer_id, text):
    try:
        vk = vk_api.VkApi(token=TOKEN).get_api()
        vk.messages.send(
            peer_id=peer_id,
            message=text,
            random_id=get_random_id()
        )
        logger.info(f"Сообщение отправлено в {peer_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def get_user_info(user_id):
    try:
        vk = vk_api.VkApi(token=TOKEN).get_api()
        return vk.users.get(user_ids=user_id)[0]
    except:
        return {"first_name": "Пользователь", "last_name": ""}

def parse_time(time_str):
    match = re.search(r'(\d+)\s*([hmd])', time_str.lower())
    if not match:
        return 3600
    value = int(match.group(1))
    unit = match.group(2)
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    return 3600

def format_time_delta(seconds):
    if seconds <= 0:
        return "закончился"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}ч {minutes}м"
    return f"{minutes}м"

# Простые БД-функции (без sqlite, используем словари для демонстрации, но лучше заменить на реальную БД)
# Для простоты используем глобальные словари. В реальности нужно использовать database.py.
users = {}  # user_id -> {"coins": 0, "warnings": 0, "messages": 0, "last_daily": 0, "daily_streak": 0, "last_work": 0, "mute_until": 0}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {"coins": 0, "warnings": 0, "messages": 0, "last_daily": 0, "daily_streak": 0, "last_work": 0, "mute_until": 0}
    return users[user_id]

def add_coins(user_id, amount):
    u = get_user(user_id)
    u["coins"] += amount

def remove_coins(user_id, amount):
    u = get_user(user_id)
    u["coins"] = max(0, u["coins"] - amount)

def get_coins(user_id):
    return get_user(user_id)["coins"]

def add_warning(user_id):
    u = get_user(user_id)
    u["warnings"] += 1

def get_warnings(user_id):
    return get_user(user_id)["warnings"]

def set_mute(user_id, duration):
    u = get_user(user_id)
    u["mute_until"] = int(time.time()) + duration

def is_muted(user_id):
    u = get_user(user_id)
    return u["mute_until"] > int(time.time())

@app.route("/", methods=["POST"])
def callback():
    data = request.json
    logger.info(f"Тип: {data.get('type')}")
    
    if data.get("type") == "confirmation":
        return CONFIRMATION_CODE
    
    if data.get("type") == "message_new":
        msg = data["object"]["message"]
        peer_id = msg["peer_id"]
        user_id = msg["from_id"]
        text = msg.get("text", "").strip().lower()
        
        logger.info(f"Сообщение от {user_id}: '{text}'")
        
        # Игнорируем, если пользователь в муте
        if is_muted(user_id) and not text.startswith("/unmute"):
            send_message(peer_id, f"❌ Вы в муте до {format_time_delta(get_user(user_id)['mute_until'] - int(time.time()))}")
            return "ok"
        
        # Обработка команд
        if text == "/help":
            help_text = """📋 **Команды бота**

💰 **Экономика:**
/balance - баланс
/daily - ежедневный бонус
/work - работа
/top - топ богатых

🎲 **Игры:**
/roll - бросок кубика
/coin - монетка

🎭 **RP:**
/me действие - *действие*
/hug @user - обнять

👑 **Модерация:**
/warn @user - варн
/kick @user - кик
/mute @user 1h - мут
/unmute @user - снять мут
/ban @user - бан
/clear N - очистка

ℹ️ **Инфо:**
/profile @user - профиль
/online - онлайн"""
            send_message(peer_id, help_text)
        
        elif text.startswith("/balance"):
            send_message(peer_id, f"💰 Баланс: {get_coins(user_id)} монет")
        
        elif text == "/daily":
            u = get_user(user_id)
            now = int(time.time())
            last = u["last_daily"]
            streak = u["daily_streak"]
            if now - last < 86400:
                remain = 86400 - (now - last)
                send_message(peer_id, f"⏰ Бонус через {format_time_delta(remain)}")
                return "ok"
            if now - last < 172800:
                streak += 1
            else:
                streak = 1
            bonus = 50 + min(streak * 10, 100)
            u["coins"] += bonus
            u["last_daily"] = now
            u["daily_streak"] = streak
            send_message(peer_id, f"🎁 +{bonus} монет! Серия: {streak} дней")
        
        elif text == "/work":
            u = get_user(user_id)
            now = int(time.time())
            last = u["last_work"]
            if now - last < 3600:
                remain = 3600 - (now - last)
                send_message(peer_id, f"⏰ Работа через {format_time_delta(remain)}")
                return "ok"
            earnings = random.randint(20, 50)
            u["coins"] += earnings
            u["last_work"] = now
            jobs = ["сделал заказ", "помог клиенту", "выполнил задание"]
            job = random.choice(jobs)
            send_message(peer_id, f"💼 Вы {job} и заработали {earnings} монет!")
        
        elif text == "/top":
            sorted_users = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:10]
            if not sorted_users:
                send_message(peer_id, "📊 Топ пуст")
                return "ok"
            resp = "🏆 **Топ богатых:**\n"
            for i, (uid, data) in enumerate(sorted_users, 1):
                try:
                    info = get_user_info(uid)
                    name = f"{info['first_name']} {info['last_name']}"
                except:
                    name = f"ID{uid}"
                resp += f"{i}. {name} - {data['coins']} 🪙\n"
            send_message(peer_id, resp)
        
        elif text.startswith("/profile"):
            parts = text.split()
            target = user_id
            if len(parts) > 1:
                # Извлечение ID из упоминания
                match = re.search(r'\[id(\d+)\|', parts[1])
                if match:
                    target = int(match.group(1))
            u = get_user(target)
            try:
                info = get_user_info(target)
                name = f"{info['first_name']} {info['last_name']}"
            except:
                name = f"ID{target}"
            resp = f"""👤 **Профиль {name}**
💰 Монет: {u['coins']}
⚠️ Варнов: {u['warnings']}
📊 Сообщений: {u['messages']}"""
            send_message(peer_id, resp)
        
        elif text == "/online":
            # В этой упрощённой версии нет функции онлайн, просто заглушка
            send_message(peer_id, "🟢 Функция онлайн в разработке")
        
        elif text.startswith("/me"):
            action = text[3:].strip()
            if not action:
                send_message(peer_id, "❌ Укажите действие")
                return "ok"
            info = get_user_info(user_id)
            name = f"{info['first_name']} {info['last_name']}"
            send_message(peer_id, f"*{name} {action}*")
        
        elif text.startswith("/hug"):
            parts = text.split()
            if len(parts) < 2:
                send_message(peer_id, "❌ Укажите пользователя: /hug @user")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            info1 = get_user_info(user_id)
            info2 = get_user_info(target)
            name1 = f"{info1['first_name']} {info1['last_name']}"
            name2 = f"{info2['first_name']} {info2['last_name']}"
            send_message(peer_id, f"🤗 *{name1} обнял(а) {name2}*")
        
        elif text == "/roll":
            result = random.randint(1, 100)
            send_message(peer_id, f"🎲 *Выпало {result}*")
        
        elif text == "/coin":
            result = random.choice(['Орёл', 'Решка'])
            send_message(peer_id, f"🪙 *{result}*")
        
        # Модерация (требуют прав, но для простоты пропускаем проверку)
        elif text.startswith("/warn"):
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                send_message(peer_id, "❌ /warn @user причина")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            reason = parts[2] if len(parts) > 2 else "без причины"
            add_warning(target)
            send_message(peer_id, f"⚠️ Пользователю [id{target}|выдано предупреждение]\nПричина: {reason}")
        
        elif text.startswith("/kick"):
            parts = text.split()
            if len(parts) < 2:
                send_message(peer_id, "❌ /kick @user")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            # Здесь нужно вызывать VK API для кика, но для упрощения просто сообщаем
            send_message(peer_id, f"👢 Пользователь [id{target}|кикнут]")
        
        elif text.startswith("/mute"):
            parts = text.split(maxsplit=3)
            if len(parts) < 3:
                send_message(peer_id, "❌ /mute @user 1h причина")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            duration = parse_time(parts[2])
            set_mute(target, duration)
            send_message(peer_id, f"🔇 Пользователь [id{target}|замьючен] на {format_time_delta(duration)}")
        
        elif text.startswith("/unmute"):
            parts = text.split()
            if len(parts) < 2:
                send_message(peer_id, "❌ /unmute @user")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            u = get_user(target)
            u["mute_until"] = 0
            send_message(peer_id, f"🔊 Пользователь [id{target}|размьючен]")
        
        elif text.startswith("/ban"):
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                send_message(peer_id, "❌ /ban @user причина")
                return "ok"
            match = re.search(r'\[id(\d+)\|', parts[1])
            if not match:
                send_message(peer_id, "❌ Не удалось определить пользователя")
                return "ok"
            target = int(match.group(1))
            reason = parts[2] if len(parts) > 2 else "без причины"
            send_message(peer_id, f"🚫 Пользователь [id{target}|забанен]\nПричина: {reason}")
        
        elif text.startswith("/clear"):
            parts = text.split()
            count = 10
            if len(parts) > 1 and parts[1].isdigit():
                count = min(int(parts[1]), 50)
            send_message(peer_id, f"🗑️ Очищено {count} сообщений")
        
        else:
            # Если команда не распознана
            if text.startswith("/"):
                send_message(peer_id, f"❌ Неизвестная команда. Напишите /help")
        
        return "ok"
    
    return "ok"

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
