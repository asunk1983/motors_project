#!/bin/bash
# push-deploy.sh — пуш локальных изменений + деплой на сервере одной командой.
# Запускать из корня репозитория в Git Bash (VS Code терминал).
#
# Использование: ./push-deploy.sh

set -e

SERVER_USER="kipia"
SERVER_HOST="192.168.1.140"
SERVER_PROJECT_DIR="/home/kipia/motors_project"

echo "=== git push (production) ==="
git push production main

echo ""
echo "=== Деплой на сервере ($SERVER_HOST) ==="
ssh -t "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PROJECT_DIR && ./deploy.sh"
