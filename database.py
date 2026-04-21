import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'vk_bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'user',
            coins INTEGER DEFAULT 0,
            tickets INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            mute_until INTEGER DEFAULT 0,
            ban_reason TEXT,
            daily_streak INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            last_weekly INTEGER DEFAULT 0,
            last_work INTEGER DEFAULT 0,
            experience INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            peer_id INTEGER,
            role TEXT DEFAULT 'user',
            PRIMARY KEY (user_id, peer_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            peer_id INTEGER,
            reason TEXT,
            admin_id INTEGER,
            timestamp INTEGER,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER,
            peer_id INTEGER,
            reason TEXT,
            admin_id INTEGER,
            timestamp INTEGER,
            PRIMARY KEY (user_id, peer_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item TEXT,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_commands (
            name TEXT,
            response TEXT,
            user_id INTEGER,
            is_global INTEGER DEFAULT 0,
            PRIMARY KEY (name, user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            peer_id INTEGER PRIMARY KEY,
            welcome_message TEXT,
            rules TEXT,
            slow_mode INTEGER DEFAULT 0,
            quiet_mode INTEGER DEFAULT 0,
            ban_links INTEGER DEFAULT 0,
            ban_swear INTEGER DEFAULT 0,
            ban_caps INTEGER DEFAULT 0,
            logs_enabled INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ignored_users (
            user_id INTEGER,
            peer_id INTEGER,
            admin_id INTEGER,
            timestamp INTEGER,
            PRIMARY KEY (user_id, peer_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def add_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_user(user_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in kwargs.items():
        cursor.execute(f'UPDATE users SET {key} = ? WHERE id = ?', (value, user_id))
    conn.commit()
    conn.close()

def get_role(user_id, peer_id=None):
    conn = get_db()
    cursor = conn.cursor()
    
    if peer_id:
        cursor.execute('SELECT role FROM user_roles WHERE user_id = ? AND peer_id = ?', (user_id, peer_id))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row['role']
    
    cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['role'] if row else 'user'

def set_role(user_id, role, peer_id=None):
    conn = get_db()
    cursor = conn.cursor()
    
    if peer_id:
        cursor.execute('''
            INSERT OR REPLACE INTO user_roles (user_id, peer_id, role)
            VALUES (?, ?, ?)
        ''', (user_id, peer_id, role))
    else:
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
    
    conn.commit()
    conn.close()

def update_message_count(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET messages_count = messages_count + 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_warning(user_id, peer_id, reason, admin_id):
    conn = get_db()
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp())
    cursor.execute('''
        INSERT INTO warnings (user_id, peer_id, reason, admin_id, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, peer_id, reason, admin_id, timestamp))
    cursor.execute('UPDATE users SET warnings = warnings + 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_warnings(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM warnings WHERE user_id = ? AND is_active = 1', (user_id,))
    warnings = cursor.fetchall()
    conn.close()
    return [dict(w) for w in warnings]

def remove_warning(warning_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE warnings SET is_active = 0 WHERE id = ?', (warning_id,))
    cursor.execute('UPDATE users SET warnings = warnings - 1 WHERE id = (SELECT user_id FROM warnings WHERE id = ?)', (warning_id,))
    conn.commit()
    conn.close()

def set_mute(user_id, duration):
    mute_until = int(datetime.now().timestamp()) + duration
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET mute_until = ? WHERE id = ?', (mute_until, user_id))
    conn.commit()
    conn.close()

def get_mute(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT mute_until FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['mute_until'] if row else 0

def set_ban(user_id, peer_id, reason, admin_id):
    conn = get_db()
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp())
    cursor.execute('''
        INSERT OR REPLACE INTO bans (user_id, peer_id, reason, admin_id, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, peer_id, reason, admin_id, timestamp))
    cursor.execute('UPDATE users SET ban_reason = ? WHERE id = ?', (reason, user_id))
    conn.commit()
    conn.close()

def get_ban(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bans WHERE user_id = ?', (user_id,))
    ban = cursor.fetchone()
    conn.close()
    return dict(ban) if ban else None

def remove_ban(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
    cursor.execute('UPDATE users SET ban_reason = NULL WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_coins(user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def remove_coins(user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET coins = coins - ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT coins FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['coins'] if row else 0

def add_item(user_id, item, quantity=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory (user_id, item, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item) DO UPDATE SET quantity = quantity + ?
    ''', (user_id, item, quantity, quantity))
    conn.commit()
    conn.close()

def get_inventory(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT item, quantity FROM inventory WHERE user_id = ?', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return [dict(item) for item in items]

def add_custom_command(name, response, user_id, is_global=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO custom_commands (name, response, user_id, is_global)
        VALUES (?, ?, ?, ?)
    ''', (name.lower(), response, user_id, 1 if is_global else 0))
    conn.commit()
    conn.close()

def remove_custom_command(name, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM custom_commands WHERE name = ? AND user_id = ?', (name.lower(), user_id))
    conn.commit()
    conn.close()

def get_user_commands(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, response FROM custom_commands WHERE user_id = ?', (user_id,))
    commands = cursor.fetchall()
    conn.close()
    return [dict(cmd) for cmd in commands]

def get_chat_settings(peer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chat_settings WHERE peer_id = ?', (peer_id,))
    settings = cursor.fetchone()
    conn.close()
    return dict(settings) if settings else {}

def set_chat_settings(peer_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    
    current = get_chat_settings(peer_id)
    if current:
        for key, value in kwargs.items():
            cursor.execute(f'UPDATE chat_settings SET {key} = ? WHERE peer_id = ?', (value, peer_id))
    else:
        keys = ['peer_id'] + list(kwargs.keys())
        values = [peer_id] + list(kwargs.values())
        placeholders = ','.join(['?'] * len(keys))
        cursor.execute(f'INSERT INTO chat_settings ({",".join(keys)}) VALUES ({placeholders})', values)
    
    conn.commit()
    conn.close()

def add_ignored(user_id, peer_id, admin_id=None):
    conn = get_db()
    cursor = conn.cursor()
    timestamp = int(datetime.now().timestamp())
    cursor.execute('''
        INSERT OR REPLACE INTO ignored_users (user_id, peer_id, admin_id, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, peer_id, admin_id, timestamp))
    conn.commit()
    conn.close()

def remove_ignored(user_id, peer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ignored_users WHERE user_id = ? AND peer_id = ?', (user_id, peer_id))
    conn.commit()
    conn.close()

def is_ignored(user_id, peer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM ignored_users WHERE user_id = ? AND peer_id = ?', (user_id, peer_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None
