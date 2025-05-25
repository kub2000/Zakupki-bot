import requests
import time
import json
import os

BOT_TOKEN = '8095946119:AAHDmPzbFSsy55V79MbxX-ussbluPaTpbCI'
URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
users = {}  # user_id -> username
user_tasks = {}  # user_id -> list of {'from': user_id, 'caption': text, 'file_id': id, 'file_type': 'photo'/'document'}
user_names = {}  # сохранённые имена пользователей
user_states = {}  # состояния пользователей
last_update_id = 0
names_file = 'user_names.json'

if os.path.exists(names_file):
    with open(names_file, 'r') as f:
        user_names = json.load(f)

def save_user_names():
    with open(names_file, 'w') as f:
        json.dump(user_names, f)

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(f'{URL}/sendMessage', json=data)

def forward_file(to_id, task):
    if task['file_type'] == 'photo':
        requests.post(f'{URL}/sendPhoto', json={
            'chat_id': to_id,
            'photo': task['file_id'],
            'caption': task['caption'],
            'reply_markup': get_done_markup()
        })
    else:
        requests.post(f'{URL}/sendDocument', json={
            'chat_id': to_id,
            'document': task['file_id'],
            'caption': task['caption'],
            'reply_markup': get_done_markup()
        })

def get_main_menu():
    return {
        'keyboard': [
            ["Мои задачи"],
            ["Добавить задачу"],
            ["Добавить пользователя"],
            ["Изменить имя пользователя"]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def get_user_buttons(for_user_id=None, action="choose"):
    buttons = []
    for uid, uname in users.items():
        name = user_names.get(str(uid), f"@{uname if isinstance(uname, str) else uid}")
        if for_user_id is None or uid != for_user_id:
            buttons.append([f"{name} [{uid}]"])
    return {'keyboard': buttons, 'resize_keyboard': True}

def get_done_markup():
    return {
        'inline_keyboard': [[{'text': 'Сделано', 'callback_data': 'done'}]]
    }

def handle_update(update):
    global users, user_tasks, user_states
    message = update.get('message')
    callback = update.get('callback_query')

    if message:
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from'].get('username', str(user_id))
        users[user_id] = username

        text = message.get('text')
        contact = message.get('contact')

        if contact:
            send_message(chat_id, "Контакт получен.")
            return

        if user_id in user_states:
            state = user_states[user_id]
            if state.startswith("rename_"):
                target_id = int(state.split("_")[1])
                user_names[str(target_id)] = text
                save_user_names()
                send_message(chat_id, "Имя пользователя обновлено.", get_main_menu())
                del user_states[user_id]
                return

        if text == '/start':
            send_message(chat_id, "Добро пожаловать!", get_main_menu())

        elif text == "Мои задачи":
            tasks = user_tasks.get(user_id, [])
            if not tasks:
                send_message(chat_id, "У вас нет задач.")
            else:
                for task in tasks:
                    forward_file(chat_id, task)

        elif text == "Добавить задачу":
            send_message(chat_id, "Выберите пользователя:", get_user_buttons(for_user_id=user_id))
            user_states[user_id] = "choose_user"

        elif text == "Добавить пользователя":
            send_message(chat_id, "Поделитесь контактом с помощью кнопки прикрепления файла.")

        elif text == "Изменить имя пользователя":
            send_message(chat_id, "Выберите пользователя, чьё имя вы хотите изменить:", get_user_buttons())
            user_states[user_id] = "choose_rename"

        elif text and '[' in text and ']' in text:
            uid = int(text.split('[')[-1].strip(']'))
            state = user_states.get(user_id)
            if state == "choose_user":
                user_states[user_id] = f"awaiting_file_{uid}"
                name = user_names.get(str(uid), f"@{users.get(uid, uid)}")
                send_message(chat_id, f"Теперь отправьте файл с подписью — это будет задача для {name}.")
            elif state == "choose_rename":
                user_states[user_id] = f"rename_{uid}"
                send_message(chat_id, "Введите новое имя для пользователя:")

        elif 'photo' in message or 'document' in message:
            state = user_states.get(user_id, "")
            if state.startswith("awaiting_file_"):
                target = int(state.split("_")[-1])
                file_id = message['photo'][-1]['file_id'] if 'photo' in message else message['document']['file_id']
                caption = message.get('caption', '(без описания)')
                file_type = 'photo' if 'photo' in message else 'document'
                task = {'from': user_id, 'caption': caption, 'file_id': file_id, 'file_type': file_type}
                user_tasks.setdefault(target, []).append(task)
                name = user_names.get(str(target), f"@{users.get(target, str(target))}")
                send_message(chat_id, f"Задача отправлена {name}.", get_main_menu())
                send_message(target, f"Вам новая задача от @{username}")
                del user_states[user_id]

    elif callback:
        data = callback['data']
        message_id = callback['message']['message_id']
        chat_id = callback['message']['chat']['id']
        from_id = callback['from']['id']

        if data == 'done':
            tasks = user_tasks.get(from_id, [])
            for task in tasks:
                if task['caption'] in callback['message'].get('caption', ''):
                    user_tasks[from_id].remove(task)
                    send_message(task['from'], f"{user_names.get(str(from_id), '@'+users.get(from_id, str(from_id)))} выполнил задачу: {task['caption']}")
                    break
            requests.post(f'{URL}/deleteMessage', json={
                'chat_id': chat_id,
                'message_id': message_id
            })

def get_updates():
    global last_update_id
    resp = requests.get(f'{URL}/getUpdates', params={'offset': last_update_id + 1}).json()
    if 'result' in resp:
        for update in resp['result']:
            last_update_id = update['update_id']
            handle_update(update)

while True:
    try:
        get_updates()
        time.sleep(1)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(3)