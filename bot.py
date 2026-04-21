import logging
import time
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, List, Tuple, Callable, Any, Optional, Union

import database as db
from commands import CommandRegistry
from utils import parse_command, parse_time, format_time_delta

logger = logging.getLogger(__name__)

# Иерархия ролей (10 уровней)
ROLE_HIERARCHY = {
    "user": 1,
    "assistant": 2,
    "junior_moderator": 3,
    "moderator": 4,
    "senior_moderator": 5,
    "admin": 6,
    "senior_admin": 7,
    "special_admin": 8,
    "owner": 9,
    "creator": 10
}

ROLE_NAMES = {
    "creator": "👑 Создатель",
    "owner": "⭐ Владелец",
    "special_admin": "🔰 Специальный администратор",
    "senior_admin": "📌 Главный администратор",
    "admin": "⚙️ Администратор",
    "senior_moderator": "🛡️ Старший модератор",
    "moderator": "🔨 Модератор",
    "junior_moderator": "📋 Младший модератор",
    "assistant": "🤝 Помощник",
    "user": "👤 Пользователь"
}

class VkBot:
    def __init__(self, group_id: str, token: str, command_cooldown: int = 3, log_peer_id: Optional[str] = None):
        self.group_id = group_id
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.command_cooldown = command_cooldown
        self.log_peer_id = log_peer_id
        
        if self.log_peer_id:
            logger.info(f"Логирование настроено. ID беседы для логов: {self.log_peer_id}")
        else:
            logger.warning("Логирование отключено: не указан ID беседы для логов")
        
        self.last_command_time = {}
        self.quiet_mode = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.delete_queue = []
        self.delete_lock = threading.Lock()
        
        self.commands = CommandRegistry(self)
        
        logger.info(f"VK Bot initialized with group_id: {group_id}")

    def send_message(self, peer_id: int, message: str) -> Optional[int]:
        try:
            result = self.vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=vk_api.utils.get_random_id()
            )
            logger.info(f"Message sent to peer_id {peer_id}: {message[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return None

    def delete_message(self, peer_id: int, message_id: int) -> bool:
        if peer_id > 2000000000:
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    cmids=int(message_id),
                    peer_id=peer_id
                )
                logger.info(f"Сообщение {message_id} удалено (беседа {peer_id})")
                return True
            except Exception as err:
                logger.warning(f"Не удалось удалить сообщение (способ 1): {str(err)}")
            
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=[int(message_id)],
                    peer_id=peer_id
                )
                logger.info(f"Сообщение {message_id} удалено списком (беседа {peer_id})")
                return True
            except Exception as err:
                logger.warning(f"Не удалось удалить сообщение (способ 2): {str(err)}")
            
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=str(message_id),
                    peer_id=peer_id
                )
                logger.info(f"Сообщение {message_id} удалено строкой (беседа {peer_id})")
                return True
            except Exception as err:
                logger.error(f"Все способы удаления сообщения не сработали: {str(err)}")
                return False
        else:
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=message_id,
                    peer_id=peer_id
                )
                logger.info(f"Удалено личное сообщение {message_id}")
                return True
            except Exception as e:
                logger.error(f"Критическая ошибка удаления: {str(e)}")
                return False
            
    def send_log_message(self, action: str, admin_id: int, target_id: Optional[int] = None, 
                        peer_id: Optional[int] = None, details: Optional[str] = None) -> bool:
        if not self.log_peer_id:
            return False
            
        try:
            admin_info = self.vk.users.get(user_ids=admin_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
            
            target_name = "N/A"
            if target_id:
                try:
                    target_info = self.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
                    target_name = f"{target_info['first_name']} {target_info['last_name']}"
                except:
                    target_name = f"ID: {target_id}"
            
            chat_info = ""
            if peer_id:
                try:
                    chat_id = peer_id - 2000000000
                    chat_name = f"Беседа #{chat_id}"
                    chat_info = f"\n📢 Беседа: {chat_name}"
                except:
                    chat_info = f"\n📢 Беседа: ID {peer_id}"
            
            action_emojis = {
                "kick": "🚪", "ban": "🚫", "unban": "✅", "warn": "⚠️",
                "unwarn": "🔄", "mute": "🔇", "unmute": "🔊", "set_role": "🔰",
                "remove_role": "⛔", "quiet": "🤫", "delete": "🗑️", "message": "💬",
                "start": "🚀", "masskick": "👥🚪"
            }
            
            action_readable = {
                "kick": "Исключение", "ban": "Блокировка", "unban": "Разблокировка",
                "warn": "Предупреждение", "unwarn": "Снятие предупреждения",
                "mute": "Отключение чата", "unmute": "Включение чата",
                "set_role": "Назначение роли", "remove_role": "Снятие роли",
                "quiet": "Режим тишины", "delete": "Удаление сообщения",
                "message": "Сообщение", "start": "Активация бота", "masskick": "Массовое исключение"
            }
            
            emoji = action_emojis.get(action, "ℹ️")
            action_text = action_readable.get(action, action.capitalize())
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            
            log_message = (
                f"{emoji} {action_text}\n\n"
                f"👮 Модератор: [id{admin_id}|{admin_name}]\n"
            )
            
            if target_id:
                log_message += f"👤 Пользователь: [id{target_id}|{target_name}]\n"
                
            if details:
                log_message += f"📋 Детали: {details}\n"
                
            log_message += f"{chat_info}\n⏱ Время: {timestamp}"
            
            result = self.send_message(int(self.log_peer_id), log_message)
            return result is not None
            
        except Exception as e:
            logger.error(f"Не удалось отправить лог: {str(e)}")
            return False

    def is_conversation_member(self, peer_id: int, user_id: int) -> bool:
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            items = conv_members.get("items", [])
            return any(item.get("member_id") == user_id for item in items)
        except Exception as e:
            logger.error(f"Error fetching conversation members: {str(e)}")
            return False

    def get_conversation_owner(self, peer_id: int) -> Optional[int]:
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            items = conv_members.get("items", [])
            for item in items:
                if item.get("is_owner", False):
                    return item.get("member_id")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении информации о создателе беседы: {str(e)}")
            return None

    def is_conversation_owner(self, peer_id: int, user_id: int) -> bool:
        owner_id = self.get_conversation_owner(peer_id)
        return owner_id == user_id

    def get_conversation_members(self, peer_id: int) -> List[Dict[str, Any]]:
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            profiles = conv_members.get("profiles", [])
            return [
                {
                    "id": profile["id"],
                    "first_name": profile["first_name"],
                    "last_name": profile["last_name"],
                    "online": profile.get("online", 0)
                }
                for profile in profiles
            ]
        except Exception as e:
            logger.error(f"Error fetching conversation members: {str(e)}")
            return []

    def get_online_members(self, peer_id: int) -> List[Dict[str, Any]]:
        members = self.get_conversation_members(peer_id)
        return [member for member in members if member.get("online", 0) == 1]

    def kick_user(self, peer_id: int, user_id: int) -> bool:
        try:
            self.vk.messages.removeChatUser(
                chat_id=peer_id - 2000000000,
                user_id=user_id
            )
            logger.info(f"Kicked user {user_id} from chat {peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to kick user: {str(e)}")
            return False

    def check_access(self, user_id: int, required_role: str, peer_id: Optional[int] = None) -> bool:
        if peer_id is not None:
            user_role = db.get_role(user_id, peer_id)
        else:
            user = db.get_user(user_id)
            if not user:
                return False
            user_role = user["role"]
            
        return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def get_user_role(self, user_id: int, peer_id: Optional[int] = None) -> str:
        if peer_id:
            role = db.get_role(user_id, peer_id)
            if role != 'user':
                return role
        
        user = db.get_user(user_id)
        if user:
            return user.get('role', 'user')
        return 'user'

    def set_user_role(self, user_id: int, role: str, peer_id: Optional[int] = None, admin_id: Optional[int] = None, reason: str = ""):
        db.set_role(user_id, role, peer_id)
        
        role_name = ROLE_NAMES.get(role, role)
        
        if admin_id:
            self.send_log_message("set_role", admin_id, user_id, peer_id, f"Должность: {role_name}\nПричина: {reason}")
        
        return True

    def has_rights(self, peer_id: int, user_id: int, required_role: str) -> bool:
        is_owner = self.is_conversation_owner(peer_id, user_id)
        has_role_access = self.check_access(user_id, required_role, peer_id)
        return is_owner or has_role_access

    def check_cooldown(self, user_id: int) -> bool:
        now = time.time()
        if user_id in self.last_command_time and now - self.last_command_time[user_id] < self.command_cooldown:
            logger.info(f"User {user_id} is on cooldown.")
            return False
        self.last_command_time[user_id] = now
        return True

    def is_muted(self, user_id: int) -> bool:
        mute_until = db.get_mute(user_id)
        now = int(time.time())
        return mute_until > now

    def is_banned(self, user_id: int) -> bool:
        return db.get_ban(user_id) is not None
        
    def extract_user_id_from_mention(self, mention: str) -> Optional[int]:
        try:
            first_word = mention.split()[0] if ' ' in mention else mention
            
            if first_word.isdigit():
                return int(first_word)
                
            if first_word.startswith("[") and "|" in first_word and "]" in first_word:
                start_idx = first_word.find("id") + 2
                end_idx = first_word.find("|")
                if start_idx > 1 and end_idx > start_idx:
                    user_id_str = first_word[start_idx:end_idx]
                    if user_id_str.isdigit():
                        return int(user_id_str)
            
            import re
            vk_url_patterns = [
                r"(?:https?://)?(?:www\.)?vk\.com/id(\d+)",
                r"(?:https?://)?(?:www\.)?vk\.me/id(\d+)",
            ]
            
            for pattern in vk_url_patterns:
                match = re.match(pattern, first_word)
                if match:
                    if len(match.groups()) > 0 and match.group(1).isdigit():
                        return int(match.group(1))
            
            if first_word.startswith("@"):
                screen_name = first_word[1:]
                try:
                    user_info = self.vk.users.get(user_ids=screen_name)
                    if user_info and len(user_info) > 0:
                        return user_info[0]["id"]
                except:
                    pass
            
            if ' ' in mention:
                id_match = re.search(r'\[id(\d+)\|[^\]]+\]', mention)
                if id_match:
                    return int(id_match.group(1))
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении ID из упоминания: {str(e)}")
            return None
            
    def get_user_id_from_reply(self, message) -> Optional[int]:
        try:
            if "reply_message" in message:
                reply = message["reply_message"]
                if "from_id" in reply:
                    return reply["from_id"]
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении ID из ответа: {str(e)}")
            return None

    def handle_message(self, event):
        message = event.obj.message
        peer_id = message['peer_id']
        user_id = message['from_id']
        text = message.get('text', '').strip()
        
        db.add_user(user_id)
        db.update_message_count(user_id)
        
        if text.startswith('/'):
            self.handle_command(peer_id, user_id, text, message)
        else:
            if self.log_peer_id and peer_id > 2000000000:
                log_text = text[:97] + "..." if len(text) > 100 else text
                self.send_log_message(
                    action="message",
                    admin_id=user_id,
                    peer_id=peer_id,
                    details=log_text
                )
            
            if self.is_muted(user_id) and not self.check_access(user_id, "moderator"):
                mute_until = db.get_mute(user_id)
                time_left = mute_until - int(time.time())
                if time_left > 0:
                    message_id = message.get('id')
                    if message_id:
                        if not self.delete_message(peer_id, message_id):
                            logger.error(f"Не могу удалить сообщение {message_id}")
                    
                    self.send_message(
                        peer_id, 
                        f"[id{user_id}|Пользователь], вы в муте. "
                        f"Осталось: {format_time_delta(time_left)}"
                    )

    def handle_command(self, peer_id: int, user_id: int, text: str, message=None):
        command, args = parse_command(text)
        
        is_owner = self.is_conversation_owner(peer_id, user_id)
        if self.quiet_mode and not self.check_access(user_id, "moderator") and not is_owner:
            logger.info(f"Игнор команды от {user_id} в тихом режиме")
            return
            
        if not self.check_cooldown(user_id):
            self.send_message(peer_id, f"[id{user_id}|Пользователь], не спешите!")
            return
            
        if not self.commands.has_command(command):
            return
        
        cmd_requires_target = ["warn", "unwarn", "warns", "kick", "ban", "unban", 
                               "mute", "unmute", "muted", "setrole", "removerole",
                               "transfer", "give", "duel", "hug", "kiss", "hit"]
        
        if message and command in cmd_requires_target:
            if "reply_message" in message and (not args or (not args[0].isdigit() and not args.startswith("[") and not args.startswith("@"))):
                target_id = self.get_user_id_from_reply(message)
                if target_id:
                    if command in ["unwarn", "warns", "kick", "unban", "unmute", "muted", "removerole"]:
                        args = str(target_id)
                    elif args:
                        args = str(target_id) + " " + args
                    else:
                        args = str(target_id)
            
        if args and command in cmd_requires_target:
            parts = args.split(" ", 1)
            first_arg = parts[0]
            
            if (first_arg.startswith("[") and "|" in first_arg) or first_arg.startswith("@"):
                target_id = self.extract_user_id_from_mention(first_arg)
                if target_id:
                    if len(parts) > 1:
                        args = str(target_id) + " " + parts[1]
                    else:
                        args = str(target_id)
            
        self.executor.submit(
            self.commands.execute_command,
            command, peer_id, user_id, args
        )

    def process_events(self):
        try:
            for event in self.longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    self.executor.submit(self.handle_message, event)
        except Exception as e:
            logger.error(f"Ошибка в событиях: {str(e)}")
            time.sleep(5)

    def process_delete_queue(self):
        while True:
            try:
                time.sleep(1)
                with self.delete_lock:
                    messages_to_delete = self.delete_queue.copy()
                    self.delete_queue = []
                for peer_id, message_id in messages_to_delete:
                    self.delete_message(peer_id, message_id)
            except Exception as e:
                logger.error(f"Не могу разобрать очередь удаления: {str(e)}")
                time.sleep(5)

    def start_polling(self):
        threading.Thread(
            target=self.process_delete_queue, 
            daemon=True
        ).start()
        
        while True:
            try:
                self.process_events()
            except Exception as e:
                logger.error(f"Основной цикл упал: {str(e)}")
                time.sleep(5)
