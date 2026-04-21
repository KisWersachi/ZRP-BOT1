import logging
import random
import time
import re
from typing import Optional

import database as db
from utils import parse_time, format_time_delta

logger = logging.getLogger(__name__)

LEVEL_TO_ROLE = {
    10: "creator",
    9: "owner",
    8: "special_admin",
    7: "senior_admin",
    6: "admin",
    5: "senior_moderator",
    4: "moderator",
    3: "junior_moderator",
    2: "assistant",
    1: "user"
}

ROLE_TO_LEVEL = {v: k for k, v in LEVEL_TO_ROLE.items()}

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

class CommandRegistry:
    def __init__(self, bot):
        self.bot = bot
        self.commands = {}
        self._register_all_commands()
    
    def _register_all_commands(self):
        # Основные
        self.commands['help'] = self.cmd_help
        self.commands['profile'] = self.cmd_profile
        self.commands['stats'] = self.cmd_stats
        self.commands['online'] = self.cmd_online
        self.commands['chat'] = self.cmd_chat_info
        self.commands['role'] = self.cmd_my_role
        self.commands['staff'] = self.cmd_staff
        self.commands['roles'] = self.cmd_role_list
        
        # Модерация
        self.commands['warn'] = self.cmd_warn
        self.commands['unwarn'] = self.cmd_unwarn
        self.commands['warns'] = self.cmd_warns
        self.commands['kick'] = self.cmd_kick
        self.commands['mute'] = self.cmd_mute
        self.commands['unmute'] = self.cmd_unmute
        self.commands['muted'] = self.cmd_muted_list
        self.commands['ban'] = self.cmd_ban
        self.commands['unban'] = self.cmd_unban
        self.commands['clear'] = self.cmd_clear
        self.commands['quiet'] = self.cmd_quiet_mode
        
        # Управление ролями
        self.commands['setrole'] = self.cmd_set_role
        self.commands['removerole'] = self.cmd_remove_role
        self.commands['myrole'] = self.cmd_my_role
        
        # Экономика
        self.commands['balance'] = self.cmd_balance
        self.commands['daily'] = self.cmd_daily
        self.commands['work'] = self.cmd_work
        self.commands['top'] = self.cmd_top
        self.commands['transfer'] = self.cmd_transfer
        self.commands['shop'] = self.cmd_shop
        self.commands['buy'] = self.cmd_buy
        
        # Игры
        self.commands['casino'] = self.cmd_casino
        self.commands['slots'] = self.cmd_slots
        self.commands['duel'] = self.cmd_duel
        self.commands['dice'] = self.cmd_dice
        self.commands['coin'] = self.cmd_coin
        self.commands['roll'] = self.cmd_roll
        
        # RP
        self.commands['me'] = self.cmd_me
        self.commands['do'] = self.cmd_do
        self.commands['try'] = self.cmd_try
        self.commands['8ball'] = self.cmd_8ball
        self.commands['hug'] = self.cmd_hug
        self.commands['kiss'] = self.cmd_kiss
        self.commands['hit'] = self.cmd_hit
        self.commands['inventory'] = self.cmd_inventory
        
        # Кастомные команды
        self.commands['createcmd'] = self.cmd_create_command
        self.commands['mycmds'] = self.cmd_my_commands
        self.commands['delcmd'] = self.cmd_delete_command
        
        logger.info(f"Registered {len(self.commands)} commands")
    
    def has_command(self, command):
        return command in self.commands
    
    def execute_command(self, command, peer_id, user_id, args):
        try:
            if command in self.commands:
                self.commands[command](peer_id, user_id, args)
            else:
                self.bot.send_message(peer_id, f"❌ Неизвестная команда. /help")
        except Exception as e:
            logger.error(f"Error: {e}")
            self.bot.send_message(peer_id, f"❌ Ошибка")
    
    # ========== ОСНОВНЫЕ ==========
    
    def cmd_help(self, peer_id, user_id, args):
        help_text = """📋 **Команды бота**

**💰 Экономика:**
/balance - баланс
/daily - бонус
/work - работа
/top - топ богатых
/transfer @user 100 - перевод

**🎲 Игры:**
/casino 100 - казино
/slots 50 - слоты
/duel @user 100 - дуэль
/dice 100 - кости
/coin - монетка
/roll - кубик

**🎭 RP:**
/me действие - *действие*
/do описание - *описание*
/try действие - попытка
/hug @user - обнять
/kiss @user - поцеловать

**👑 Админ:**
/warn @user - варн
/kick @user - кик
/mute @user 1h - мут
/ban @user - бан
/clear 10 - очистка
/setrole @user 5 - назначить роль

**ℹ️ Инфо:**
/profile @user - профиль
/online - онлайн
/staff - админы
/roles - список ролей"""
        self.bot.send_message(peer_id, help_text)
    
    def cmd_role_list(self, peer_id, user_id, args):
        roles_text = """**Роли (0-9):**

9 👑 Создатель
8 ⭐ Владелец
7 🔰 Спец. админ
6 📌 Гл. админ
5 ⚙️ Администратор
4 🛡️ Ст. модератор
3 🔨 Модератор
2 📋 Мл. модератор
1 🤝 Помощник
0 👤 Пользователь

/setrole @user 5"""
        self.bot.send_message(peer_id, roles_text)
    
    def cmd_profile(self, peer_id, user_id, args):
        target_id = self._get_target_id(args, user_id)
        user = db.get_user(target_id)
        if not user:
            self.bot.send_message(peer_id, "❌ Не найден")
            return
        
        role = self.bot.get_user_role(target_id, peer_id)
        role_name = ROLE_NAMES.get(role, "👤 Пользователь")
        
        text = f"""👤 **Профиль**
ID: {target_id}
Роль: {role_name}
💰 Монет: {user.get('coins', 0)}
📊 Сообщений: {user.get('messages_count', 0)}
⚠️ Варнов: {user.get('warnings', 0)}"""
        self.bot.send_message(peer_id, text)
    
    def cmd_online(self, peer_id, user_id, args):
        if peer_id < 2000000000:
            self.bot.send_message(peer_id, "❌ Только в беседах")
            return
        
        members = self.bot.get_online_members(peer_id)
        if not members:
            self.bot.send_message(peer_id, "📡 Никого нет")
            return
        
        names = [f"{m['first_name']} {m['last_name']}" for m in members[:20]]
        self.bot.send_message(peer_id, f"🟢 **Онлайн ({len(members)}):**\n" + "\n".join(names))
    
    # ========== МОДЕРАЦИЯ ==========
    
    def cmd_warn(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "moderator", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        parts = args.split(' ', 1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /warn @user причина")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        reason = parts[1]
        db.add_warning(target_id, peer_id, reason, user_id)
        self.bot.send_message(peer_id, f"⚠️ Варн [id{target_id}|пользователю]\nПричина: {reason}")
    
    def cmd_kick(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "moderator", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        target_id = self._get_target_id(args, None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        if self.bot.kick_user(peer_id, target_id):
            self.bot.send_message(peer_id, f"👢 [id{target_id}|Пользователь] кикнут")
    
    def cmd_mute(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "moderator", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        parts = args.split(' ', 2)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /mute @user 1h причина")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        duration = parse_time(parts[1])
        db.set_mute(target_id, duration)
        self.bot.send_message(peer_id, f"🔇 Мут на {format_time_delta(duration)}")
    
    def cmd_ban(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "admin", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        parts = args.split(' ', 1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /ban @user причина")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        reason = parts[1]
        db.set_ban(target_id, peer_id, reason, user_id)
        self.bot.kick_user(peer_id, target_id)
        self.bot.send_message(peer_id, f"🚫 Бан [id{target_id}|пользователя]\nПричина: {reason}")
    
    def cmd_clear(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "moderator", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        try:
            count = int(args) if args else 10
            count = min(count, 50)
        except:
            count = 10
        
        self.bot.send_message(peer_id, f"🗑️ Очищено {count} сообщений")
    
    # ========== УПРАВЛЕНИЕ РОЛЯМИ ==========
    
    def cmd_set_role(self, peer_id, user_id, args):
        if not self.bot.check_access(user_id, "admin", peer_id):
            self.bot.send_message(peer_id, "❌ Нет прав")
            return
        
        parts = args.split(' ', 1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /setrole @user 0-9")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        try:
            level = int(parts[1])
            if level < 0 or level > 9:
                self.bot.send_message(peer_id, "❌ Уровень 0-9")
                return
            
            role = LEVEL_TO_ROLE.get(level, 'user')
            role_name = ROLE_NAMES.get(role, '👤 Пользователь')
            
            user_level = ROLE_TO_LEVEL.get(self.bot.get_user_role(user_id, peer_id), 1)
            if level >= user_level and user_level < 9:
                self.bot.send_message(peer_id, "❌ Нельзя назначить роль выше своей")
                return
            
            self.bot.set_user_role(target_id, role, peer_id, user_id, f"Назначена роль {role_name}")
            self.bot.send_message(peer_id, f"✅ [id{target_id}|Пользователь] получил роль {role_name}")
        except ValueError:
            self.bot.send_message(peer_id, "❌ Уровень должен быть числом")
    
    # ========== ЭКОНОМИКА ==========
    
    def cmd_balance(self, peer_id, user_id, args):
        target_id = self._get_target_id(args, user_id)
        balance = db.get_coins(target_id)
        self.bot.send_message(peer_id, f"💰 Баланс: {balance} монет")
    
    def cmd_daily(self, peer_id, user_id, args):
        user = db.get_user(user_id)
        now = int(time.time())
        last_daily = user.get('last_daily', 0)
        streak = user.get('daily_streak', 0)
        
        if now - last_daily < 86400:
            remaining = 86400 - (now - last_daily)
            self.bot.send_message(peer_id, f"⏰ Бонус через {self._format_time(remaining)}")
            return
        
        if now - last_daily < 172800:
            streak += 1
        else:
            streak = 1
        
        bonus = 50 + min(streak * 10, 100)
        db.add_coins(user_id, bonus)
        db.update_user(user_id, daily_streak=streak, last_daily=now)
        
        self.bot.send_message(peer_id, f"🎁 +{bonus} монет!\n📅 Серия: {streak} дней")
    
    def cmd_work(self, peer_id, user_id, args):
        user = db.get_user(user_id)
        last_work = user.get('last_work', 0)
        now = int(time.time())
        
        if now - last_work < 3600:
            remaining = 3600 - (now - last_work)
            self.bot.send_message(peer_id, f"⏰ Работа через {self._format_time(remaining)}")
            return
        
        earnings = random.randint(20, 50)
        db.add_coins(user_id, earnings)
        db.update_user(user_id, last_work=now)
        
        jobs = ["сделал заказ", "помог клиенту", "выполнил задание"]
        job = random.choice(jobs)
        
        self.bot.send_message(peer_id, f"💼 Вы {job} и заработали {earnings} монет!")
    
    def cmd_transfer(self, peer_id, user_id, args):
        parts = args.split(' ', 1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /transfer @user 100")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        try:
            amount = int(parts[1])
            if amount <= 0:
                self.bot.send_message(peer_id, "❌ Сумма > 0")
                return
        except:
            self.bot.send_message(peer_id, "❌ Укажите сумму")
            return
        
        if db.get_coins(user_id) < amount:
            self.bot.send_message(peer_id, "❌ Недостаточно монет")
            return
        
        db.remove_coins(user_id, amount)
        db.add_coins(target_id, amount)
        self.bot.send_message(peer_id, f"✅ Передано {amount} монет")
    
    def cmd_top(self, peer_id, user_id, args):
        conn = db.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, coins FROM users ORDER BY coins DESC LIMIT 10')
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            self.bot.send_message(peer_id, "📊 Топ пуст")
            return
        
        text = "🏆 **Топ богатых:**\n"
        for i, user in enumerate(users, 1):
            try:
                info = self.bot.vk.users.get(user_ids=user['id'])[0]
                name = f"{info['first_name']} {info['last_name']}"
                text += f"{i}. {name} - {user['coins']} 🪙\n"
            except:
                text += f"{i}. ID:{user['id']} - {user['coins']} 🪙\n"
        
        self.bot.send_message(peer_id, text)
    
    # ========== ИГРЫ ==========
    
    def cmd_casino(self, peer_id, user_id, args):
        try:
            bet = int(args) if args else 0
            if bet < 10:
                self.bot.send_message(peer_id, "❌ Ставка минимум 10")
                return
            
            if db.get_coins(user_id) < bet:
                self.bot.send_message(peer_id, "❌ Недостаточно монет")
                return
            
            if random.random() < 0.48:
                win = int(bet * 1.9)
                db.add_coins(user_id, win - bet)
                self.bot.send_message(peer_id, f"🎰 Выиграли {win} монет!")
            else:
                db.remove_coins(user_id, bet)
                self.bot.send_message(peer_id, f"😞 Проиграли {bet} монет")
        except:
            self.bot.send_message(peer_id, "❌ Укажите ставку")
    
    def cmd_slots(self, peer_id, user_id, args):
        try:
            bet = int(args) if args else 0
            if bet < 10:
                self.bot.send_message(peer_id, "❌ Ставка минимум 10")
                return
            
            if db.get_coins(user_id) < bet:
                self.bot.send_message(peer_id, "❌ Недостаточно монет")
                return
            
            symbols = ['🍒', '🍋', '🍊', '🍉', '⭐', '💎']
            result = [random.choice(symbols) for _ in range(3)]
            result_str = ' '.join(result)
            
            if result[0] == result[1] == result[2]:
                win = bet * 5
                db.add_coins(user_id, win)
                self.bot.send_message(peer_id, f"🎰 ДЖЕКПОТ! {result_str}\n+{win} монет!")
            elif result[0] == result[1] or result[1] == result[2]:
                win = bet * 2
                db.add_coins(user_id, win)
                self.bot.send_message(peer_id, f"🎰 {result_str}\n+{win} монет!")
            else:
                db.remove_coins(user_id, bet)
                self.bot.send_message(peer_id, f"🎰 {result_str}\n-{bet} монет")
        except:
            self.bot.send_message(peer_id, "❌ Укажите ставку")
    
    def cmd_duel(self, peer_id, user_id, args):
        parts = args.split(' ')
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /duel @user 100")
            return
        
        target_id = self._get_target_id(parts[0], None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        try:
            bet = int(parts[1])
            if bet < 10:
                self.bot.send_message(peer_id, "❌ Ставка минимум 10")
                return
            
            if db.get_coins(user_id) < bet:
                self.bot.send_message(peer_id, "❌ У вас нет монет")
                return
            
            if db.get_coins(target_id) < bet:
                self.bot.send_message(peer_id, "❌ У соперника нет монет")
                return
            
            user_roll = random.randint(1, 6)
            target_roll = random.randint(1, 6)
            
            if user_roll > target_roll:
                db.add_coins(user_id, bet)
                db.remove_coins(target_id, bet)
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Соперник: {target_roll}\n✅ +{bet} монет!")
            elif user_roll < target_roll:
                db.remove_coins(user_id, bet)
                db.add_coins(target_id, bet)
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Соперник: {target_roll}\n❌ -{bet} монет")
            else:
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Соперник: {target_roll}\n🤝 Ничья")
        except:
            self.bot.send_message(peer_id, "❌ Укажите ставку")
    
    def cmd_dice(self, peer_id, user_id, args):
        try:
            bet = int(args) if args else 0
            if bet < 10:
                self.bot.send_message(peer_id, "❌ Ставка минимум 10")
                return
            
            if db.get_coins(user_id) < bet:
                self.bot.send_message(peer_id, "❌ Недостаточно монет")
                return
            
            user_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            
            if user_roll > bot_roll:
                win = bet * 2
                db.add_coins(user_id, win)
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Бот: {bot_roll}\n✅ +{win} монет!")
            elif user_roll < bot_roll:
                db.remove_coins(user_id, bet)
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Бот: {bot_roll}\n❌ -{bet} монет")
            else:
                self.bot.send_message(peer_id, f"🎲 Вы: {user_roll} | Бот: {bot_roll}\n🤝 Ничья")
        except:
            self.bot.send_message(peer_id, "❌ Укажите ставку")
    
    def cmd_roll(self, peer_id, user_id, args):
        max_val = 100
        if args and args.isdigit():
            max_val = int(args)
        
        result = random.randint(1, max_val)
        self.bot.send_message(peer_id, f"🎲 *Выпало {result} из {max_val}*")
    
    def cmd_coin(self, peer_id, user_id, args):
        result = random.choice(['Орёл', 'Решка'])
        self.bot.send_message(peer_id, f"🪙 *{result}*")
    
    # ========== RP ==========
    
    def cmd_me(self, peer_id, user_id, args):
        if not args:
            self.bot.send_message(peer_id, "❌ Укажите действие")
            return
        
        info = self.bot.vk.users.get(user_ids=user_id)[0]
        name = f"{info['first_name']} {info['last_name']}"
        self.bot.send_message(peer_id, f"*{name} {args}*")
    
    def cmd_hug(self, peer_id, user_id, args):
        target_id = self._get_target_id(args, None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        user_info = self.bot.vk.users.get(user_ids=user_id)[0]
        target_info = self.bot.vk.users.get(user_ids=target_id)[0]
        name = f"{user_info['first_name']} {user_info['last_name']}"
        target_name = f"{target_info['first_name']} {target_info['last_name']}"
        
        self.bot.send_message(peer_id, f"🤗 *{name} обнял(а) {target_name}*")
    
    def cmd_kiss(self, peer_id, user_id, args):
        target_id = self._get_target_id(args, None)
        if not target_id:
            self.bot.send_message(peer_id, "❌ Укажите пользователя")
            return
        
        user_info = self.bot.vk.users.get(user_ids=user_id)[0]
        target_info = self.bot.vk.users.get(user_ids=target_id)[0]
        name = f"{user_info['first_name']} {user_info['last_name']}"
        target_name = f"{target_info['first_name']} {target_info['last_name']}"
        
        self.bot.send_message(peer_id, f"💋 *{name} поцеловал(а) {target_name}*")
    
    # ========== КАСТОМНЫЕ КОМАНДЫ ==========
    
    def cmd_create_command(self, peer_id, user_id, args):
        parts = args.split(' ', 1)
        if len(parts) < 2:
            self.bot.send_message(peer_id, "❌ /createcmd название ответ")
            return
        
        name = parts[0].lower()
        if not name.startswith('/'):
            name = '/' + name
        
        response = parts[1]
        
        db.add_custom_command(name, response, user_id)
        self.bot.send_message(peer_id, f"✅ Команда {name} создана!")
    
    def cmd_my_commands(self, peer_id, user_id, args):
        cmds = db.get_user_commands(user_id)
        if not cmds:
            self.bot.send_message(peer_id, "📝 Нет команд")
            return
        
        text = "📝 **Ваши команды:**\n" + "\n".join([c['name'] for c in cmds[:15]])
        self.bot.send_message(peer_id, text)
    
    def cmd_delete_command(self, peer_id, user_id, args):
        if not args:
            self.bot.send_message(peer_id, "❌ Укажите название")
            return
        
        name = args.lower()
        if not name.startswith('/'):
            name = '/' + name
        
        db.remove_custom_command(name, user_id)
        self.bot.send_message(peer_id, f"✅ Команда {name} удалена")
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ==========
    
    def _get_target_id(self, arg, default_id=None):
        if not arg:
            return default_id
        
        if str(arg).isdigit():
            return int(arg)
        
        match = re.search(r'\[id(\d+)\|', arg)
        if match:
            return int(match.group(1))
        
        if arg.startswith('@'):
            try:
                users = self.bot.vk.users.get(user_ids=arg[1:])
                if users:
                    return users[0]['id']
            except:
                pass
        
        return default_id
    
    def _format_time(self, seconds):
        if seconds <= 0:
            return "сейчас"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        return f"{minutes}м"
