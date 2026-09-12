#!/bin/bash
# rollback-remote.sh — запускает диалог отката на сервере одной командой с Windows.
# Запускать из корня репозитория в Git Bash / bash push-deploy.sh стиле.
#
# Использование: bash rollback-remote.sh

SERVER_USER="kipia"
SERVER_HOST="192.168.1.140"
SERVER_PROJECT_DIR="/home/kipia/motors_project"

ssh -t "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PROJECT_DIR && ./rollback.sh"
