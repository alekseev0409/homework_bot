import time
import requests
import telegram
import logging
import sys
from constants import (
    RETRY_PERIOD,
    ENDPOINT,
    HEADERS,
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    HOMEWORK_VERDICTS,
)
from exception import (
    EnvNotFound,
    ErrorStatusHomework,
    UnavailableApi,
    UrlError
)
from http import HTTPStatus


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s, %(levelname)s, %(name)s, %(message)s",
    filename="main.log",
    filemode="w",
)
logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    """Функция проверят наличие переменных окружения.

    :return: все ли переменные окружения установлены
    """
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return False
    return True


def send_message(bot: telegram.Bot, message: str) -> bool:
    """Функция отправляет сообщения в чат телеграм-бота.
    :param bot:
    :param message: текст сообщения

    :return: Отправлено ли сообщение
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Сообщение отправлено")
        return True
    except:
        logger.error("Ошибка при отправке задания из бота")
        return False


def get_api_answer(timestamp: float = None) -> dict:
    """Получаем информацию.
    :param timestamp: время, для которого просматриваем домашние работы
    :return: результат корректного ответа от энд-поинта
    """
    now_timestamp = int(timestamp or time.time())
    params = {"from_date": now_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK.value:
            return response.json()
        else:
            logger.error("Сбой при запросе к эндпоинту!")
            raise UnavailableApi
    except requests.RequestException():
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
    """Функция проверяет статус текущей домашней работы.
    :param homework: словарь с параметрами домашней работы
    :return: текстовая строчка с уведомлением об изменении статуса
    """
    if "homework_name" in homework.keys() and "status" in homework.keys():
        homework_name = homework["homework_name"]
        status = homework["status"]
        if status in HOMEWORK_VERDICTS.keys():
            return f'Изменился статус проверки работы "{homework_name}". ' \
                   f'Текущий статус работы - {HOMEWORK_VERDICTS[status]}'
    raise ErrorStatusHomework


def main():
    """Основная логика работы бота.
    :return: None
    """
    prev_message = ""
    cur_error = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        if not check_tokens():
            logger.critical("Недоступны переменные окружения!")
            sys.exit("Недоступны переменные окружения!")
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                homeworks = response["homeworks"]
                if len(homeworks) == 0:
                    logger.debug("В работе нет изменений")
                for homework in homeworks:
                    message = parse_status(homework)
                    if message != prev_message:
                        send_message(bot, message)
                        send_message(bot,
                                     HOMEWORK_VERDICTS[homework['status']]
                                     )
                logger.debug("Все домашние работы проверены")
            else:
                logger.error("Ошибка в формате данных ответа.")

        except (EnvNotFound, UrlError,
                ErrorStatusHomework, UnavailableApi) as enf:
            message = f"Сбой в работе программы: {enf}"
            logger.error(message)
            if cur_error != enf.__name__():
                cur_error = enf.__name__()
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
