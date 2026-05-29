#!/bin/bash

# Прекращать выполнение скрипта при любой ошибке (ненулевой код возврата любой команды)
set -e

APPLICATION_USERNAME=subjob
# Без / в конце
APPLICATION_CATALOG=/opt/subjob


# Цвета для вывода
RED_COLOR='\033[0;91m'
GREEN_COLOR='\033[0;92m'
YELLOW_COLOR='\033[0;93m'
BLUE_COLOR='\033[0;94m'
RESET_COLOR='\033[0m'

# Проверить наличие прав для выполнения команд скрипта
# Если их недостаточно, скрипт не выполнится
if [ "$(id -u)" -ne 0 ]; then
  echo -e "${RED_COLOR}To execute the script, run it with sudo${RESET_COLOR}"
  exit 1
fi


echo -e "${BLUE_COLOR}Install Docker...${RESET_COLOR}"
# 1. Установка Docker

echo -e "\n${GREEN_COLOR}Docker install successful${RESET_COLOR}"


echo -e "\n${BLUE_COLOR}Create application user ${APPLICATION_USERNAME}...${RESET_COLOR}"
# Проверка существования пользователя (вывод подавляется)
if id "${APPLICATION_USERNAME}" &>/dev/null; then
  echo -e "\n${GREEN_COLOR}User ${APPLICATION_USERNAME} already exists${RESET_COLOR}"
else
  # Создание системного пользователя (не предназначен для входа в систему по паролю)
  # Под этим пользователем не получится выполнить команды, требующие авторизации
  sudo useradd --system --no-create-home --shell /usr/sbin/nologin ${APPLICATION_USERNAME}
  sudo usermod -aG docker ${APPLICATION_USERNAME}
  echo -e "\n${GREEN_COLOR}User ${APPLICATION_USERNAME} create successful${RESET_COLOR}"
fi
echo -e "\n${BLUE_COLOR}User info: $(id ${APPLICATION_USERNAME})${RESET_COLOR}"


# Создание рабочего каталога для проекта и файла с переменными окружения
echo -e "\n${BLUE_COLOR}Create project catalog ${APPLICATION_CATALOG}...${RESET_COLOR}"
sudo mkdir -p ${APPLICATION_CATALOG}
sudo chown -R ${APPLICATION_USERNAME}:${APPLICATION_USERNAME} ${APPLICATION_CATALOG}

read -s -p "Enter telegram API token: " telegram_api_token
if [ -z "$telegram_api_token" ]; then
  echo -e "\n${YELLOW_COLOR}You enter empty Telegram API token...${RESET_COLOR}"
fi

# Создать файл /opt/subjob/.env от имени пользователя в APPLICATION_USERNAME
# и перенаправить в него текст (структуру файла окружения), вывод скрыть
sudo -u ${APPLICATION_USERNAME} tee ${APPLICATION_CATALOG}/.env >/dev/null << EOF
TELEGRAM_API_TOKEN=$telegram_api_token
RSS_CHECK_INTERVAL_SECONDS=3600
VACANCIES_PARSE_LIMIT=3
EOF
echo -e "\n${GREEN_COLOR}Catalog ${APPLICATION_CATALOG} create successful${RESET_COLOR}"
echo -e "${GREEN_COLOR}Env file create successful${RESET_COLOR}"


# Создать ключ для подключения по
# 4. SSH-ключ (сделать копипасту ключа параметром)
# 5. Файрвол

echo -e "\n${GREEN_COLOR}Server is ready for deployment\nNext: configure Github Secrets (more info in README.md)${RESET_COLOR}"