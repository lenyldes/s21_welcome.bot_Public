import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict

DEFAULT_DB_PATH = os.path.join(os.getenv('DATA_DIR', 'data'), 'is_used_link_from_ID.db')

class IsUsedLinkFromIDDB:
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
                    WHERE type='table' AND name='used_links'
                ''')
                table_exists = cursor.fetchone() is not None
                
                # Создаем таблицу если не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS used_links (
                        user_id INTEGER PRIMARY KEY,
                        is_used_link BOOLEAN NOT NULL DEFAULT FALSE,
                        link TEXT,
                        created_at TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Логируем только если таблица была создана
                if not table_exists:
                    logging.info("Создана пустая таблица used_links")
                else:
                    logging.info("Загружена существующая таблица used_links")
                    
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
    
    def get_all_links(self) -> Dict[int, Dict]:
        """
        Получить все записи о выданных ссылках
        
        Returns:
            Dict[int, Dict]: Словарь где ключ - user_id, значение - словарь с данными
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, is_used_link, link, created_at FROM used_links ORDER BY created_at')
                result = {}
                for row in cursor.fetchall():
                    result[row[0]] = {
                        'user_id': row[0],
                        'is_used_link': bool(row[1]),
                        'link': row[2],
                        'created_at': row[3]
                    }
                logging.info(f"Получены все записи о ссылках, количество: {len(result)}")
                return result
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении всех записей: {e}")
            return {}
    
    def add_link(self, user_id: int, link: str) -> bool:
        """
        Добавить или обновить запись о выданной ссылке пользователю
        
        Args:
            user_id (int): ID пользователя
            link (str): Ссылка выданная пользователю
            
        Returns:
            bool: True если успешно, False если ошибка
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.error("Ошибка: user_id должен быть положительным целым числом")
            return False
        
        if not link or not isinstance(link, str):
            logging.error("Ошибка: link должен быть непустой строкой")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Используем INSERT OR REPLACE для обновления существующей записи
                cursor.execute('''
                    INSERT OR REPLACE INTO used_links 
                    (user_id, is_used_link, link, created_at) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, True, link, current_time))
                
                conn.commit()
                
                # Проверяем, была ли это новая запись или обновление
                if cursor.rowcount == 1:
                    # rowcount возвращает 1 для INSERT и количество измененных строк для UPDATE
                    # Для более точной проверки можно проверить существование записи до операции
                    cursor.execute('SELECT COUNT(*) FROM used_links WHERE user_id = ?', (user_id,))
                    existed_before = cursor.fetchone()[0] > 0
                    
                    if existed_before:
                        logging.info(f"Обновлена ссылка для пользователя {user_id}")
                    else:
                        logging.info(f"Добавлена новая ссылка для пользователя {user_id}")
                
                return True
                
        except sqlite3.Error as e:
            logging.error(f"Ошибка при добавлении/обновлении ссылки для пользователя {user_id}: {e}")
            return False
    
    def remove_link(self, user_id: int) -> bool:
        """
        Удалить запись о пользователе
        
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
                cursor.execute('DELETE FROM used_links WHERE user_id = ?', (user_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logging.info(f"Запись пользователя {user_id} успешно удалена")
                    return True
                else:
                    logging.warning(f"Пользователь {user_id} не найден в базе")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при удалении пользователя {user_id}: {e}")
            return False
    
    def is_link_used(self, user_id: int) -> bool:
        """
        Проверяет была ли выдана ссылка пользователю
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True если ссылка была выдана, False если нет или ошибка
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.warning("Попытка проверки невалидного user_id")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_used_link FROM used_links WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                if result and bool(result[0]):
                    logging.info(f"Пользователю {user_id} была выдана ссылка")
                    return True
                else:
                    logging.info(f"Пользователю {user_id} ссылка не выдавалась")
                    return False
        except sqlite3.Error as e:
            logging.error(f"Ошибка при проверке пользователя {user_id}: {e}")
            return False
    
    def get_user_link(self, user_id: int) -> Optional[str]:
        """
        Получить ссылку выданную пользователю
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Optional[str]: Ссылка если была выдана, None если не выдавалась или ошибка
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logging.warning("Попытка получения ссылки по невалидному user_id")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT link FROM used_links WHERE user_id = ? AND is_used_link = TRUE', (user_id,))
                result = cursor.fetchone()
                if result:
                    logging.info(f"Получена ссылка для пользователя {user_id}")
                    return result[0]
                else:
                    logging.info(f"Ссылка для пользователя {user_id} не найдена")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении ссылки для пользователя {user_id}: {e}")
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
                cursor.execute('DELETE FROM used_links')
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
                cursor.execute('SELECT COUNT(*) FROM used_links')
                count = cursor.fetchone()[0]
                logging.info(f"Текущее количество пользователей в базе: {count}")
                return count
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении количества пользователей: {e}")
            return 0

    def get_user_info(self, user_id: int) -> Dict:
        """
        Получить информацию о конкретном пользователе
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict: Словарь с информацией о пользователе или пустой словарь если не найден
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, is_used_link, link, created_at FROM used_links WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    logging.info(f"Получена информация о пользователе {user_id}")
                    return {
                        'user_id': row[0],
                        'is_used_link': bool(row[1]),
                        'link': row[2],
                        'created_at': row[3]
                    }
                logging.info(f"Информация о пользователе {user_id} не найдена")
                return {}
        except sqlite3.Error as e:
            logging.error(f"Ошибка при получении информации о пользователе {user_id}: {e}")
            return {}