#!/bin/bash

# Прекращать выполнение скрипта при любой ошибке (ненулевой код возврата любой команды)
set -e

APPLICATION_USERNAME=subjob
# Без / в конце
APPLICATION_CATALOG=/opt/subjob
SSH_CATALOG=/home/${APPLICATION_USERNAME}/.ssh
SSH_AUTH_KEYS_PATH=${SSH_CATALOG}/authorized_keys

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


echo -e "${BLUE_COLOR}==================Install Docker==================${RESET_COLOR}"
# 1. Установка Docker
if docker info &>/dev/null; then
  echo -e "${GREEN_COLOR}Docker already installed${RESET_COLOR}"
  docker --version
else
  echo -e "${BLUE_COLOR}Install docker${RESET_COLOR}"
  sudo apt update
  sudo apt install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  sudo tee /etc/apt/sources.list.d/docker.sources << EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  sudo apt update

  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
echo -e "\n${GREEN_COLOR}Docker installation successful${RESET_COLOR}"


echo -e "\n${BLUE_COLOR}==================Install Git==================${RESET_COLOR}"
if ! command -v git &>/dev/null; then
    echo -e "\n${GREEN_COLOR}Git not found. Installing Git...${RESET_COLOR}"
    sudo apt update
    sudo apt install -y git
else
    echo -e "\n${GREEN_COLOR}Git is already installed${RESET_COLOR}"
    git --version
fi
echo -e "\n${GREEN_COLOR}Git installation successful${RESET_COLOR}"


echo -e "\n${BLUE_COLOR}==================Create application user ${APPLICATION_USERNAME}==================${RESET_COLOR}"
# Проверка существования пользователя (вывод подавляется)
if id "${APPLICATION_USERNAME}" &>/dev/null; then
  echo -e "\n${GREEN_COLOR}User ${APPLICATION_USERNAME} already exists${RESET_COLOR}"
else
  # Создание системного пользователя (не предназначен для входа в систему по паролю)
  sudo useradd --system --no-create-home --shell /bin/bash ${APPLICATION_USERNAME}
  sudo usermod -aG docker ${APPLICATION_USERNAME}
  echo -e "\n${GREEN_COLOR}User ${APPLICATION_USERNAME} create successful${RESET_COLOR}"
fi
echo -e "\n${BLUE_COLOR}User info: $(id ${APPLICATION_USERNAME})${RESET_COLOR}"


# Создание рабочего каталога для проекта и файла с переменными окружения
echo -e "\n${BLUE_COLOR}==================Initialize project catalog ${APPLICATION_CATALOG}==================${RESET_COLOR}"
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


# Задать публичный ключ (пару к приватному ключу, который будет использовать раннер для подключения к серверу)
echo -e "\n${BLUE_COLOR}==================Add public key for git runner authorization==================${RESET_COLOR}"
mkdir -p ${SSH_CATALOG}
read -r -p "Enter public ssh key pair for Git: " public_ssh_git_key
if [ -z "$public_ssh_git_key" ]; then
  echo -e "\n${YELLOW_COLOR}You enter empty public ssh key pair for Git...${RESET_COLOR}"
elif [ -e ${SSH_AUTH_KEYS_PATH} ] ; then
  if ! grep -qF "$public_ssh_git_key" ${SSH_AUTH_KEYS_PATH}; then
    # Если файл существует и не содержит введенный ключ, дополнить новой записью
    echo "$public_ssh_git_key" | sudo tee -a "$SSH_AUTH_KEYS_PATH" > /dev/null
    echo -e "${GREEN_COLOR}Append SSH key appended to ${SSH_AUTH_KEYS_PATH}${RESET_COLOR}"
  else
    echo -e "${GREEN_COLOR}Public SSH key is already in ${SSH_AUTH_KEYS_PATH}${RESET_COLOR}"
  fi
else
  # Если файл не существует, создать
  echo "$public_ssh_git_key" | sudo tee "$SSH_AUTH_KEYS_PATH" > /dev/null
fi

sudo chmod 700 ${SSH_CATALOG}
sudo chmod 600 ${SSH_AUTH_KEYS_PATH}
sudo chown -R ${APPLICATION_USERNAME}:${APPLICATION_USERNAME} ${SSH_CATALOG}

echo -e "\n${GREEN_COLOR}Server is ready for deployment\nNext: configure Github Secrets (more info in README.md)${RESET_COLOR}"