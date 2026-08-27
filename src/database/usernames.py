import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional, Union

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'usernames_to_user_id.db')

class UsernamesToUserIDDB:
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
                    WHERE type='table' AND name='usernames_mapping'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usernames_mapping (
                        login_platform TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        full_name TEXT,
                        username_TG TEXT,
                        created_at TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица usernames_mapping")
                else:
                    logging.info("Загружена существующая таблица usernames_mapping")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def _normalize_field(self, value: Optional[str]) -> Optional[str]:
        """Нормализация строковых полей: пустые строки преобразуются в None"""
        if value is None or value == "":
            return None
        return str(value).strip()
    
    def get_all_users(self) -> Dict[str, Dict[str, Union[int, str, None]]]:
        """
        Получить всю базу данных
        
        Returns:
            Dict[str, Dict[str, Union[int, str, None]]]: Словарь где ключ - login_platform, значение - словарь с данными пользователя
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT login_platform, user_id, full_name, username_TG, created_at 
                    FROM usernames_mapping 
                    ORDER BY created_at
                ''')
                result = {
                    row[0]: {
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    } for row in cursor.fetchall()
                }
                logging.info(f"Получена вся база данных, количество записей: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении базы данных: {e}")
            return {}
    
    def add_user(self, login_platform: str, user_id: int, full_name: Optional[str] = None, username_TG: Optional[str] = None) -> bool:
        """
        Добавить пользователя в базу данных или обновить существующего
        
        Args:
            login_platform (str): Ник пользователя на платформе
            user_id (int): ID пользователя
            full_name (Optional[str]): Полное имя пользователя (может быть None или пустым)
            username_TG (Optional[str]): Username в Telegram (может быть None или пустым)
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        # Валидация обязательных полей
        if not login_platform or not isinstance(login_platform, str):
            logging.error("Ошибка: login_platform должен быть непустой строкой")
            return False
        
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return False
        
        # Нормализация необязательных полей
        normalized_full_name = self._normalize_field(full_name)
        normalized_username_TG = self._normalize_field(username_TG)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Проверяем, существует ли пользователь
                cursor.execute('SELECT 1 FROM usernames_mapping WHERE login_platform = ?', (login_platform,))
                user_exists = cursor.fetchone() is not None
                
                if user_exists:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE usernames_mapping 
                        SET user_id = ?, full_name = ?, username_TG = ?, created_at = ?
                        WHERE login_platform = ?
                    ''', (user_id, normalized_full_name, normalized_username_TG, current_time, login_platform))
                    logging.info(f"Пользователь '{login_platform}' успешно обновлен в базе данных")
                else:
                    # Добавляем нового пользователя
                    cursor.execute('''
                        INSERT INTO usernames_mapping 
                        (login_platform, user_id, full_name, username_TG, created_at) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (login_platform, user_id, normalized_full_name, normalized_username_TG, current_time))
                    logging.info(f"Пользователь '{login_platform}' успешно добавлен в базу данных")
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении/обновлении пользователя '{login_platform}': {e}")
            return False
    
    def remove_user_from_username(self, login_platform: str) -> bool:
        """
        Удалить пользователя из базы данных по login_platform
        
        Args:
            login_platform (str): Ник пользователя на платформе
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not login_platform or not isinstance(login_platform, str):
            logging.error("Ошибка: login_platform должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM usernames_mapping WHERE login_platform = ?', (login_platform,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Пользователь '{login_platform}' успешно удален из базы данных")
                    return True
                else:
                    logging.warning(f"Пользователь '{login_platform}' не найден в базе данных")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении пользователя '{login_platform}': {e}")
            return False

    def remove_user_from_id(self, user_id: int) -> bool:
        """
        Удалить пользователя из базы данных по user_id
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM usernames_mapping WHERE user_id = ?', (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Пользователь с user_id '{user_id}' успешно удален из базы данных")
                    return True
                else:
                    logging.warning(f"Пользователь с user_id '{user_id}' не найден в базе данных")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении пользователя с user_id '{user_id}': {e}")
            return False
    
    def user_exists(self, login_platform: str) -> bool:
        """
        Проверяет есть ли пользователь в базе данных по login_platform
        
        Args:
            login_platform (str): Ник пользователя на платформе
            
        Returns:
            bool: True если пользователь найден, False если нет или ошибка
        """
        if not login_platform or not isinstance(login_platform, str):
            logging.warning("Попытка проверки невалидного login_platform")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM usernames_mapping WHERE login_platform = ?', (login_platform,))
                result = cursor.fetchone() is not None
                if result:
                    logging.info(f"Пользователь '{login_platform}' найден в базе данных")
                else:
                    logging.info(f"Пользователь '{login_platform}' не найден в базе данных")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке пользователя '{login_platform}': {e}")
            return False
    
    def remove_all_users(self) -> bool:
        """
        Очистить всю базу данных
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM usernames_mapping')
                conn.commit()
                logging.info("Вся база данных успешно очищена")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке базы данных: {e}")
            return False
    
    def get_user_count(self) -> int:
        """
        Получить количество пользователей в базе данных
        
        Returns:
            int: Количество пользователей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM usernames_mapping')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество пользователей в базе данных: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества пользователей: {e}")
            return 0

    def get_user_by_login_platform(self, login_platform: str) -> Optional[Dict[str, Union[int, str, None]]]:
        """
        Получить информацию о пользователе по login_platform
        
        Args:
            login_platform (str): Ник пользователя на платформе
            
        Returns:
            Dict[str, Union[int, str, None]] или None: Словарь с информацией о пользователе или None если не найден
        """
        if not login_platform or not isinstance(login_platform, str):
            logging.error("Ошибка: login_platform должен быть непустой строкой")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT login_platform, user_id, full_name, username_TG, created_at 
                    FROM usernames_mapping 
                    WHERE login_platform = ?
                ''', (login_platform,))
                row = cursor.fetchone()
                if row:
                    user_info = {
                        'login_platform': row[0],
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    }
                    logging.info(f"Найден пользователь по login_platform '{login_platform}': {user_info}")
                    return user_info
                logging.info(f"Пользователь с login_platform '{login_platform}' не найден")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске пользователя по login_platform '{login_platform}': {e}")
            return None

    def get_user_by_user_id(self, user_id: int) -> Optional[Dict[str, Union[int, str, None]]]:
        """
        Получить информацию о пользователе по user_id
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict[str, Union[int, str, None]] или None: Словарь с информацией о пользователе или None если не найден
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT login_platform, user_id, full_name, username_TG, created_at 
                    FROM usernames_mapping 
                    WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                if row:
                    user_info = {
                        'login_platform': row[0],
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    }
                    logging.info(f"Найден пользователь по user_id '{user_id}': {user_info}")
                    return user_info
                logging.info(f"Пользователь с user_id '{user_id}' не найден")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске пользователя по user_id '{user_id}': {e}")
            return None

    def get_user_by_full_name(self, full_name: Optional[str] = None) -> Optional[Dict[str, Union[int, str, None]]]:
        """
        Получить информацию о пользователе по full_name
        
        Args:
            full_name (Optional[str]): Полное имя пользователя (может быть None)
            
        Returns:
            Dict[str, Union[int, str, None]] или None: Словарь с информацией о пользователе или None если не найден
        """
        normalized_full_name = self._normalize_field(full_name)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if normalized_full_name is None:
                    # Ищем пользователей с NULL full_name
                    cursor.execute('''
                        SELECT login_platform, user_id, full_name, username_TG, created_at 
                        FROM usernames_mapping 
                        WHERE full_name IS NULL
                    ''')
                else:
                    # Ищем по конкретному full_name
                    cursor.execute('''
                        SELECT login_platform, user_id, full_name, username_TG, created_at 
                        FROM usernames_mapping 
                        WHERE full_name = ?
                    ''', (normalized_full_name,))
                
                row = cursor.fetchone()
                if row:
                    user_info = {
                        'login_platform': row[0],
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    }
                    logging.info(f"Найден пользователь по full_name '{full_name}': {user_info}")
                    return user_info
                logging.info(f"Пользователь с full_name '{full_name}' не найден")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске пользователя по full_name '{full_name}': {e}")
            return None

    def get_user_by_username_TG(self, username_TG: Optional[str] = None) -> Optional[Dict[str, Union[int, str, None]]]:
        """
        Получить информацию о пользователе по username_TG
        
        Args:
            username_TG (Optional[str]): Username в Telegram (может быть None)
            
        Returns:
            Dict[str, Union[int, str, None]] или None: Словарь с информацией о пользователе или None если не найден
        """
        normalized_username_TG = self._normalize_field(username_TG)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if normalized_username_TG is None:
                    # Ищем пользователей с NULL username_TG
                    cursor.execute('''
                        SELECT login_platform, user_id, full_name, username_TG, created_at 
                        FROM usernames_mapping 
                        WHERE username_TG IS NULL
                    ''')
                else:
                    # Ищем по конкретному username_TG
                    cursor.execute('''
                        SELECT login_platform, user_id, full_name, username_TG, created_at 
                        FROM usernames_mapping 
                        WHERE username_TG = ?
                    ''', (normalized_username_TG,))
                
                row = cursor.fetchone()
                if row:
                    user_info = {
                        'login_platform': row[0],
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    }
                    logging.info(f"Найден пользователь по username_TG '{username_TG}': {user_info}")
                    return user_info
                logging.info(f"Пользователь с username_TG '{username_TG}' не найден")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске пользователя по username_TG '{username_TG}': {e}")
            return None
        
    def get_login_platform_by_user_id(self, user_id: int) -> Optional[str]:
        """
        Получить login_platform по user_id
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            str или None: login_platform или None если не найден
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT login_platform FROM usernames_mapping WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    login_platform = row[0]
                    logging.info(f"Найден login_platform '{login_platform}' для user_id '{user_id}'")
                    return login_platform
                logging.info(f"Пользователь с user_id '{user_id}' не найден")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске login_platform по user_id '{user_id}': {e}")
            return None

    def get_users_with_null_fields(self) -> Dict[str, Dict[str, Union[int, str, None]]]:
        """
        Получить всех пользователей у которых хотя бы одно из полей full_name или username_TG равно NULL
        
        Returns:
            Dict[str, Dict[str, Union[int, str, None]]]: Словарь с пользователями у которых есть NULL поля
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT login_platform, user_id, full_name, username_TG, created_at 
                    FROM usernames_mapping 
                    WHERE full_name IS NULL OR username_TG IS NULL
                    ORDER BY created_at
                ''')
                result = {
                    row[0]: {
                        'user_id': row[1],
                        'full_name': row[2],
                        'username_TG': row[3],
                        'created_at': row[4]
                    } for row in cursor.fetchall()
                }
                logging.info(f"Найдено пользователей с NULL полями: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске пользователей с NULL полями: {e}")
            return {}