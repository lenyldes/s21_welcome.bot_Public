import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logging():
    """
    Настройка системы логирования для сервиса
    """
    
    # === ПАПКА ДЛЯ ЛОГОВ ===
    # Указывает папку, где будут храниться файлы логов
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.getenv("LOGS_DIR", os.path.join(base_dir, "logs"))
    
    # === СОЗДАНИЕ ПАПКИ ===
    # Создает папку для логов, если она не существует
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # === ФОРМАТ ЛОГОВ ===
    # Определяет как будет выглядеть каждая строка лога:
    # - %(asctime)s - дата и время
    # - %(name)s - имя логгера
    # - %(levelname)s - уровень (INFO, WARNING, ERROR и т.д.)
    # - %(message)s - текст сообщения
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'  # Формат даты и времени
    )
    
    # === ОСНОВНОЙ УРОВЕНЬ ЛОГИРОВАНИЯ ===
    # Устанавливает минимальный уровень логирования для корневого логгера:
    # DEBUG < INFO < WARNING < ERROR < CRITICAL
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # === ФАЙЛОВЫЙ ОБРАБОТЧИК С РОТАЦИЕЙ ПО ВРЕМЕНИ ===
    # Записывает логи в файл с ротацией по времени (раз в сутки).
    # backupCount=0 означает хранить ВСЕ файлы бэкапа бессрочно.
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'bot_service.log'),  # Путь к файлу лога
        when='midnight',     # Ротация в полночь
        interval=1,          # Интервал - каждый день
        backupCount=0,       # 0 = Бессрочное хранение всех файлов логов
        encoding='utf-8',    # Кодировка для поддержки русских символов
        utc=False            # Использовать локальное время
    )
    file_handler.setFormatter(formatter)  # Применяем формат к обработчику
    file_handler.setLevel(logging.INFO)   # Уровень для файлового вывода
    
    # === КОНСОЛЬНЫЙ ОБРАБОТЧИК ===
    # Выводит логи в консоль (терминал)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)   # Применяем формат к обработчику
    console_handler.setLevel(logging.INFO)    # Уровень для консольного вывода
    
    # === ДОБАВЛЕНИЕ ОБРАБОТЧИКОВ ===
    # Добавляем оба обработчика к основному логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # === НАСТРОЙКА ЛОГГЕРОВ СТОРОННИХ БИБЛИОТЕК ===
    # Уменьшаем verbosity (подробность) логов для telebot и urllib3/requests
    # чтобы избежать спама в логах
    for lib_name in ['telebot', 'TeleBot', 'urllib3', 'requests', 'httpx']:
        logging.getLogger(lib_name).setLevel(logging.WARNING)
    
    # === ЗАПИСЬ О НАЧАЛЕ РАБОТЫ ===
    # Первая запись в лог после инициализации
    logging.info("=== Logging system initialized (Infinite Retention) ===")
    
    return logger