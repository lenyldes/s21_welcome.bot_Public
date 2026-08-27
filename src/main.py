import telebot
import random
import logging
import os
import sys
from datetime import datetime, timedelta

# Определение путей проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.logging_config import setup_logging
setup_logging()

from src.services.rocketchat import send_dm

from src.database import (
    IsUsedLinkFromIDDB,
    IsUsedLinkFromUsernameDB,
    UserStateDB,
    UsernamesToUserIDDB,
    WhiteListDB,
    VerificationCodeDB,
)

# ====================== НАСТРОЙКИ ======================
BOT_TOKEN = os.getenv('BOT_TOKEN')
if BOT_TOKEN is None:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

CHAT_ID = int(os.getenv('CHAT_ID', '-1001234567890')) # Секта 21
# CHAT_ID = -1009876543210 # s21_test
admins_raw = os.getenv('ADMINS_USER_ID', '111111111,222222222')
ADMINS_USER_ID = [int(x.strip()) for x in admins_raw.split(',') if x.strip()]
MY_TG = os.getenv('MY_TG', '@example_admin')

DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
ASSETS_DIR = os.getenv("ASSETS_DIR", os.path.join(BASE_DIR, "assets"))
LOGS_DIR = os.getenv("LOGS_DIR", os.path.join(BASE_DIR, "logs"))

# Создаем экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

# ====================== КОМАНДЫ БОТА ======================
@bot.message_handler(commands=['start'], chat_types=['private'])
def send_welcome(message):
    logging.info(f"Обработка команды /start от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
    
    welcome_text = f"""
Привет, {message.from_user.full_name}! 
Я бот для приглашений в чат основы Школы 21 (кампус НН).

Чтобы получить ссылку для вступления в наш чат воспользуйся командой:

/get_invite - Получить приглашение в чат

⚠️ВАЖНО⚠️: у тебя должен быть настроен и работать RocketChat. Он необходим для успешной авторизации

Если возникнут проблемы - можешь обратиться к администратору напрямую: {MY_TG}
    """
    
    try:
        bot.send_message(message.chat.id, welcome_text)
        logging.info(f"Приветственное сообщение отправлено пользователю {message.from_user.username}|{message.from_user.id}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке приветственного сообщения пользователю {message.from_user.username}|{message.from_user.id}: {str(e)}")

@bot.message_handler(commands=['get_invite'], chat_types=['private'])
def get_invite(message):
    logging.info(f"Обработка команды /get_invite от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
    
    user_id = message.from_user.id
    
    # Проверяем, не получал ли пользователь уже ссылку
    if db_used_link_from_ID.is_link_used(user_id=user_id):
        bot.send_message(message.chat.id, f"❌ По моим данным ты {message.from_user.full_name} уже получал ссылку.\nДля повторного получения обратись к администратору: {MY_TG}")
        logging.warning(f"❌ Повторная попытка получения ссылки пользователем {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return

    # Сразу запрашиваем кодовое слово
    bot.send_message(message.chat.id, "Напиши ТОЛЬКО свой школьный логин (ник) и ничего более:")

    # Регистрируем следующий шаг - ожидание логина
    db_userstate.set_user_state(user_id=user_id, state="waiting_for_login")

    #logging.info(f"Пользователь {message.from_user.username}|{message.from_user.id} переведен в состояние waiting_for_login")

@bot.message_handler(
    func=lambda message: db_userstate.get_user_state(message.from_user.id) == "waiting_for_login", 
    chat_types=['private']
)
def process_login_verification(message):
    logging.info(f"Обработка логина от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
    
    user_id = message.from_user.id
    platform_login = message.text.strip().lower()

    if platform_login == "/cancel":
        db_userstate.remove_user_state(user_id=user_id)
        logging.info(f"Команда /cancel от пользователя {message.from_user.username}|{message.from_user.id} в процессе верификации логина")
        return
    
    if db_whitelist.is_in_white_list(username=platform_login):
        #logging.info(f"Логин {platform_login} найден в белом списке для пользователя {message.from_user.username}|{message.from_user.id}")
        
        if db_used_link_from_username.is_link_used(username=platform_login):
            bot.send_message(message.chat.id, f"❌ По моим данным пользователь с логином '{platform_login}' уже получал ссылку.\nДля повторного получения обратись к администратору: {MY_TG}")
            logging.warning(f"❌ Повторная попытка получения ссылки для логина {platform_login} от пользователя {message.from_user.username}|{message.from_user.id}")
            bot.send_message(ADMINS_USER_ID[0], f"Повторная попытка получения ссылки для логина {platform_login} от пользователя {message.from_user.username}|{message.from_user.id}")
            db_userstate.remove_user_state(user_id=user_id)
            return
        
        bot.reply_to(message, "🎉 Поздравляю!\nТвой логин принят!\n\nЯ сейчас отправлю одноразовый код тебе в ЛС RocketChat, пришли мне его.\nЭто необходимая мера, чтобы убедиться что ты - это ты :)\n")

        db_usernames.add_user(
            login_platform=platform_login,
            user_id=user_id,
            username_TG=message.from_user.username if message.from_user.username else "None",
            full_name=message.from_user.full_name if message.from_user.full_name else "None"
        )

        code = random.randint(100000, 999999)
        code = str(code)

        db_verification_code.add_verification_code(username=platform_login, code=code)

        success_send_message = send_dm(platform_login, code)

        if not success_send_message:
            logging.error(f"❌ Не удалось отправить код {code} в RocketChat для логина {platform_login} от пользователя {message.from_user.username}|{message.from_user.id}")
            bot.send_message(message.chat.id, f"❌ Не удалось отправить код в RocketChat. Попробуй, пожалуйста, немного позже (возможно слишком много одновремнных запросов) или обратись к администратору: @{MY_TG}.")
            bot.send_message(chat_id=ADMINS_USER_ID[0], text=f"⚠️Не удалось отправить код в RocketChat для логина {platform_login} от пользователя @{message.from_user.username}|{message.from_user.id}")
            db_userstate.remove_user_state(user_id=user_id)
            db_verification_code.remove_verification_code(username=platform_login)
            
        else:
            #logging.info(f"Код верификации '{code}' отправлен для логина {platform_login} пользователю {message.from_user.username}|{message.from_user.id}")
            db_userstate.set_user_state(user_id=user_id, state="waiting_for_code")
            db_verification_code.mark_code_as_issued(username=platform_login)
            bot.send_message(message.chat.id, "Введи одноразовый код отправленный тебе в RocketChat:")
            
    else:
        logging.warning(f"❌ Логин {platform_login} не найден в белом списке для пользователя {message.from_user.username}|{message.from_user.id}")
        bot.reply_to(message, "❌ Отказано в получении ссылки...\n")
        bot.send_message(
            chat_id=message.chat.id,
            text="Убедись что ты ПРАВИЛЬНО написал свой логин (ник) и что ты являешься участником основного обучения.\nПопробуй ещё раз или введи /cancel для отмены команды:"
        )
        bot.send_message(chat_id=ADMINS_USER_ID[0], text=f"Отказ в получении ссылки. Логин {platform_login} не найден в белом списке для пользователя {message.from_user.username}|{message.from_user.id}")
        
@bot.message_handler(
    func=lambda message: db_userstate.get_user_state(message.from_user.id) == "waiting_for_code", 
    chat_types=['private']
)
def process_code_verification(message):
    logging.info(f"Обработка кода верификации от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
    
    user_id = message.from_user.id
    code = message.text.strip().lower()
    username = db_usernames.get_login_platform_by_user_id(user_id=user_id)

    # Проверяем, есть ли код для верификации
    if not db_verification_code.get_code_by_username(username=username):
        bot.reply_to(message, "❌ Сессия устарела. Начните заново с /get_invite")
        db_userstate.remove_user_state(user_id)
        return

    if code == "/cancel":
        db_userstate.remove_user_state(user_id=user_id)
        db_verification_code.remove_verification_code(username=username)
        logging.info(f"Команда /cancel от пользователя {message.from_user.username}|{message.from_user.id} в процессе верификации кода")
        return

    if db_verification_code.check_verify_code(username=username, code=code):
        if username == "wothsara":
            image_path = os.path.join(ASSETS_DIR, 'image.jpg')
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    bot.send_photo(user_id, photo)
            else:
                logging.warning(f"Файл пасхалки {image_path} не найден")

            bot.reply_to(message, "Хорошая попытка, Саша, но нет!)")
            db_userstate.remove_user_state(user_id=user_id)

            bot.send_message(chat_id=ADMINS_USER_ID[0], text=f"Саша АДМ попыталась получить код :О!\n{message.from_user.username}|{message.from_user.id} с ником '{username}'.")
            logging.warning(f"Саша АДМ попыталась получить код :О!\n{message.from_user.username}|{message.from_user.id} с ником '{username}'.")
            return

        
        logging.info(f"Код верификации {code} успешно подтвержден для пользователя {message.from_user.username}|{message.from_user.id} с ником '{username}'")
        bot.reply_to(message, "🎉 Поздравляю!\nВерификация пройдена успешно!")

        db_verification_code.remove_verification_code(username=username)

        msg = bot.send_message(
            chat_id=message.chat.id,
            text="Генерирую ссылку..."
        )

        username = db_usernames.get_login_platform_by_user_id(user_id=user_id)
        invite_link = generate_one_invite_links(username)

        if not invite_link:
            bot.reply_to(message, "❌ Ошибка при создании ссылки. Попробуйте позже.")
            logging.error(f"❌ Ошибка при создании ссылки для пользователя {message.from_user.username}|{message.from_user.id} с ником {username}")
            db_userstate.remove_user_state(user_id=user_id)
            return
        
        bot.edit_message_text(
            text=f"Твоя ссылка для вступления в чат: {invite_link.invite_link}\n\n⚠️ Ссылка одноразовая, действительна только 24 часа и только для тебя!\nНикому её не передавай!\n",
            chat_id=msg.chat.id,
            message_id=msg.message_id
        )

        logging.info(f"Ссылка {invite_link.invite_link} создана для пользователя {message.from_user.username}|{message.from_user.id} с ником {username}")
        db_userstate.remove_user_state(user_id=user_id)
        db_used_link_from_ID.add_link(user_id=user_id, link=invite_link.invite_link)
        db_used_link_from_username.add_link(username=username, link=invite_link.invite_link)
        db_usernames.add_user(
            login_platform=username,
            user_id=user_id,
            username_TG=message.from_user.username if message.from_user.username else "None",
            full_name=message.from_user.full_name if message.from_user.full_name else "None"
        )
    else:
        #db_usernames.remove_user_from_id(user_id=user_id)
        bot.reply_to(message, "❌ Неверный код!\nПопробуй ещё раз или введи /cancel для отмены команды:")
        bot.send_message(chat_id=ADMINS_USER_ID[0], text=f"Неверный код верификации от пользователя {message.from_user.username}|{message.from_user.id} с ником '{username}'. Введен: {code}, ожидался: {db_verification_code.get_code_by_username(username=username)}")
        logging.warning(f"❌ Неверный код верификации от пользователя {message.from_user.username}|{message.from_user.id} с ником '{username}'. Введен: {code}, ожидался: {db_verification_code.get_code_by_username(username=username)}")


# ====================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======================

def generate_one_invite_links(login):     
    try:
        expire_date = datetime.now() + timedelta(hours=24)
        # Преобразуем в timestamp (целое число), так как Telegram API ожидает timestamp
        expire_timestamp = int(expire_date.timestamp())

        invite_link = bot.create_chat_invite_link(
            chat_id=CHAT_ID,
            name=login,
            member_limit=1,
            creates_join_request=False,
            expire_date=expire_timestamp
        )
        #logging.info(f"Успешно создана ссылка-приглашение для логина {login}")
        return invite_link
    except Exception as e:
        logging.error(f"❌ Ошибка при создании ссылки-приглашения для логина {login}: {str(e)}")
        return None

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = """
Доступные команды:

/get_invite - Получить приглашение в чат
/help - Получить справку
"""
    
    # Добавляем команды для администраторов
    if message.from_user.id in ADMINS_USER_ID:
        help_text += """
Команды администратора:
/get_chat_info - Получить ID чата и топика
/add_users_to_white_list - Добавить несколько пользователей в белый список
/add_user_to_DB - Добавить пользователей в БД
/remove_one_user_from_white_list - Удалить одного пользователя из белого списка
/get_white_list - Получить белый список пользователей
/get_user_info_by_id - Получить информацию о пользователе по ID
/get_user_info_by_login - Получить информацию о пользователе по логину
/get_used_links - Получить список пользователей получивших ссылки
/get_unused_links - Получить список пользователей НЕ получивших ссылки
/get_all_users - Получить список всех пользователей в формате login_platform[tab]user_id[tab]created_at[tab]username_tg[tab]full_name

⚠️⚠️⚠️ /remove_used_link_user_from_id - сбросить использование ссылки по tg_id
⚠️⚠️⚠️ /remove_used_link_user_from_username - сбросить использование ссылки по username

/get_log - получить логи
"""
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил справку с административными командами")
    else:
        logging.info(f"Пользователь {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id} запросил справку")
    
    help_text += f"\nПо вопросам: {MY_TG}"
    
    bot.send_message(message.from_user.id, help_text)

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

# ====================== КОМАНДЫ АДМИНИСТРАТОРА ======================

@bot.message_handler(commands=['get_chat_info'])
def get_chat_info(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_chat_info\n"
            f"👤 Пользователь: {message.from_user.username or 'нет username'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_chat_info от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    info_text = (f"💬 Информация для отправки сообщений:\n"
                 f"you_id: {message.from_user.id}\n"
                 f"chat_id: {message.chat.id}\n"
                 f"thread_id: {message.message_thread_id}\n"
                 f"chat_title: {message.chat.title or 'ЛС'}")
    
    bot.send_message(message.from_user.id, info_text)
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о чате {message.chat.title}|{message.chat.id}")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")


@bot.message_handler(commands=['add_users_to_white_list'], chat_types=['private'])
def add_all_users_to_white_list(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /add_users_to_white_list\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /add_users_to_white_list от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, "Введите список username для добавления в белый список (по одному на строке, без @):")
    
    # Используем базу данных для хранения состояния
    db_userstate.set_user_state(message.from_user.id, 'waiting_usernames_list')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал добавление пользователей в белый список")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_usernames_list', chat_types=['private'])
def handle_usernames_list_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    usernames_text = message.text.strip()

    if (usernames_text == "/cancel"):
        db_userstate.remove_user_state(message.from_user.id)
        bot.send_message(message.from_user.id, "❌ Операция отменена")
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил добавление пользователей в белый список")
        return

    usernames = [username.strip().lower() for username in usernames_text.split('\n') if username.strip()]
    
    if not usernames:
        bot.send_message(message.from_user.id, "❌ Список username пуст")
        db_userstate.remove_user_state(message.from_user.id)
        logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} отправил пустой список для добавления в белый список")
        return
    
    results = []
    success_count = 0
    error_count = 0
    
    try:
        for username in usernames:
            success = db_whitelist.add_to_white_list(username=username)
            
            if success:
                results.append(f"✅ {username}")
                success_count += 1
                logging.info(f"Пользователь {username} добавлен в белый список админом {message.from_user.username}|{message.from_user.id}")
            else:
                results.append(f"❌ {username}")
                error_count += 1
                logging.warning(f"Не удалось добавить пользователя {username} в белый список админом {message.from_user.username}|{message.from_user.id}")
        
        result_text = f"📊 Результат добавления:\nУспешно: {success_count}, Ошибок: {error_count}\n\n"
        result_text += "\n".join(results)
        
        bot.send_message(message.from_user.id, result_text)
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} завершил добавление пользователей в белый список: успешно {success_count}, ошибок {error_count}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при добавлении списка: {str(e)}")
        logging.error(f"Ошибка при добавлении списка пользователей в белый список админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    # Удаляем состояние пользователя
    db_userstate.remove_user_state(message.from_user.id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['remove_one_user_from_white_list'], chat_types=['private'])
def remove_user_from_white_list(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /remove_one_user_from_white_list\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /remove_one_user_from_white_list от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    user_id = message.from_user.id
    
    bot.send_message(message.from_user.id, "Введите username пользователя для удаления из белого списка (без @):")
    
    db_userstate.set_user_state(user_id=user_id, state='waiting_username_remove')

    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал удаление пользователя из белого списка")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_username_remove', chat_types=['private'])
def handle_username_remove_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    username = message.text.strip().lower()
    user_id = message.from_user.id

    if (username == "/cancel"):
        db_userstate.remove_user_state(user_id=user_id)
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил удаление пользователя из белого списка")
        return
        
    try:
        success = db_whitelist.remove_from_white_list(username=username)
        
        if success:
            bot.send_message(message.from_user.id, f"✅ Пир {username} успешно удален из белого списка")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно удалил пользователя {username} из белого списка")
        else:
            bot.send_message(message.from_user.id, f"❌ Не удалось удалить пира {username} из белого списка")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} не смог удалить пользователя {username} из белого списка")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при удалении: {str(e)}")
        logging.error(f"Ошибка при удалении пользователя {username} из белого списка админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    # Очищаем состояние
    db_userstate.remove_user_state(user_id=user_id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")


@bot.message_handler(commands=['get_white_list'], chat_types=['private'])
def get_white_list_command(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_white_list\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_white_list от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    try:
        white_list = db_whitelist.get_white_list()
        
        if not white_list:
            bot.send_message(message.from_user.id, "📝 Белый список пуст")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил белый список - список пуст")
            return
        
        white_list_text = "📋 Белый список пользователей:\n\n"
        # Сортируем по дате добавления и форматируем вывод
        sorted_users = sorted(white_list.items(), key=lambda x: x[1])  # Сортировка по дате
        white_list_text += "\n".join([f"{username} (добавлен: {created_at})" for username, created_at in sorted_users])
        white_list_text += f"\n\nВсего: {len(white_list)} пользователей"
        
        # Если список слишком длинный, разбиваем на части
        if len(white_list) > 10:
            # Отправляем файлом если слишком много данных
            white_list_content = "\n".join([f"@{username} - {created_at}" for username, created_at in sorted(white_list.items())])
            with open('white_list.txt', 'w', encoding='utf-8') as f:
                f.write(white_list_content)
            
            with open('white_list.txt', 'rb') as f:
                bot.send_document(message.from_user.id, f, caption=f"📋 Белый список ({len(white_list)} пользователей)")

            # Удаляем временный файл
            import os
            os.remove('white_list.txt')

            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил белый список - отправлен файлом ({len(white_list)} пользователей)")
        else:
            bot.send_message(message.from_user.id, white_list_text)
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил белый список - отправлен сообщением ({len(white_list)} пользователей)")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении белого списка: {str(e)}")
        logging.error(f"Ошибка при получении белого списка админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_user_info_by_id'], chat_types=['private'])
def get_user_info_by_id_command(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_user_info_by_id\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_user_info_by_id от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, "Введите user_id пользователя для получения информации:")
    
    db_userstate.set_user_state(message.from_user.id, 'waiting_user_id_info')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал запрос информации о пользователе по ID")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_user_id_info', chat_types=['private'])
def handle_user_id_info_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    user_id_text = message.text.strip()

    if user_id_text == "/cancel":
        db_userstate.remove_user_state(message.from_user.id)
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил запрос информации о пользователе по ID")
        return
        
    try:
        user_id = int(user_id_text)
        
        # Ищем пользователя в основной базе по user_id
        user_info = db_usernames.get_user_by_user_id(user_id)
        
        if user_info:
            # Проверяем, была ли выдана ссылка (по username из основной базы)
            login_platform = user_info.get('login_platform')
            is_used_link = db_used_link_from_username.is_link_used(login_platform) if login_platform else False
            
            info_text = f"👤 Информация о пользователе:\n\n"
            info_text += f"User ID: `{user_info.get('user_id')}`\n"
            info_text += f"Логин на платформе: {user_info.get('login_platform', 'не указан')}\n"
            info_text += f"Username TG: @{user_info.get('username_TG', 'не указан')}\n"
            info_text += f"Полное имя: {user_info.get('full_name', 'не указано')}\n"
            info_text += f"Получил ссылку: {'✅' if is_used_link else '❌'}\n"
            info_text += f"Дата регистрации: {user_info.get('created_at', 'неизвестно')}"
            
            bot.send_message(message.from_user.id, info_text)
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о пользователе {user_id} - найдено: {user_info.get('login_platform', 'N/A')}")
        else:
            bot.send_message(message.from_user.id, f"❌ Пользователь с ID {user_id} не найден в базе данных")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о несуществующем пользователе {user_id}")
    
    except ValueError:
        bot.send_message(message.from_user.id, "❌ Ошибка: user_id должен быть числом")
        logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} ввел некорректный user_id: {user_id_text}")
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении информации: {str(e)}")
        logging.error(f"Ошибка при получении информации о пользователе {user_id_text} админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    db_userstate.remove_user_state(message.from_user.id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_user_info_by_login'], chat_types=['private'])
def get_user_info_by_login_command(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_user_info_by_login\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_user_info_by_login от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, "Введите логин пользователя на платформе:")
    
    db_userstate.set_user_state(message.from_user.id, 'waiting_login_info')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал запрос информации о пользователе по логину")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_login_info', chat_types=['private'])
def handle_login_info_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    login_platform = message.text.strip()

    if login_platform == "/cancel":
        db_userstate.remove_user_state(message.from_user.id)
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил запрос информации о пользователе по логину")
        return
        
    try:
        # Ищем пользователя по login_platform
        user_info = db_usernames.get_user_by_login_platform(login_platform)
        
        if user_info:
            # Проверяем, была ли выдана ссылка
            is_used_link = db_used_link_from_username.is_link_used(login_platform)
            link_info = db_used_link_from_username.get_user_info(login_platform)
            
            info_text = f"👤 Информация о пользователе:\n\n"
            info_text += f"Логин на платформе: {user_info.get('login_platform', 'не указан')}\n"
            info_text += f"User ID: `{user_info.get('user_id')}`\n"
            info_text += f"Username TG: @{user_info.get('username_TG', 'не указан')}\n"
            info_text += f"Полное имя: {user_info.get('full_name', 'не указано')}\n"
            info_text += f"Получил ссылку: {'✅' if is_used_link else '❌'}\n"
            
            if is_used_link and link_info.get('link'):
                info_text += f"Выданная ссылка: {link_info.get('link')}\n"
            
            info_text += f"Дата регистрации: {user_info.get('created_at', 'неизвестно')}"
            
            bot.send_message(message.from_user.id, info_text)
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о пользователе {login_platform} - найдено: user_id {user_info.get('user_id')}, получил ссылку: {is_used_link}")
        else:
            bot.send_message(message.from_user.id, f"❌ Пользователь с логином '{login_platform}' не найден")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о несуществующем логине: {login_platform}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении информации: {str(e)}")
        logging.error(f"Ошибка при получении информации о пользователе {login_platform} админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    db_userstate.remove_user_state(message.from_user.id)

@bot.message_handler(commands=['remove_used_link_user_from_id'], chat_types=['private'])
def remove_used_link_user_from_id_command(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /remove_used_link_user_from_id\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /remove_used_link_user_from_id от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, "Введите user_id пользователя для сброса флага использованной ссылки:")
    
    # Используем базу данных для хранения состояний
    db_userstate.set_user_state(message.from_user.id, 'waiting_user_id_remove_used_link')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал сброс флага использованной ссылки")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_user_id_remove_used_link', chat_types=['private'])
def handle_user_id_remove_used_link_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    user_id_text = message.text.strip()

    if user_id_text == "/cancel":
        db_userstate.remove_user_state(message.from_user.id)
        bot.send_message(message.from_user.id, "❌ Операция отменена")
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил сброс флага использованной ссылки")
        return
        
    try:
        # Пытаемся преобразовать в число
        user_id = int(user_id_text)
        
        # Проверяем существует ли пользователь в базе ссылок
        user_info = db_used_link_from_ID.get_user_info(user_id)
        
        if user_info:
            # Удаляем пользователя из базы использованных ссылок
            success = db_used_link_from_ID.remove_link(user_id=user_id)
            
            if success:
                bot.send_message(message.from_user.id, f"✅ Флаг использованной ссылки сброшен для user_id: {user_id}")
                logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно сбросил флаг использованной ссылки для user_id: {user_id}")
            else:
                bot.send_message(message.from_user.id, f"❌ Не удалось сбросить флаг для user_id: {user_id}")
                logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} не смог сбросить флаг использованной ссылки для user_id: {user_id}")
        else:
            bot.send_message(message.from_user.id, f"ℹ️ Пользователь с user_id: {user_id} не найден в базе использованных ссылок")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} попытался сбросить флаг для несуществующего user_id: {user_id}")
    
    except ValueError:
        bot.send_message(message.from_user.id, "❌ Ошибка: user_id должен быть числом")
        logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} ввел некорректный user_id: {user_id_text}")
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при сбросе флага: {str(e)}")
        logging.error(f"Ошибка при сбросе флага использованной ссылки админом {message.from_user.username}|{message.from_user.id} для user_id {user_id_text}: {str(e)}")
    
    # Очищаем состояние пользователя
    db_userstate.remove_user_state(message.from_user.id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['remove_used_link_user_from_username'], chat_types=['private'])
def remove_used_link_user_from_username_command(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /remove_used_link_user_from_username\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /remove_used_link_user_from_username от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, "Введите username пользователя для сброса флага использованной ссылки (без @):")
    
    # Используем базу данных для хранения состояний
    db_userstate.set_user_state(message.from_user.id, 'waiting_username_remove_used_link')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал сброс флага использованной ссылки по username")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_username_remove_used_link', chat_types=['private'])
def handle_username_remove_used_link_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    username_text = message.text.strip()

    # Убираем @ если пользователь его ввел
    if username_text.startswith('@'):
        username_text = username_text[1:]

    if username_text == "/cancel":
        db_userstate.remove_user_state(message.from_user.id)
        bot.send_message(message.from_user.id, "❌ Операция отменена")
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил сброс флага использованной ссылки по username")
        return
        
    try:
        # Проверяем существует ли пользователь в базе использованных ссылок по username
        user_info = db_used_link_from_username.get_user_info(username_text)
        
        if user_info:
            # Удаляем пользователя только из базы использованных ссылок по username
            success = db_used_link_from_username.remove_link(username=username_text)
            
            if success:
                bot.send_message(message.from_user.id, f"✅ Флаг использованной ссылки сброшен для username: @{username_text}")
                logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно сбросил флаг использованной ссылки для username: @{username_text}")
            else:
                bot.send_message(message.from_user.id, f"❌ Не удалось сбросить флаг для username: @{username_text}")
                logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} не смог сбросить флаг использованной ссылки для username: @{username_text}")
        else:
            bot.send_message(message.from_user.id, f"ℹ️ Пользователь с username: @{username_text} не найден в базе использованных ссылок")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} попытался сбросить флаг для несуществующего username: @{username_text}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при сбросе флага: {str(e)}")
        logging.error(f"Ошибка при сбросе флага использованной ссылки админом {message.from_user.username}|{message.from_user.id} для username @{username_text}: {str(e)}")
    
    # Очищаем состояние пользователя
    db_userstate.remove_user_state(message.from_user.id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_log'], chat_types=['private'])
def get_log_file(message):
    log_file_path = os.path.join(LOGS_DIR, 'bot_service.log')
    try:
        # Чтение и отправка последних 50 записей
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            lines = log_file.readlines()
            last_50_lines = lines[-50:] if len(lines) >= 50 else lines
            
            if last_50_lines:
                log_text = ''.join(last_50_lines)
                # Разбиваем на части если текст слишком длинный
                if len(log_text) > 4000:
                    chunks = [log_text[i:i+4000] for i in range(0, len(log_text), 4000)]
                    for i, chunk in enumerate(chunks[:3]):  # Ограничиваем 3 частями чтобы не спамить
                        caption = f"📋 Последние записи логов (часть {i+1}):\n```\n{chunk}\n```"
                        bot.send_message(message.from_user.id, caption)
                else:
                    caption = f"📋 Последние 50 записей логов:\n```\n{log_text}\n```"
                    bot.send_message(message.from_user.id, caption)
            else:
                bot.send_message(message.from_user.id, "📋 Файл логов пуст")
        
        # Отправка файла логов
        with open(log_file_path, 'rb') as log_file:
            bot.send_document(message.from_user.id, log_file, caption=f"📄 Файл логов {log_file_path}")
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно запросил и получил файл логов")
    
    except FileNotFoundError:
        bot.send_message(message.from_user.id, f"❌ Файл логов {log_file_path} отсутствует")
        logging.error(f"Админ {message.from_user.username}|{message.from_user.id} запросил файл логов - файл не найден")
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при отправке логов: {str(e)}")
        logging.error(f"Ошибка при отправке логов админу {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_used_links'], chat_types=['private'])
def get_used_links_file(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_used_links\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_used_links от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    try:
        # Получаем все записи о ссылках из базы данных username
        all_links = db_used_link_from_username.get_all_links()
        
        if not all_links:
            bot.send_message(message.from_user.id, "📋 База данных пуста - никто еще не получал ссылки")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил список выданных ссылок - база пуста")
            return
        
        # Формируем данные для вывода
        links_data = []
        for username, data in all_links.items():
            if data['is_used_link'] and data['link']:
                link_text = data['link'] if data['link'] else "ссылка отсутствует"
                date_str = data['created_at'] if data['created_at'] else "дата неизвестна"
                links_data.append(f"{username} - {link_text} - {date_str}")
        
        if not links_data:
            bot.send_message(message.from_user.id, "📋 Нет пользователей с выданными ссылками")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил список выданных ссылок - нет данных")
            return
        
        # Если записей меньше или равно 25, выводим в консоль
        if len(links_data) <= 25:
            result_text = "📋 Пользователи с выданными ссылками:\n\n" + "\n".join(links_data)
            caption = f"📋 Список пользователей с выданными ссылками:\n```\n{result_text}\n```"
            bot.send_message(message.from_user.id, caption, parse_mode='Markdown')
        
        # Создаем и отправляем файл в любом случае
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"used_links_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("Список пользователей с выданными ссылками:\n")
            file.write("=" * 50 + "\n")
            for line in links_data:
                file.write(line + "\n")
            file.write(f"\nВсего пользователей: {len(links_data)}")
        
        with open(filename, 'rb') as file:
            bot.send_document(
                message.from_user.id, 
                file, 
                caption=f"📄 Файл с выданными ссылками\nВсего записей: {len(links_data)}"
            )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
        
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно запросил и получил файл с выданными ссылками. Записей: {len(links_data)}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении списка ссылок: {str(e)}")
        logging.error(f"Ошибка при отправке списка ссылок админу {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_unused_links'], chat_types=['private'])
def get_unused_links_file(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_unused_links\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_unused_links от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    try:
        # Получаем белый список
        white_list = db_whitelist.get_white_list()
        
        if not white_list:
            bot.send_message(message.from_user.id, "📋 Белый список пуст")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил список неполучивших ссылки - белый список пуст")
            return
        
        # Проверяем каждого пользователя из белого списка
        unused_users = []
        for username in white_list.keys():
            # Используем метод is_link_used для проверки
            if not db_used_link_from_username.is_link_used(username):
                unused_users.append(username)
        
        if not unused_users:
            bot.send_message(message.from_user.id, "📋 Все пользователи из белого списка уже получили ссылки")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил список неполучивших ссылки - все получили")
            return
        
        # Сортируем по алфавиту для удобства
        unused_users.sort()
        
        # Если записей меньше или равно 25, выводим в сообщении
        if len(unused_users) <= 25:
            result_text = "📋 Пользователи которые еще не получали ссылки:\n\n" + "\n".join(unused_users)
            caption = f"📋 Список пользователей без выданных ссылок:\n```\n{result_text}\n```"
            bot.send_message(message.from_user.id, caption, parse_mode='Markdown')
        else:
            # Если много записей, отправляем только файл
            bot.send_message(message.from_user.id, f"📋 Найдено {len(unused_users)} пользователей без ссылок. Формирую файл...")
        
        # Создаем и отправляем файл в любом случае
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"unused_links_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("Список пользователей которые еще не получали ссылки:\n")
            file.write("=" * 60 + "\n")
            for i, username in enumerate(unused_users, 1):
                file.write(f"{i}. {username}\n")
            file.write(f"\nВсего пользователей без ссылки: {len(unused_users)}\n")
            file.write(f"Всего в белом списке: {len(white_list)}\n")
            file.write(f"Получили ссылки: {len(white_list) - len(unused_users)}\n")
            file.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        with open(filename, 'rb') as file:
            bot.send_document(
                message.from_user.id, 
                file, 
                caption=f"📄 Файл с пользователями без ссылок\n"
                       f"👤 Не получили: {len(unused_users)}\n"
                       f"📋 Всего в белом списке: {len(white_list)}"
            )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
        
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно запросил список неполучивших ссылки. "
                    f"Не получили: {len(unused_users)}/{len(white_list)}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении списка: {str(e)}")
        logging.error(f"Ошибка при отправке списка неполучивших ссылок админу {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['get_all_users'], chat_types=['private'])
def get_all_users_file(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /get_all_users\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /get_all_users от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    try:
        # Получаем всех пользователей из базы данных
        all_users = db_usernames.get_all_users()
        
        if not all_users:
            bot.send_message(message.from_user.id, "📋 База данных пользователей пуста")
            logging.info(f"Админ {message.from_user.username}|{message.from_user.id} запросил всех пользователей - база пуста")
            return
        
        # Сортируем пользователей по login_platform для удобства
        sorted_users = sorted(all_users.items(), key=lambda x: x[0].lower())
        
        # Формируем список строк в нужном формате
        result_lines = []
        for login_platform, user_data in sorted_users:
            username_tg = user_data.get('username_TG', '') or 'None'
            full_name = user_data.get('full_name', '') or 'None'
            created_at = user_data.get('created_at', '') or 'None'
            user_id = user_data.get('user_id', '') or 'None'
            
            # Используем табуляцию с фиксированной шириной
            line = f"{login_platform}\t{user_id}\t{created_at}\t{username_tg:20}\t{full_name:30}"
            result_lines.append(line)
        
        # Если записей меньше или равно 25, выводим в сообщении
        if len(sorted_users) <= 25:
            result_text = "\n".join(result_lines)
            caption = f"📋 Все пользователи ({len(sorted_users)}):\n```\n{result_text}\n```"
            bot.send_message(message.from_user.id, caption, parse_mode='Markdown')
        else:
            # Если много записей, отправляем только файл
            bot.send_message(message.from_user.id, f"📋 Найдено {len(sorted_users)} пользователей. Формирую файл...")
        
        # Создаем и отправляем файл в любом случае
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"all_users_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("Список всех пользователей:\n")
            file.write("Формат: login_platform[tab]user_id[tab]created_at[tab]username_tg[tab]full_name\n")
            file.write("=" * 80 + "\n")
            
            # Используем тот же result_lines для записи в файл
            for line in result_lines:
                file.write(line + "\n")
            
            file.write(f"\nВсего пользователей: {len(sorted_users)}\n")
            file.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        with open(filename, 'rb') as file:
            bot.send_document(
                message.from_user.id, 
                file, 
                caption=f"📄 Файл со всеми пользователями\n"
                       f"👤 Всего пользователей: {len(sorted_users)}"
            )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
        
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} успешно запросил всех пользователей. "
                    f"Найдено: {len(sorted_users)}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при получении списка пользователей: {str(e)}")
        logging.error(f"Ошибка при отправке списка всех пользователей админу {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(commands=['add_user_to_DB'], chat_types=['private'])
def add_user_to_db(message):
    if message.from_user.id not in ADMINS_USER_ID:
        bot.send_message(ADMINS_USER_ID[0], 
            f"⚠️ Попытка использования /add_user_to_DB\n"
            f"👤 Пользователь: {message.from_user.username or 'нет'} | {message.from_user.full_name} | {message.from_user.id}\n"
            f"💬 Чат: {message.chat.title or 'ЛС'} | {message.chat.id}")
        logging.warning(f"Неавторизованная попытка использования /add_user_to_DB от пользователя {message.from_user.username}|{message.from_user.full_name}|{message.from_user.id}")
        return
    
    bot.send_message(message.from_user.id, 
        "Введите данные пользователей для добавления в базу данных:\n\n"
        "Формат (через табуляцию):\n"
        "login_platform[пробел]-[пробел]username_TG[пробел]-[пробел]full_name[пробел]-[пробел]user_id\n\n"
        "Пример:\n"
        "john_doe - johndoe - John Doe - 12345\n"
        "alice_smith - alice - Alice Smith - 67890\n\n"
        "Можно вводить несколько пользователей (по одному на строку).\n"
        "Для отмены введите /cancel")
    
    # Используем базу данных для хранения состояния
    db_userstate.set_user_state(message.from_user.id, 'waiting_users_data_for_db')
    logging.info(f"Админ {message.from_user.username}|{message.from_user.id} начал добавление пользователей в базу данных")

    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(func=lambda message: db_userstate.get_user_state(message.from_user.id) == 'waiting_users_data_for_db', chat_types=['private'])
def handle_users_data_input(message):
    if message.from_user.id not in ADMINS_USER_ID:
        return
    
    users_text = message.text.strip()

    if (users_text == "/cancel"):
        db_userstate.remove_user_state(message.from_user.id)
        bot.send_message(message.from_user.id, "❌ Операция отменена")
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} отменил добавление пользователей в базу данных")
        return

    users_lines = [line.strip() for line in users_text.split('\n') if line.strip()]
    
    if not users_lines:
        bot.send_message(message.from_user.id, "❌ Список пользователей пуст")
        db_userstate.remove_user_state(message.from_user.id)
        logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} отправил пустой список для добавления в базу данных")
        return
    
    results = []
    success_count = 0
    error_count = 0
    
    try:
        for line in users_lines:
            # Парсим строку
            parts = line.split(' - ')
            
            if len(parts) != 4:
                results.append(f"❌ Неверный формат (ожидается 4 части): {line}")
                error_count += 1
                continue
            
            login_platform = parts[0].strip()
            username_TG = parts[1].strip()
            full_name = parts[2].strip()
            user_id_str = parts[3].strip()
            
            # Валидация login_platform
            if not login_platform:
                results.append(f"❌ Пустой login_platform: {line}")
                error_count += 1
                continue
            
            # Валидация user_id
            user_id = 0
            try:
                user_id = int(user_id_str)
                if user_id <= 0:
                    raise ValueError("User ID должен быть положительным числом")
            except ValueError as e:
                results.append(f"❌ Неверный user_id '{user_id_str}': {line}")
                error_count += 1
                continue
            
            # Обрабатываем username_TG (убираем @ если есть)
            if username_TG and username_TG.startswith('@'):
                username_TG = username_TG[1:]
            
            # Добавляем пользователя в базу данных
            success = db_usernames.add_user(
                login_platform=login_platform,
                user_id=user_id,
                full_name=full_name if full_name else None,
                username_TG=username_TG if username_TG else None
            )
            
            if success:
                results.append(f"✅ {login_platform} -> ID: {user_id} -> username: {username_TG}")
                success_count += 1
                logging.info(f"Пользователь {login_platform} (ID: {user_id}) -> username: {username_TG} добавлен в базу данных админом {message.from_user.username}|{message.from_user.id}")
            else:
                results.append(f"❌ {login_platform} (ID: {user_id}) - ошибка добавления")
                error_count += 1
                logging.warning(f"Не удалось добавить пользователя {login_platform} (ID: {user_id} -> username: {username_TG}) в базу данных админом {message.from_user.username}|{message.from_user.id}")
        
        result_text = f"📊 Результат добавления в базу данных:\nУспешно: {success_count}, Ошибок: {error_count}\n\n"
        result_text += "\n".join(results)
        
        # Если слишком много результатов, разбиваем на несколько сообщений
        if len(result_text) > 4000:
            chunks = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            for chunk in chunks:
                bot.send_message(message.from_user.id, chunk)
        else:
            bot.send_message(message.from_user.id, result_text)
        
        logging.info(f"Админ {message.from_user.username}|{message.from_user.id} завершил добавление пользователей в базу данных: успешно {success_count}, ошибок {error_count}")
    
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ Ошибка при добавлении списка пользователей: {str(e)}")
        logging.error(f"Ошибка при добавлении списка пользователей в базу данных админом {message.from_user.username}|{message.from_user.id}: {str(e)}")
    
    # Удаляем состояние пользователя
    db_userstate.remove_user_state(message.from_user.id)
    
    if message.chat.type != 'private':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение в чате {message.chat.id}: {str(e)}")

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    if message.chat.id != CHAT_ID:
        return
    
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            continue
            
        welcome_message = f"Добро пожаловать к нам в секту, {new_member.full_name}"
        if new_member.username:
            welcome_message += f" (@{new_member.username})"
        welcome_message += f"!\n\n"
        welcome_message += f"⚠️Пожалуйста⚠️, напиши свой учебный логин (ник) в теме #s21-welcome (https://t.me/c/1234567890/78).\n"
        welcome_message += f"Фото и реальное имя добавляй по желанию.\n\n"


        # добавляем теги
        user_info = db_usernames.get_user_by_user_id(new_member.id)

        if user_info:
            # Проверяем, была ли выдана ссылка (по username из основной базы)
            login_platform = user_info.get('login_platform')
            result = bot.set_chat_member_tag(chat_id=CHAT_ID, user_id=new_member.id, tag=str(login_platform))

            if result == False:
                logging.error(f"Пользователю user_id={new_member.id} не удалось установить статус: {login_platform}")

            logging.info(f"Пользователю {new_member.id} успешно установлен тег: {login_platform}")

        else:
            bot.send_message(message.from_user.id, f"❌ Пользователь с ID {user_id} не найден в базе данных")
            logging.warning(f"Админ {message.from_user.username}|{message.from_user.id} запросил информацию о несуществующем пользователе {user_id}")
        
        try:
            bot.send_message(chat_id=new_member.id, text=welcome_message)
            logging.info(f"Приветственное сообщение отправлено новому участнику {new_member.full_name}|@{new_member.username}|{new_member.id}")
        except Exception as e:
            logging.error(f"Ошибка отправки приветственного сообщения участнику {new_member.full_name}|@{new_member.username}|{new_member.id}: {str(e)}")

# ====================== ЗАПУСК БОТА ======================
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    db_used_link_from_ID = IsUsedLinkFromIDDB(os.path.join(DATA_DIR, 'is_used_link_from_ID.db'))
    db_used_link_from_username = IsUsedLinkFromUsernameDB(os.path.join(DATA_DIR, 'is_used_link_from_username.db'))
    db_usernames = UsernamesToUserIDDB(os.path.join(DATA_DIR, 'usernames_to_user_id.db'))
    db_userstate = UserStateDB(os.path.join(DATA_DIR, 'user_state.db'))
    db_whitelist = WhiteListDB(os.path.join(DATA_DIR, 'white_list.db'))
    db_verification_code = VerificationCodeDB(os.path.join(DATA_DIR, 'verification_code.db'))

    logging.info("Бот запущен и готов к работе")
    bot.infinity_polling()
except Exception as e:
    logging.critical(f"Критическая ошибка в работе бота: {str(e)}")