#!/bin/bash
#
# Скрипт установки автоматического монтирования NFS
# Этот скрипт устанавливает systemd unit для автоматического монтирования NFS
#

set -e

# Конфигурация
NFS_SERVER="${NFS_SERVER:-172.20.129.1:/backups}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/veeam_nfs}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    log_error "Этот скрипт должен запускаться с правами root"
    echo "Использование: sudo $0"
    exit 1
fi

log_info "Установка автоматического монтирования NFS"
log_info "NFS сервер: $NFS_SERVER"
log_info "Точка монтирования: $MOUNT_POINT"

# 1. Установка NFS клиента
log_info "Проверка установки NFS клиента..."
if ! command -v mount.nfs &> /dev/null; then
    log_info "Установка nfs-common..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y nfs-common
    elif command -v yum &> /dev/null; then
        yum install -y nfs-utils
    else
        log_error "Не удалось определить пакетный менеджер"
        exit 1
    fi
else
    log_info "NFS клиент уже установлен"
fi

# 2. Создание точки монтирования
log_info "Создание точки монтирования: $MOUNT_POINT"
mkdir -p "$MOUNT_POINT"
chmod 755 "$MOUNT_POINT"

# 3. Копирование systemd unit файла
log_info "Настройка systemd mount unit..."

MOUNT_UNIT_FILE="$PROJECT_DIR/systemd/mnt-veeam_nfs.mount"
SYSTEMD_MOUNT_PATH="/etc/systemd/system/mnt-veeam_nfs.mount"

# Обновление NFS сервера в unit файле
sed "s|What=.*|What=$NFS_SERVER|" "$MOUNT_UNIT_FILE" > /tmp/mnt-veeam_nfs.mount

# Копирование в systemd
cp /tmp/mnt-veeam_nfs.mount "$SYSTEMD_MOUNT_PATH"
chmod 644 "$SYSTEMD_MOUNT_PATH"

log_info "✅ Systemd mount unit установлен: $SYSTEMD_MOUNT_PATH"

# 4. Включение и запуск службы
log_info "Включение автоматического монтирования..."
systemctl daemon-reload
systemctl enable mnt-veeam_nfs.mount
systemctl start mnt-veeam_nfs.mount

# Проверка статуса
sleep 2
if systemctl is-active --quiet mnt-veeam_nfs.mount; then
    log_info "✅ NFS успешно смонтирована автоматически"
    mount | grep "$MOUNT_POINT"
else
    log_warn "NFS не смонтирована автоматически. Проверьте статус:"
    echo "  systemctl status mnt-veeam_nfs.mount"
    echo "  journalctl -u mnt-veeam_nfs.mount -n 50"
fi

log_info ""
log_info "Для управления монтированием используйте:"
log_info "  systemctl status mnt-veeam_nfs.mount  # Статус"
log_info "  systemctl start mnt-veeam_nfs.mount   # Монтировать"
log_info "  systemctl stop mnt-veeam_nfs.mount    # Размонтировать"
log_info "  systemctl restart mnt-veeam_nfs.mount # Перемонтировать"




