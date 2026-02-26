# Настройки мониторинга
MONITORING_CONFIG = {
    'default': {
        'check_interval': 1,  # секунды между проверками
        'batch_size': 10,     # размер батча для проверки пропущенных
        'max_skips': 100,     # максимальное количество пропусков перед переходом
        'retry_delay': 1,     # задержка при ошибке
        'concurrent_requests': 20,  # максимальное количество одновременных запросов
    },
    'aggressive': {
        'check_interval': 0.5,
        'batch_size': 20,
        'max_skips': 50,
        'retry_delay': 0.5,
        'concurrent_requests': 30,
    },
    'conservative': {
        'check_interval': 2,
        'batch_size': 5,
        'max_skips': 200,
        'retry_delay': 2,
        'concurrent_requests': 10,
    }
}

# Текущий режим
CURRENT_MODE = 'aggressive'