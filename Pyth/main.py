import telebot
import random
from telebot import types
from datetime import datetime, timedelta
import json
import requests
import time
import uuid
from yookassa import Payment
from config import BOT_TOKEN, FOLDER_ID, SERVICE_ACCOUNT_ID, YANDEX_PRIVATE_KEY_PATH, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL, TRIAL_PRICE, MONTHLY_PRICE
from flask import Flask, request
import os
import logging
from dotenv import load_dotenv
load_dotenv()
from yookassa import Configuration
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from db import init_db, set_subscription_active, is_subscription_active, get_subscription_expiry

WEBHOOK_URL = 'https://i-am-bog.onrender.com/'  # пример: https://taro-bot.onrender.com/

bot = telebot.TeleBot(BOT_TOKEN)

bot.remove_webhook()

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Пример хранилища подписок
subscriptions = {}

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/yookassa_webhook', methods=['POST'])
def yookassa_webhook():
    payload = request.get_json()

    if payload.get("event") == "payment.succeeded":
        payment = payload["object"]
        user_id = int(payment["metadata"]["user_id"])
        sub_type = payment["metadata"].get("subscription_type", "trial")

        # Активируем подписку
        set_subscription_active(user_id, days=30)
        print(f"✅ Подписка ({sub_type}) активирована для пользователя {user_id}")

        # Автопродление после пробной
        if sub_type == "trial":
            def auto_renew():
                payment = Payment.create({
                    "amount": {
                        "value": "689.00",
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": YOOKASSA_RETURN_URL
                    },
                    "capture": True,
                    "description": f"Автопродление подписки для user_id {user_id}",
                    "metadata": {
                        "user_id": str(user_id),
                        "subscription_type": "auto"
                    }
                }, uuid.uuid4())

                bot.send_message(user_id,
                    f"🔁 Срок пробной подписки истёк. Перейдите по ссылке для продления:\n{payment.confirmation.confirmation_url}")

            from threading import Timer
            Timer(30 * 24 * 60 * 60, auto_renew).start()

    return '', 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200


# Путь к ключу сервисного аккаунта
KEY_FILE = 'sa_key.json'

# Получение IAM токена из сервисного аккаунта
def get_iam_token():
    with open(KEY_FILE, 'r') as f:
        sa_key = json.load(f)

    import jwt
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    payload = {
        "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        "iss": sa_key["service_account_id"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp())
    }

    encoded_jwt = jwt.encode(
        payload,
        sa_key["private_key"],
        algorithm="PS256",
        headers={"kid": sa_key["key_id"]}  # <--- ОБЯЗАТЕЛЬНО!
    )

    response = requests.post(
        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        headers={"Content-Type": "application/json"},
        json={"jwt": encoded_jwt}
    )

    if response.status_code == 200:
        return response.json()["iamToken"]
    else:
        raise Exception(f"Ошибка получения IAM токена: {response.text}")

# Все карты Таро
TAROT_CARDS = [
    'Шут', 'Маг', 'Верховная Жрица', 'Императрица', 'Император', 'Иерофант', 'Влюбленные', 'Колесница',
    'Сила', 'Отшельник', 'Колесо Фортуны', 'Справедливость', 'Повешенный', 'Смерть', 'Умеренность',
    'Дьявол', 'Башня', 'Звезда', 'Луна', 'Солнце', 'Суд', 'Мир'
] + [f'{rank} {suit}' for suit in ['жезлов', 'кубков', 'мечей', 'пентаклей'] for rank in [
    'Туз', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Паж', 'Рыцарь', 'Королева', 'Король']]

# Сохраняем временные данные
user_data = {}

# Замените на ваш актуальный IAM токен и ID каталога

def ask_yandex_gpt(prompt_text):
    iam_token = get_iam_token()  # получаем новый токен каждый раз
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты опытный таролог, анализируй расклад карт и отвечай по делу, как человек."
            },
            {
                "role": "user",
                "text": prompt_text
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        return result["result"]["alternatives"][0]["message"]["text"]
    else:
        print("Ошибка при запросе к YandexGPT:", response.text)
        return "Произошла ошибка при обработке запроса. Попробуйте позже."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
        "Добро пожаловать! Я помогу тебе сделать магический расклад и предсказание на любой интересующий вопрос ✨\n\n"
"Сформулируй свой вопрос и отправь его мне.\n"
"Ты можешь выбрать карты прямо здесь в боте или указать их вручную через запятую, если используешь свою колоду 🃏\n\n"
"Пример вопроса:\n"
"Наладятся ли отношения с мамой?\n"
"Пример расклада:\n"
"Императрица, Башня, 2 кубков\n\n"
"P.S. Если что-то пошло не так — просто напиши /start\n"
"Меню находится внизу рядом с полем ввода сообщения 👇"
    )

# Обработка команды /question
@bot.message_handler(commands=['question'])
def handle_question(message):
    bot.send_message(message.chat.id, "Напиши своё имя и возраст (например: Алена 23)")
    bot.register_next_step_handler(message, ask_question)

def ask_question(message):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Неверный формат. Введите как: Имя 23")
        return
    user_data[message.chat.id] = {'name': parts[0], 'age': parts[1]}
    bot.send_message(message.chat.id, "Теперь напиши свой вопрос для расклада:")
    bot.register_next_step_handler(message, ask_card_choice)

def ask_card_choice(message):
    user_data[message.chat.id]['question'] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Выбрать 3 карты", callback_data='choose_cards'))
    markup.add(types.InlineKeyboardButton("Ввести свои карты", callback_data='write_cards'))
    bot.send_message(message.chat.id, "Выбери, как ты хочешь получить карты:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'choose_cards')
def handle_choose_cards(call):
    chat_id = call.message.chat.id

    #  Проверка подписки
    if not is_subscription_active(chat_id):
        bot.answer_callback_query(call.id, "Нет активной подписки.")
        bot.send_message(chat_id, "У вас нет активной подписки. Пожалуйста, оформите её, чтобы продолжить.")
        return

    selected = random.sample(TAROT_CARDS, 3)
    user_data[chat_id]['cards'] = selected

    cards_text = "\n".join(selected)
    question = user_data[chat_id]['question']

    bot.send_message(chat_id, f"Ваши карты:\n{cards_text}\n\nПожалуйста, подождите, идет интерпретация...")

    # Если пользователя нет в словаре, создаем его
    if chat_id not in user_data:
        user_data[chat_id] = {}

    user_data[chat_id]['cards'] = selected
    question = user_data[call.message.chat.id]['question']
    interpretation = generate_ai_interpretation(question, selected)
    bot.send_message(call.message.chat.id, f"Карты: {', '.join(selected)}\n\n{interpretation}")

@bot.callback_query_handler(func=lambda call: call.data == 'write_cards')
def handle_write_cards(call):
    bot.send_message(call.message.chat.id, "Напиши три карты через запятую. Пример: Влюбленные, Справедливость, 6 мечей")
    bot.register_next_step_handler(call.message, handle_user_cards)

def handle_user_cards(message):
    cards = [card.strip() for card in message.text.split(',')]
    if len(cards) != 3:
        bot.send_message(message.chat.id, "Нужно ввести ровно 3 карты через запятую.")
        return
    user_data[message.chat.id]['cards'] = cards
    question = user_data[message.chat.id]['question']
    interpretation = generate_ai_interpretation(question, cards)
    bot.send_message(message.chat.id, f"Карты: {', '.join(cards)}\n\n{interpretation}")

def generate_ai_interpretation(question, cards):
    prompt = f"Вопрос: {question}\nКарты: {', '.join(cards)}\nНекоторые карты могут быть перевёрнутыми. Дай подробную, но лаконичную интерпретацию расклада."
    return ask_yandex_gpt(prompt)

@bot.callback_query_handler(func=lambda call: call.data.startswith("selected_cards:"))
def handle_card_selection(call):
    selected_cards = call.data.split(":")[1].split(",")
    question = user_data[call.from_user.id]['question']

    prompt = f"Вопрос: {question}\nКарты: {', '.join(selected_cards)}\nДай интерпретацию расклада."
    interpretation = ask_yandex_gpt(prompt)

    bot.send_message(call.message.chat.id, f"🔮 Интерпретация расклада:\n{interpretation}")

# Обработка команды /help

@bot.message_handler(commands=['help'])
def handle_help(message):
    text = '''Как пользоваться ботом ⬇️

В нашем боте есть веб-карты (онлайн-карты, они для тех, у кого нет карт на руках), чтобы воспользоваться этой функцией:
1. Нажмите на кнопку «задать вопрос», после этого напишите ваш вопрос.
2. После вопроса, внизу в меню выйдет окно «получить карты», нажмите на эту кнопку.
3. Выберите интуитивно карты, затем дождитесь вашего расклада 🙏🏼

Также можно самому ввести карты, если есть физическая колода:
• Нажмите на кнопку «задать вопрос».
• Напишите свой вопрос для расклада и отправьте боту.
• Сделайте расклад и выпавшие карты введите в бота (карты вводите через запятую).
• А теперь ждите трактовку расклада.

Пример работы с ботом:

Стоит ли мне идти на мероприятие?
Пример выпавших карт:
Влюбленные, Справедливость, перевернутый Паж кубков.
(Бот также работает с перевернутыми картами)

С любовью ❤️ Ваш персональный бот

<a href='https://telegra.ph/Polzovatelskoe-soglashenie-12-16-9'>Пользовательское соглашение</a>
'''
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# Обработка команды /subscriptions

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

@bot.message_handler(commands=['subscriptions'])
def handle_subscriptions(message):
    user_id = message.chat.id
    now = datetime.now()
    expiry = get_subscription_expiry(user_id)
    if expiry and datetime.fromisoformat(expiry) > datetime.now():
        bot.send_message(user_id, f"✅ Подписка активна до {datetime.fromisoformat(expiry).strftime('%d.%m.%Y %H:%M')}")
    else:
        markup = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(
            "🆓 Оформить пробную подписку (99₽)",
            url=create_yookassa_payment_url(user_id)  # Ссылка на оплату
        )
        markup.add(pay_button)
        bot.send_message(user_id, "У вас нет активной подписки. Хотите оформить пробную на 1 день (99₽)?", reply_markup=markup)


def create_yookassa_payment_url(user_id):
    payment = Payment.create({
        "amount": {
            "value": "99.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": YOOKASSA_RETURN_URL
        },
        "capture": True,
        "description": f"Пробная подписка для user_id {user_id}",
        "metadata": {
            "user_id": str(user_id),
            "subscription_type": "trial"
        }
    }, uuid.uuid4())
    return payment.confirmation.confirmation_url


if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)



