import os
import sqlite3
import logging
from typing import Dict, Optional

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'user_state.db')

class UserStateDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """
        Инициализация базы данных состояний пользователей
        
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
                    WHERE type='table' AND name='user_state'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_state (
                        user_id INTEGER PRIMARY KEY,
                        state TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица user_state")
                else:
                    logging.info("Загружена существующая таблица user_state")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def get_all_states(self) -> Dict[int, str]:
        """
        Получить все состояния пользователей
        
        Returns:
            Dict[int, str]: Словарь где ключ - user_id, значение - state
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, state FROM user_state ORDER BY user_id')
                result = {row[0]: row[1] for row in cursor.fetchall()}
                logging.info(f"Получены все состояния, количество записей: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении состояний: {e}")
            return {}
    
    def set_user_state(self, user_id: int, state: str) -> bool:
        """
        Установить состояние пользователя
        (создает новую запись или обновляет существующую)
        
        Args:
            user_id (int): ID пользователя
            state (str): Состояние пользователя
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return False
        
        if not state or not isinstance(state, str):
            logging.error("Ошибка: state должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO user_state (user_id, state) VALUES (?, ?)',
                    (user_id, state)
                )
                conn.commit()
                logging.info(f"Состояние пользователя {user_id} успешно установлено: '{state}'")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при установке состояния пользователя {user_id}: {e}")
            return False
    
    def remove_user_state(self, user_id: int) -> bool:
        """
        Удалить состояние пользователя
        
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
                cursor.execute('DELETE FROM user_state WHERE user_id = ?', (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Состояние пользователя {user_id} успешно удалено")
                    return True
                else:
                    logging.warning(f"Пользователь {user_id} не найден в базе состояний")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении состояния пользователя {user_id}: {e}")
            return False
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """
        Получить состояние пользователя
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Optional[str]: Состояние пользователя или None если не найден
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.warning("Попытка получения состояния для невалидного user_id")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT state FROM user_state WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                if result:
                    #logging.info(f"Получено состояние пользователя {user_id}: '{result[0]}'")
                    return result[0]
                else:
                    #logging.info(f"Пользователь {user_id} не найден в базе состояний")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении состояния пользователя {user_id}: {e}")
            return None
    
    def remove_all_states(self) -> bool:
        """
        Очистить все состояния пользователей
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_state')
                conn.commit()
                logging.info("Все состояния пользователей успешно очищены")
                return True
        except sqlite3.Error as e:
            logging.error(f"Ошибка при очистке состояний: {e}")
            return False
    
    def get_users_count(self) -> int:
        """
        Получить количество пользователей в базе состояний
        
        Returns:
            int: Количество пользователей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM user_state')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество пользователей в базе состояний: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества пользователей: {e}")
            return 0

    def user_exists(self, user_id: int) -> bool:
        """
        Проверяет есть ли пользователь в базе состояний
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True если пользователь найден, False если нет или ошибка
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.warning("Попытка проверки невалидного user_id")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM user_state WHERE user_id = ?', (user_id,))
                result = cursor.fetchone() is not None
                if result:
                    logging.info(f"Пользователь {user_id} найден в базе состояний")
                else:
                    logging.info(f"Пользователь {user_id} не найден в базе состояний")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке пользователя {user_id}: {e}")
            return False

