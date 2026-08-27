import os
import requests
import logging
import json

# ====================== НАСТРОЙКИ ======================

ROCKET_TOKEN = os.getenv("ROCKET_TOKEN", "")
ROCKET_ID = os.getenv("ROCKET_ID", "")
ROCKETCHAT_URL = os.getenv("ROCKETCHAT_URL", "https://chat.example.com")

# ====================== ФУНКЦИИ ОТПРАВКИ СООБЩЕНИЙ В ROCKET CHAT ======================

def api_post(endpoint, data):
    """Упрощённая функция POST-запроса"""
    url = f"{ROCKETCHAT_URL}/api/v1/{endpoint}"
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": ROCKET_TOKEN,
        "X-User-Id": ROCKET_ID,
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if not response.ok:
            logging.error(f"Ошибка запроса {endpoint}: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        logging.error(f"Исключение при запросе {endpoint}: {str(e)}")
        return None

def send_dm(username, text):
    """Создать (или получить) личный чат и отправить сообщение"""
    try:
        res = api_post("im.create", {"username": username})
        if res is None:
            logging.error(f"Ошибка при создании чата с пользователем @{username}")
            return False
        
        room_id = res.get("room", {}).get("_id")
        if not room_id:
            logging.error(f"Не удалось получить roomId для пользователя @{username}")
            return False

        res = api_post("chat.postMessage", {"roomId": room_id, "text": text})
        if res and res.get("success"):
            logging.info(f"Сообщение {text} успешно отправлено пользователю @{username}")
            return True
        else:
            logging.error(f"Ошибка при отправке сообщения {text} пользователю @{username}: {res}")
            return False
            
    except Exception as e:
        logging.error(f"Исключение при отправке сообщения {text} пользователю @{username}: {str(e)}")
        return False