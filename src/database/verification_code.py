import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'verification_code.db')

class VerificationCodeDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """
        Инициализация базы данных кодов верификации
        
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
                    WHERE type='table' AND name='verification_codes'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS verification_codes (
                        username TEXT PRIMARY KEY,
                        code TEXT NOT NULL,
                        is_issued BOOLEAN NOT NULL DEFAULT FALSE,
                        issued_at TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица verification_codes")
                else:
                    logging.info("Загружена существующая таблица verification_codes")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def get_all_codes(self) -> Dict[str, Dict]:
        """
        Получить все коды верификации
        
        Returns:
            Dict[str, Dict]: Словарь где ключ - username, значение - словарь с данными кода
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, code, is_issued, issued_at 
                    FROM verification_codes 
                    ORDER BY issued_at
                ''')
                result = {}
                for row in cursor.fetchall():
                    result[row[0]] = {
                        'code': row[1],
                        'is_issued': bool(row[2]),
                        'issued_at': row[3]
                    }
                logging.info(f"Получены все коды верификации, количество записей: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении всех кодов верификации: {e}")
            return {}
    
    def add_verification_code(self, username: str, code: str) -> bool:
        """
        Добавить или обновить код верификации для пользователя
        
        Args:
            username (str): Имя пользователя
            code (str): Код верификации (строка)
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not isinstance(username, str) or not username.strip():
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        if not isinstance(code, str) or not code.strip():
            logging.error("Ошибка: code должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Используем INSERT OR REPLACE для автоматического обновления существующей записи
                cursor.execute(
                    'INSERT OR REPLACE INTO verification_codes (username, code, is_issued, issued_at) VALUES (?, ?, ?, ?)',
                    (username.strip(), code.strip(), False, current_time)
                )
                conn.commit()
                
                # Проверяем, была ли это новая запись или обновление
                if cursor.rowcount == 1:
                    logging.info(f"Код верификации {code} для username '{username}' успешно добавлен/обновлен")
                return True
                
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении/обновлении кода для username '{username}': {e}")
            return False
    
    def mark_code_as_issued(self, username: str) -> bool:
        """
        Пометить код как выданный
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not isinstance(username, str) or not username.strip():
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE verification_codes SET is_issued = ? WHERE username = ?',
                    (True, username.strip())
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Код для username '{username}' помечен как выданный")
                    return True
                else:
                    logging.warning(f"Пользователь с username '{username}' не найден")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при обновлении статуса кода для username '{username}': {e}")
            return False
    
    def remove_verification_code(self, username: str) -> bool:
        """
        Удалить код верификации пользователя
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если успешно, False если ошибка или пользователь не найден
        """
        if not isinstance(username, str) or not username.strip():
            logging.error("Ошибка: username должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM verification_codes WHERE username = ?', (username.strip(),))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Код верификации для username '{username}' успешно удален")
                    return True
                else:
                    logging.warning(f"Пользователь с username '{username}' не найден")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении кода для username '{username}': {e}")
            return False
    
    def has_verification_code(self, username: str) -> bool:
        """
        Проверяет есть ли код верификации для пользователя
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если код найден, False если нет или ошибка
        """
        if not isinstance(username, str) or not username.strip():
            logging.warning("Попытка проверки невалидного username")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM verification_codes WHERE username = ?', (username.strip(),))
                result = cursor.fetchone() is not None
                if result:
                    logging.info(f"Код верификации для username '{username}' найден")
                else:
                    logging.info(f"Код верификации для username '{username}' не найден")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке кода для username '{username}': {e}")
            return False
    
    def is_code_issued(self, username: str) -> bool:
        """
        Проверяет был ли код выдан пользователю
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            bool: True если код был выдан, False если нет или ошибка
        """
        if not isinstance(username, str) or not username.strip():
            logging.warning("Попытка проверки невалидного username")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_issued FROM verification_codes WHERE username = ?', (username.strip(),))
                result = cursor.fetchone()
                if result:
                    is_issued = bool(result[0])
                    logging.info(f"Статус выдачи кода для username '{username}': {is_issued}")
                    return is_issued
                else:
                    logging.info(f"Код верификации для username '{username}' не найден")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке статуса выдачи кода для username '{username}': {e}")
            return False
    
    def check_verify_code(self, username: str, code: str) -> bool:
        """
        Проверить код верификации
        
        Args:
            username (str): Имя пользователя
            code (str): Код для проверки (строка)
            
        Returns:
            bool: True если код верный, False если нет или ошибка
        """
        if not isinstance(username, str) or not username.strip():
            logging.warning("Попытка проверки невалидного username")
            return False
        
        if not isinstance(code, str) or not code.strip():
            logging.warning("Попытка проверки невалидного кода")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT code FROM verification_codes WHERE username = ? AND is_issued = ?',
                    (username.strip(), True)
                )
                result = cursor.fetchone()
                if result:
                    code_matches = result[0] == code.strip()
                    #if code_matches:
                        #logging.info(f"Код для username '{username}' верный")
                    #else:
                        #logging.info(f"Код для username '{username}' неверный")
                    return code_matches
                else:
                    logging.info(f"Код верификации для username '{username}' не найден или не был выдан")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке кода для username '{username}': {e}")
            return False
    
    def remove_all_codes(self) -> bool:
        """
        Очистить все коды верификации
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM verification_codes')
                conn.commit()
                logging.info("Все коды верификации успешно очищены")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке всех кодов верификации: {e}")
            return False
    
    def get_codes_count(self) -> int:
        """
        Получить количество кодов верификации
        
        Returns:
            int: Количество кодов
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM verification_codes')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество кодов верификации: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества кодов: {e}")
            return 0

    def get_code_info(self, username: str) -> Optional[Dict]:
        """
        Получить информацию о коде верификации пользователя
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            Optional[Dict]: Словарь с информацией о коде или None если не найден
        """
        if not isinstance(username, str) or not username.strip():
            logging.warning("Попытка получения информации по невалидному username")
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, code, is_issued, issued_at 
                    FROM verification_codes 
                    WHERE username = ?
                ''', (username.strip(),))
                row = cursor.fetchone()
                if row:
                    logging.info(f"Получена информация о коде для username '{username}'")
                    return {
                        'username': row[0],
                        'code': row[1],
                        'is_issued': bool(row[2]),
                        'issued_at': row[3]
                    }
                logging.info(f"Информация о коде для username '{username}' не найдена")
                return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении информации о коде для username '{username}': {e}")
            return None
        
    def get_code_by_username(self, username: str) -> Optional[str]:
        """
        Получить код верификации по username
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            Optional[str]: Код верификации или None если не найден
        """
        if not isinstance(username, str) or not username.strip():
            logging.warning("Попытка получения кода по невалидному username")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT code FROM verification_codes WHERE username = ?', (username.strip(),))
                result = cursor.fetchone()
                if result:
                    code = result[0]
                    logging.info(f"Получен код для username '{username}'")
                    return code
                else:
                    logging.info(f"Код для username '{username}' не найден")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении кода для username '{username}': {e}")
            return None