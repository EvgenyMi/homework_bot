import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from endpoints import ENDPOINT
from exceptions import (NotNewWorksException, NotOkStatusException,
                        UnavailableException)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TEL_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TEL_CHAT_ID')

RETRY_PERIOD = 600
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем наличие токенов."""
    if all([
        PRACTICUM_TOKEN is not None,
        TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None,
    ]) == True:
        return True
    logging.critical('Не хватает токенов')
    return False


def send_message(bot, message):
    """Отправка сообщения в чат."""
    try:
        logging.debug('Успешная отправка сообщения в Telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Не удаётся отправить сообщение: {error}')


def get_api_answer(timestamp):
    """Получение ответа от API Яндекс Практикума."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
        if response.status_code != HTTPStatus.OK:
            logging.error('Эндпоинт недоступен')
            raise NotOkStatusException('Эндпоинт недоступен')
        if isinstance(response.json(), dict):
            return response.json()
        else:
            raise ValueError('В ответе от API не словарь')
    except ConnectionError:
        logging.error('Проблемы в соединении')
        raise ConnectionError('Проблемы в соединении')
    except requests.RequestException:
        logging.error('URL недоступен')
        raise UnavailableException('URL недоступен')


def check_response(response):
    """Проверка ответа."""
    if not isinstance(response, dict):
        logging.error('API передал не словарь')
        raise TypeError('API передал не словарь')
    homeworks = response.get('homeworks')
    if homeworks is None:
        logging.error('API не содержит ключа homeworks')
        raise KeyError('API не содержит ключа homeworks')
    if not isinstance(homeworks, list):
        logging.error('Это не список')
        raise TypeError('Это не список')
    return homeworks


def parse_status(homework):
    """Получаем информацию о судьбе домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('В ответе нет ключа homework_name')
        raise KeyError('В ответе нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logging.error('В ответе нет ключа homework_status')
        raise KeyError('В ответе нет ключа homework_status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        logging.error('Статус домашней работы неизвестен')
        raise KeyError('Статус домашней работы неизвестен')
    if verdict is None:
        logging.error(f'Неизвестный статус домашней работы: {homework_status}')
        raise ValueError(
            f'Неизвестный статус домашней работы: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
    if not check_tokens():
        logging.critical('Не хватает токенов')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    cache = []
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            try:
                (homeworks[0])
            except IndexError:
                logging.critical('Нет новых работ на проверку')
                raise NotNewWorksException('Нет новых работ на проверку')
            message = parse_status(homeworks[0])
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            if message in cache:
                logging.debug('Новых статусов нет')
            else:
                cache.append(message)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
