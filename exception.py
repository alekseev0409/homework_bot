class UrlError(Exception):
    def __str__(self) -> str:
        return "Ошибка с доступом к URL"


class ErrorStatusHomework(Exception):
    def __str__(self) -> str:
        return "Неожиданный статус работы!"


class UnavailableApi(Exception):
    def __str__(self) -> str:
        return "Сбой при запросе к API!"

class CheckHomeworkStatus(Exception):
    def __init__(self, text):
        self.txt = text
