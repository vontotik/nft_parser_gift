from pydantic_settings import BaseSettings
import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEfrom pydantic_settings import BaseSettings
import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Additional tokens are ignored now – we use only the main one
    TELEGRAM_BOT_TOKEN_2: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_2", "")
    TELEGRAM_BOT_TOKEN_3: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_3", "")
    TELEGRAM_BOT_TOKEN_4: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_4", "")
    TELEGRAM_BOT_TOKEN_5: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_5", "")
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# ID чата для отправки сообщений
CHAT_ID = ""

# Настройки мониторинга
MONITORING_SETTINGS = {
    'rate_limit_per_second': 0.1,
    'timeout': 20,
}

def get_all_bot_tokens() -> List[str]:
    """Возвращает только основной токен (используем одного бота)"""
    tokens = []
    if settings.TELEGRAM_BOT_TOKEN:
        tokens.append(settings.TELEGRAM_BOT_TOKEN)
    return tokens

BOT_TOKENS = get_all_bot_tokens()

if not BOT_TOKENS:
    print("❌ ОШИБКА: Не найден токен бота в .env файле!")
    print("Добавьте TELEGRAM_BOT_TOKEN=ваш_токен")
    exit(1)GRAM_BOT_TOKEN")
    
    # Дополнительные токены ботов
    TELEGRAM_BOT_TOKEN_2: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_2", "")
    TELEGRAM_BOT_TOKEN_3: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_3", "")
    TELEGRAM_BOT_TOKEN_4: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_4", "")
    TELEGRAM_BOT_TOKEN_5: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN_5", "")
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# ID чата для отправки сообщений
CHAT_ID = ""  # Замените на ваш ID чата

# Настройки мониторинга
MONITORING_SETTINGS = {
    'rate_limit_per_second': 0.1,
    'timeout': 20,
}

# Получаем все доступные токены ботов
def get_all_bot_tokens() -> List[str]:
    """Получает все доступные токены ботов"""
    tokens = []
    
    # Основной токен
    if settings.TELEGRAM_BOT_TOKEN:
        tokens.append(settings.TELEGRAM_BOT_TOKEN)
    
    # Дополнительные токены
    for i in range(2, 6):
        token_name = f"TELEGRAM_BOT_TOKEN_{i}"
        token_value = getattr(settings, token_name, None)
        if token_value and token_value.strip():
            tokens.append(token_value.strip())
    
    return tokens

# Список всех доступных токенов
BOT_TOKENS = get_all_bot_tokens()

# Если нет токенов, выводим ошибку
if not BOT_TOKENS:
    print("❌ ОШИБКА: Не найден ни один токен бота в .env файле!")
    print("Добавьте хотя бы один токен: TELEGRAM_BOT_TOKEN=ваш_токен")
    exit(1)