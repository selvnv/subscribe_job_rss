# ==================== Этап 1: Сборка ====================
# Полный python-образ со всеми утилитами, необходимыми для сборки проекта
FROM python:3.12 AS build

# Установить пакетный менеджер uv
RUN pip install --no-cache-dir uv

# Рабочая директория для сборки
WORKDIR /build

# Копировать только файлы зависимостей (оптимизация кэширования слоев)
COPY pyproject.toml uv.lock ./

# Установить зависимости проекта
#   --frozen              : использовать зафиксированные версии из uv.lock
#   --no-dev              : установить только production-зависимости
#   --no-install-project  : не устанавливать проект (пакет из исходников)
RUN uv sync --frozen --no-dev --no-install-project

# Копировать исходники проекта
COPY modules/ ./modules/

# Установить сам проект — создать entry-point "subjob" в .venv/bin/
#   --no-deps             : не устанавливать повторно зависимости (установлены ранее)
RUN uv pip install --no-deps .


# ==================== Этап 2: Рантайм ====================
# slim-образ: урезанная версия Python (~50 MB вместо ~1 GB у полного образа)
FROM python:3.12-slim AS runtime

# Создать непривилегированного пользователя для запуска приложения
#   --uid 1000       : фиксированный UID для корректной настройки прав на смонтированные volume
RUN useradd --no-create-home --uid 1000 subjob

WORKDIR /app

# Копировать установленные пакеты из этапа сборки build
# /build/.venv/lib/python3.12/site-packages : путь к зависимостям, установленным uv
# /usr/local/lib/python3.12/site-packages   : путь к пакетам пользователя системы
COPY --from=build /build/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Копировать entry-point скрипт "subjob", предоставляющий доступ к приложению из cli
# /build/.venv/bin/subjob : путь, по которому uv разместил скрипт
# /usr/local/bin/subjob   : путь к исполняемому скрипту в контейнере
# /usr/local/bin уже в $PATH, скрипт доступен глобально
COPY --from=build /build/.venv/bin/subjob /usr/local/bin/subjob
# Заменить путь к интерпретатору python в скрипте
RUN sed -i 's|#!/build/.venv/bin/python3|#!/usr/local/bin/python|' /usr/local/bin/subjob

# Копировать шаблоны сообщений для бота
COPY templates/ ./templates/

# Создать директории для данных и логов
RUN mkdir -p /app/data /app/logs && chown -R subjob:subjob /app

# Переключиться на непривилегированного пользователя для запуска приложения
USER subjob

# Команда по умолчанию — запуск Telegram-бота.
CMD ["subjob", "runbot"]

