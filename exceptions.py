class NotOkStatusException:
    """Статут ответа от API не 200."""

    pass


class NotNewWorksException:
    """Нет новых работ на проверку"""

    pass


class RequestException:
    """Проблемы с доступом к url"""

    pass


class UnavailableException:
    """URL недоступен"""

    pass
