from math import ceil
from tabulate import tabulate


def print_table_paged(row_data,
                         headers: list,
                         page_size: int = 8):
    if not row_data:
        print(f"\033[1m\033[94m[INFO] >>>>\033[0m No data to display")
        return

    total_rows = len(row_data)
    total_pages = ceil(total_rows / page_size)

    current_page = 0

    while current_page < total_pages:
        start_row = current_page * page_size
        end_row = min(start_row + page_size, total_rows)

        selection = row_data[start_row:end_row]

        print(tabulate(
            selection,
            headers=headers,
            tablefmt="rounded_grid"
        ))

        user_choice = input(
            f"\nPage {current_page + 1} of {total_pages}." +
            f"Rows {end_row} of {total_rows}. \n" +
            f"Press \033[1m\033[92menter\033[0m to continue (\033[1m\033[92mq\033[0m to skip\\exit): "
        )

        if user_choice == "q":
            break

        current_page += 1