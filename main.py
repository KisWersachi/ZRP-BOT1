import logging
import os
import sys
from flask import Flask, request

sys.path.insert(0, os.path.dirname(__file__))

from bot import VkBot
from config import load_config
from database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

config = load_config()
init_db()

bot = VkBot(
    group_id=config["group_id"],
    token=config["token"],
    command_cooldown=config["command_cooldown"],
    log_peer_id=config.get("log_peer_id")
)

# Код подтверждения из переменных окружения или новый
CONFIRMATION_CODE = os.getenv("CONFIRMATION_CODE", "be1f1be5")

app = Flask(__name__)

@app.route("/", methods=["POST"])
def callback():
    data = request.json
    logger.info(f"Получен тип: {data.get('type')}")
    
    # Подтверждение сервера
    if data.get("type") == "confirmation":
        logger.info(f"Отправляем код подтверждения: {CONFIRMATION_CODE}")
        return CONFIRMATION_CODE
    
    # Новое сообщение
    if data.get("type") == "message_new":
        message = data["object"]["message"]
        
        # Создаём событие для бота
        class Event:
            pass
        
        event = Event()
        event.obj = Event()
        event.obj.message = message
        event.type = "message_new"
        
        bot.handle_message(event)
        
        return "ok"
    
    return "ok"

@app.route("/", methods=["GET"])
def health():
    return "VK Bot is running", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    logger.info(f"Запуск на порту {port}")
    app.run(host="0.0.0.0", port=port)
