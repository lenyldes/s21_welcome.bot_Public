import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'white_list.db')

class WhiteListDB:
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
                    WHERE type='table' AND name='white_list'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS white_list (
                        username TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица white_list")
                else:
                    logging.info("Загружена существующая таблица white_list")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def get_white_list(self) -> Dict[str, str]:
        """
        Получить весь белый список
        
        Returns:
            Dict[str, str]: Словарь где ключ - username, значение - created_at
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, created_at FROM white_list ORDER BY created_at')
                result = {row[0]: row[1] for row in cursor.fetchall()}
                logging.info(f"Получен белый список, количество записей: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении белого списка: {e}")
            return {}
    
    def add_to_white_list(self, username: str) -> bool:
        """
        Добавить пользователя в белый список
        
        Args:
            username (str): Логин пользователя
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not username or not isinstance(username, str):
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    'INSERT INTO white_list (username, created_at) VALUES (?, ?)',
                    (username, current_time)
                )
                conn.commit()
                logging.info(f"Пользователь '{username}' успешно добавлен в белый список")
                return True
        except sqlite3.IntegrityError:
            logging.warning(f"Пользователь '{username}' уже существует в белом списке")
            return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении пользователя '{username}': {e}")
            return False
    
    def remove_from_white_list(self, username: str) -> bool:
        """
        Удалить пользователя из белого списка
        
        Args:
            username (str): Логин пользователя
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not username or not isinstance(username, str):
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM white_list WHERE username = ?', (username,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Пользователь '{username}' успешно удален из белого списка")
                    return True
                else:
                    logging.warning(f"Пользователь '{username}' не найден в белом списке")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении пользователя '{username}': {e}")
            return False
    
    def is_in_white_list(self, username: str) -> bool:
        """
        Проверяет есть ли пользователь в белом списке
        
        Args:
            username (str): Логин пользователя
            
        Returns:
            bool: True если пользователь найден, False если нет или ошибка
        """
        if not username or not isinstance(username, str):
            logging.warning("Попытка проверки невалидного username")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM white_list WHERE username = ?', (username,))
                result = cursor.fetchone() is not None
                if result:
                    logging.info(f"Пользователь '{username}' найден в белом списке")
                else:
                    logging.info(f"Пользователь '{username}' не найден в белом списке")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке пользователя '{username}': {e}")
            return False
    
    def remove_all_white_list(self) -> bool:
        """
        Очистить весь белый список
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM white_list')
                conn.commit()
                logging.info("Весь белый список успешно очищен")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке белого списка: {e}")
            return False
    
    def get_user_count(self) -> int:
        """
        Получить количество пользователей в белом списке
        
        Returns:
            int: Количество пользователей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM white_list')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество пользователей в белом списке: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества пользователей: {e}")
            return 0

    def get_user_info(self, username: str) -> Dict[str, str]:
        """
        Получить информацию о конкретном пользователе
        
        Args:
            username (str): Логин пользователя
            
        Returns:
            Dict[str, str]: Словарь с информацией о пользователе или пустой словарь если не найден
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, created_at FROM white_list WHERE username = ?', (username,))
                row = cursor.fetchone()
                if row:
                    logging.info(f"Получена информация о пользователе '{username}'")
                    return {'username': row[0], 'created_at': row[1]}
                logging.info(f"Информация о пользователе '{username}' не найдена")
                return {}
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении информации о пользователе '{username}': {e}")
            return {}

