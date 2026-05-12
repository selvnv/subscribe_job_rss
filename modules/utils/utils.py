"""Модуль утилит для вспомогательных операций CLI.

Предоставляет функцию постраничного табличного вывода записей в терминал
с использованием библиотеки tabulate.
"""

from math import ceil
from tabulate import tabulate


def print_table_paged(row_data,
                         headers: list,
                         page_size: int = 8):
    """Вывести записи в постраничной таблице с пагинацией в терминале.

    Разбивает список записей на страницы по page_size строк и выводит
    их с помощью tabulate. Пользователь нажимает Enter для продолжения
    или 'q' для выхода.
    """
    # Проверить, что данные не пусты
    if not row_data:
        print(f"\033[1m\033[94m[INFO] >>>>\033[0m No data to display")
        return

    # Вычислить общее количество строк и страниц
    total_rows = len(row_data)
    total_pages = ceil(total_rows / page_size)

    current_page = 0

    # Итерировать по страницам, пока пользователь не прервёт просмотр
    while current_page < total_pages:
        # Вычислить границы текущей страницы
        start_row = current_page * page_size
        end_row = min(start_row + page_size, total_rows)

        # Извлечь срез данных для текущей страницы
        selection = row_data[start_row:end_row]

        # Вывести таблицу с данными текущей страницы
        print(tabulate(
            selection,
            headers=headers,
            tablefmt="rounded_grid"
        ))

        # Запросить у пользователя действие: продолжить или выйти
        user_choice = input(
            f"\nPage {current_page + 1} of {total_pages}." +
            f"Rows {end_row} of {total_rows}. \n" +
            f"Press \033[1m\033[92menter\033[0m to continue (\033[1m\033[92mq\033[0m to skip\\exit): "
        )

        # Прервать вывод, если пользователь ввёл 'q'
        if user_choice == "q":
            break

        current_page += 1