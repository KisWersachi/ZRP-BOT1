import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        logger.error(f"Файл конфигурации не найден: {config_path}")
        raise FileNotFoundError(f"config.json not found at {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_fields = ['group_id', 'token', 'command_cooldown']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Отсутствует поле: {field}")
        
        logger.info(f"Конфиг загружен: group_id={config['group_id']}")
        
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга config.json: {e}")
        raise
