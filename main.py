import logging
import os
from flask import Flask, request
import vk_api
from vk_api.utils import get_random_id

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

@app.route("/", methods=["POST"])
def callback():
    data = request.json
    logger.info(f"Получен тип: {data.get('type')}")
    
    if data.get("type") == "confirmation":
        return CONFIRMATION_CODE
    
    if data.get("type") == "message_new":
        message = data["object"]["message"]
        peer_id = message["peer_id"]
        text = message.get("text", "").strip()
        user_id = message["from_id"]
        
        logger.info(f"Сообщение от {user_id}: '{text}'")
        
        # Простая обработка команд
        if text == "/help":
            send_message(peer_id, "✅ Бот работает!\n\nКоманды:\n/help - помощь\n/balance - баланс\n/daily - бонус")
            logger.info("Ответ на /help отправлен")
        elif text == "/balance":
            send_message(peer_id, "💰 Баланс: 0 монет")
        elif text == "/daily":
            send_message(peer_id, "🎁 Ежедневный бонус: +50 монет!")
        else:
            send_message(peer_id, f"❌ Неизвестная команда. Напишите /help")
        
        return "ok"
    
    return "ok"

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
