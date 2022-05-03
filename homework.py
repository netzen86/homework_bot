from custom_exception import (
    NotCorrectAPIAnswer,
    TokensMissing,
    TelegaMessageNotSent,
    APIReturnNon200,
    KeysMissing
)
from dotenv import load_dotenv
from telegram import Bot
import requests
import logging
import time
import os


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN_YNX')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGA')
TELEGRAM_CHAT_ID = 918325986

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s,'
)


def send_message(bot, message):
    """Отправка сообщения в телегу."""
    chat = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat, message)
        logging.info('Статус работы отправлен в телегу')
    except TelegaMessageNotSent:
        logging.error('Не удалось отправить в телегу')


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс практикума."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code != 200:
        raise APIReturnNon200('Функция get_api_answer вернула не 200')
    hw = homework_statuses.json()
    if isinstance(hw, list):
        hw = hw[0]
    hw.update({'sc': homework_statuses.status_code})
    return hw


def check_response(response):
    """Проверка ответа API Яндекс практикума."""
    sc = response.pop('sc')
    if sc != 200:
        raise APIReturnNon200('Функция get_api_answer вернула не 200')
    if isinstance(response, dict):
        if isinstance(response.get('homeworks'), list):
            if len(response.get('homeworks')):
                if 'homework_name' or 'status' in response.get(
                    'homeworks'
                )[0].keys():
                    return response.get('homeworks')
                else:
                    raise KeysMissing(
                        'отсутствие ожидаемых ключей в ответе API'
                    )
            return response.get('homeworks')
        else:
            raise NotCorrectAPIAnswer('Под ключом `homeworks` не список')
    else:
        raise NotCorrectAPIAnswer('Функция get_api_answer вернула не словарь')


def parse_status(homework):
    """Подготовка сообщения для отправки в телегу."""
    print(homework)
    if len(homework):
        if isinstance(homework, list):
            homework = homework[0]
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        if homework_status not in HOMEWORK_STATUSES.keys():
            logging.error('недокументированный статус домашней работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия необходимых токенов."""
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN:
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует какой то токен =)')
        raise TokensMissing

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            checked_response = check_response(response)
            if checked_response:
                message = parse_status(checked_response)
                send_message(bot, message)
            logging.debug('отсутствие в ответе новых статусов')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
