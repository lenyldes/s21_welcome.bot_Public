# for f in ./logs/bot_service.log*; do                                                                                                                                                                        git:(main) ✗
#     cat "$f" | grep "process_code_verification"
# done >> 3.txt

# python3 fix.py 3.txt

import re
import sys
from pathlib import Path

def parse_log(log_text: str):
    """
    Извлекает из лога:
    - Для fix.txt: (user_id, new_username, link)
    - Для fix_2.txt: (new_username, old_username, first_name, user_id)
    """
    # Паттерн для строки "Ссылка https://t.me/+... создана для пользователя ...|ID с ником username"
    link_pattern = re.compile(
        r'Ссылка (https?://t\.me/[^\s]+) создана для пользователя .*?\|(\d+) с ником (\S+)'
    )
    # Паттерн для строки "Обработка кода верификации от пользователя username|first_name|user_id"
    process_pattern = re.compile(
        r'Обработка кода верификации от пользователя ([^|]+)\|([^|]+)\|(\d+)'
    )
    # Паттерн для строки "Код верификации ... успешно подтвержден для пользователя ...|user_id с ником 'new_username'"
    confirm_pattern = re.compile(
        r'Код верификации \d+ успешно подтвержден для пользователя .*?\|(\d+) с ником \'([^\']+)\''
    )

    links = []          # для fix.txt: (user_id, new_username, link)
    user_info = {}      # для fix_2.txt: key=user_id -> (old_username, first_name)
    new_usernames = {}  # key=user_id -> new_username

    # Сначала собираем все данные
    for line in log_text.splitlines():
        # Ищем ссылки
        link_match = link_pattern.search(line)
        if link_match:
            link, user_id_str, username = link_match.groups()
            user_id = int(user_id_str)
            links.append((user_id, username, link))
            continue

        # Ищем строки обработки (старый username и first_name)
        proc_match = process_pattern.search(line)
        if proc_match:
            old_username, first_name, user_id_str = proc_match.groups()
            user_id = int(user_id_str)
            user_info[user_id] = (old_username, first_name)
            continue

        # Ищем строки подтверждения (новый username)
        conf_match = confirm_pattern.search(line)
        if conf_match:
            user_id_str, new_username = conf_match.groups()
            user_id = int(user_id_str)
            new_usernames[user_id] = new_username

    # Формируем список для fix_2.txt, объединяя данные по user_id
    fix2_entries = []
    for user_id, (old_username, first_name) in user_info.items():
        if user_id in new_usernames:
            new_username = new_usernames[user_id]
            fix2_entries.append((new_username, old_username, first_name, user_id))

    # Для fix.txt берём ссылки (уникальные по user_id)
    unique_links = {}
    for user_id, new_username, link in links:
        # если для одного user_id несколько ссылок – возьмём последнюю (или первую)
        unique_links[user_id] = (new_username, link)
    fix_entries = [(user_id, new_username, link) for user_id, (new_username, link) in unique_links.items()]

    return fix_entries, fix2_entries

def generate_fix_txt(entries, output_file="fix.txt"):
    lines = ["users_data = ["]
    for user_id, username, link in entries:
        lines.append(f"        ({user_id}, \"{username}\", \"{link}\"),")
    lines.append("    ]")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Файл {output_file} успешно создан с {len(entries)} записями.")

def generate_fix2_txt(entries, output_file="fix_2.txt"):
    lines = []
    for new_username, old_username, first_name, user_id in entries:
        lines.append(f"{new_username} - {old_username} - {first_name} - {user_id}")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Файл {output_file} успешно создан с {len(entries)} записями.")

def main():
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
        if not log_path.is_file():
            print(f"Ошибка: файл {log_path} не найден.", file=sys.stderr)
            sys.exit(1)
        log_text = log_path.read_text(encoding="utf-8")
    else:
        print("Чтение лога из stdin (завершите ввод Ctrl+D):")
        log_text = sys.stdin.read()

    fix_entries, fix2_entries = parse_log(log_text)
    if not fix_entries and not fix2_entries:
        print("Не найдено ни одной записи. Проверьте формат лога.", file=sys.stderr)
        sys.exit(1)

    if fix_entries:
        generate_fix_txt(fix_entries)
    else:
        print("Нет данных для fix.txt (не найдены строки со ссылками).")

    if fix2_entries:
        generate_fix2_txt(fix2_entries)
    else:
        print("Нет данных для fix_2.txt (не найдены строки обработки/подтверждения).")

if __name__ == "__main__":
    main()