import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'is_used_link_from_username.db')

class IsUsedLinkFromUsernameDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """
        Инициализация базы данных
        
        Args:
            db_path (str): Путь к файлу базы данных
        """
        self.db_path = db_path
        self._create_table()
    
    def _create_table(self) -> None:
        """Создание таблицы если она не существует"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли таблица
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='username_used_links'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS username_used_links (
                        username TEXT PRIMARY KEY,
                        is_used_link BOOLEAN NOT NULL DEFAULT FALSE,
                        link TEXT,
                        created_at TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица username_used_links")
                else:
                    logging.info("Загружена существующая таблица username_used_links")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def get_all_links(self) -> Dict[str, Dict]:
        """
        Получить все записи о выданных ссылках
        
        Returns:
            Dict[str, Dict]: Словарь где ключ - username, значение - словарь с данными
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, is_used_link, link, created_at FROM username_used_links ORDER BY created_at')
                result = {}
                for row in cursor.fetchall():
                    result[row[0]] = {
                        'username': row[0],
                        'is_used_link': bool(row[1]),
                        'link': row[2],
                        'created_at': row[3]
                    }
                logging.info(f"Получены все записи о ссылках, количество: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении всех записей: {e}")
            return {}
    
    def add_link(self, username: str, link: str) -> bool:
        """
        Добавить или обновить запись о выданной ссылке пользователю
        
        Args:
            username (str): Имя пользователя
            link (str): Ссылка выданная пользователю
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not username or not isinstance(username, str):
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        if not link or not isinstance(link, str):
            logging.error("Ошибка: link должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Используем INSERT OR REPLACE для добавления или обновления записи
                cursor.execute('''
                    INSERT OR REPLACE INTO username_used_links 
                    (username, is_used_link, link, created_at) 
                    VALUES (?, ?, ?, ?)
                ''', (username, True, link, current_time))
                
                conn.commit()
                logging.info(f"Ссылка для пользователя {username} успешно добавлена/обновлена")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении/обновлении ссылки для пользователя {username}: {e}")
            return False
    
    def remove_link(self, username: str) -> bool:
        """
        Удалить запись о пользователе
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not username or not isinstance(username, str):
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM username_used_links WHERE username = ?', (username,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Запись пользователя {username} успешно удалена")
                    return True
                else:
                    logging.warning(f"Пользователь {username} не найден в базе")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении пользователя {username}: {e}")
            return False
    
    def is_link_used(self, username: str) -> bool:
        """
        Проверяет была ли выдана ссылка пользователю
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если ссылка была выдана, False если нет или ошибка
        """
        if not username or not isinstance(username, str):
            logging.warning("Попытка проверки невалидного username")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_used_link FROM username_used_links WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result and bool(result[0]):
                    logging.info(f"Пользователю {username} была выдана ссылка")
                    return True
                else:
                    logging.info(f"Пользователю {username} ссылка не выдавалась")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке пользователя {username}: {e}")
            return False
    
    def get_user_link(self, username: str) -> Optional[str]:
        """
        Получить ссылку выданную пользователю
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            Optional[str]: Ссылка если была выдана, None если не выдавалась или ошибка
        """
        if not username or not isinstance(username, str):
            logging.warning("Попытка получения ссылки по невалидному username")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT link FROM username_used_links WHERE username = ? AND is_used_link = TRUE', (username,))
                result = cursor.fetchone()
                if result:
                    logging.info(f"Получена ссылка для пользователя {username}")
                    return result[0]
                else:
                    logging.info(f"Ссылка для пользователя {username} не найдена")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении ссылки для пользователя {username}: {e}")
            return None
    
    def remove_all_links(self) -> bool:
        """
        Очистить всю базу данных
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM username_used_links')
                conn.commit()
                logging.info("Все записи о ссылках успешно очищены")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке базы данных: {e}")
            return False
    
    def get_user_count(self) -> int:
        """
        Получить количество пользователей в базе
        
        Returns:
            int: Количество пользователей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM username_used_links')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество пользователей в базе: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества пользователей: {e}")
            return 0

    def get_user_info(self, username: str) -> Dict:
        """
        Получить информацию о конкретном пользователе
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            Dict: Словарь с информацией о пользователе или пустой словарь если не найден
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, is_used_link, link, created_at FROM username_used_links WHERE username = ?', (username,))
                row = cursor.fetchone()
                if row:
                    logging.info(f"Получена информация о пользователе {username}")
                    return {
                        'username': row[0],
                        'is_used_link': bool(row[1]),
                        'link': row[2],
                        'created_at': row[3]
                    }
                logging.info(f"Информация о пользователе {username} не найдена")
                return {}
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении информации о пользователе {username}: {e}")
            return {}