import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from exception import (CheckHomeworkStatus, UnavailableApi)
from constants import (
    RETRY_PERIOD,
    ENDPOINT,
    HEADERS,
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    HOMEWORK_VERDICTS
)

status_all_homeworks = {}


def init_logger() -> logging.Logger:
    """Настройки и инициализация логгера."""
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


logger = init_logger()


def check_tokens() -> bool:
    """
    Функция проверят наличие переменных окружения.

    :return: все ли переменные окружения установлены
    """
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return False
    return True


def get_api_answer(timestamp: float = None) -> dict:
    """
    Получаем информацию.
    :param timestamp: время, для которого просматриваем домашние работы
    :return: результат корректного ответа от энд-поинта
    """
    now_timestamp = int(timestamp or time.time())
    params = {"from_date": now_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error("Сбой при запросе к эндпоинту!")
            raise UnavailableApi
        else:
            return response.json()

    except requests.exceptions.RequestException:
        logger.error("Сбой при запросе к эндпоинту!")
        raise UnavailableApi


def check_response(response: dict) -> None:
    """
    Функция проверят правильность формата данных.
    :param response: словарь с параметрами домашних работ
    :return: None
    Выбрасывается исключение, если тип не соответствует данному формату
    """
    if not isinstance(response, dict):
        raise TypeError
    if "homeworks" not in response.keys() and\
       "current_date" in response.keys():
        raise TypeError
    if not isinstance(response["homeworks"], list):
        raise TypeError
    if not isinstance(response["current_date"], int):
        raise TypeError


def parse_status(homework: dict) -> str:
    """информации о конкретной домашней работе, статус этой работы."""
    if 'homework_name' not in homework:
        message_error = ('Ошибка проверка статуса домашней работы, '
                         'отсутствует искомый ключ "homework_name"')
        raise KeyError(message_error)
    if 'status' not in homework:
        message_error = ('Ошибка проверка статуса домашней работы, '
                         'отсутствует искомый ключ "status"')
        raise KeyError(message_error)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message_error = (f'Ошибка проверка статуса домашней работы, '
                         f'недокументированный статус: {homework_status}')
        raise CheckHomeworkStatus(message_error)
    if homework_name not in status_all_homeworks:
        status_all_homeworks[homework_name] = homework_status
        verdict = HOMEWORK_VERDICTS[homework_status]
        return (f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')
    if homework_status != status_all_homeworks[homework_name]:
        status_all_homeworks[homework_name] = homework_status
        verdict = HOMEWORK_VERDICTS[homework_status]
        return (f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')
    message = (f'Cтатус домашней "{homework_name}" '
               f'работы, не изменился')
    logger.debug(message)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение успешно отправлено в Telegram: {message}')
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в Telegram: {error}')


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют необходимые переменные окружения'
        logger.critical(message)
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    chek_send_message_error = False
    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_response(response)
            for homework_dict in response['homeworks']:
                verdict_status = parse_status(homework_dict)
                if verdict_status is not None:
                    send_message(bot, verdict_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if not chek_send_message_error:
                send_message(bot, message)
                chek_send_message_error = True
        finally:
            time.sleep(RETRY_PERIOD)
            current_timestamp = int(time.time())


if __name__ == '__main__':
    main()
