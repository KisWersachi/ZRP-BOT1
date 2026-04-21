import random
import re
import time
from datetime import datetime, timedelta

def parse_command(text):
    parts = text.strip().split()
    if not parts:
        return '', ''
    
    command = parts[0].lower()
    args = ' '.join(parts[1:]) if len(parts) > 1 else ''
    
    return command, args

def parse_time(time_str):
    if not time_str:
        return 3600
    
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
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if secs > 0 and not parts:
        parts.append(f"{secs} сек")
    
    return ' '.join(parts) if parts else "0 сек"

def get_random_number(min_val=1, max_val=100):
    return random.randint(min_val, max_val)

def chance(percent):
    return random.randint(1, 100) <= percent

def format_date(timestamp):
    if not timestamp:
        return "неизвестно"
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")

def clean_text(text, max_len=500):
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len-3] + "..."
    return text

def extract_mentions(text):
    pattern = r'\[id(\d+)\|([^\]]+)\]'
    return re.findall(pattern, text)

def is_all_mention(text):
    return text and text.lower().strip() == '@all'
