#!/bin/bash
#
# Скрипт для монтирования NFS шары
# Использование: ./mount-nfs.sh [NFS_SERVER:/path] [MOUNT_POINT]
#
# Пример: ./mount-nfs.sh 172.20.129.1:/backups /mnt/veeam_nfs

set -e

# Параметры по умолчанию
NFS_SERVER_PATH="${1:-172.20.129.1:/backups}"
MOUNT_POINT="${2:-/mnt/veeam_nfs}"
NFS_OPTIONS="${NFS_OPTIONS:-vers=4.1,soft,timeo=30,retrans=3,noatime}"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    log_error "Этот скрипт должен запускаться с правами root (используйте sudo)"
    exit 1
fi

# Проверка существования NFS клиента
if ! command -v mount.nfs &> /dev/null; then
    log_error "NFS клиент не установлен. Установите: sudo apt-get install nfs-common"
    exit 1
fi

# Создание точки монтирования
if [ ! -d "$MOUNT_POINT" ]; then
    log_info "Создание точки монтирования: $MOUNT_POINT"
    mkdir -p "$MOUNT_POINT"
    chmod 755 "$MOUNT_POINT"
fi

# Проверка, уже ли смонтирована NFS
if mountpoint -q "$MOUNT_POINT"; then
    log_warn "NFS уже смонтирована в $MOUNT_POINT"
    
    # Проверка доступности
    if [ -r "$MOUNT_POINT" ]; then
        log_info "NFS доступна для чтения"
        exit 0
    else
        log_warn "NFS смонтирована, но недоступна. Пытаемся перемонтировать..."
        umount -f "$MOUNT_POINT" || true
    fi
fi

# Монтирование NFS
log_info "Монтирование NFS: $NFS_SERVER_PATH -> $MOUNT_POINT"
log_info "Опции монтирования: $NFS_OPTIONS"

if mount -t nfs -o "$NFS_OPTIONS" "$NFS_SERVER_PATH" "$MOUNT_POINT"; then
    log_info "✅ NFS успешно смонтирована"
    
    # Проверка доступности
    if [ -r "$MOUNT_POINT" ]; then
        log_info "✅ NFS доступна для чтения"
        
        # Показываем информацию о монтировании
        echo ""
        log_info "Информация о монтировании:"
        mount | grep "$MOUNT_POINT"
        echo ""
        log_info "Свободное место:"
        df -h "$MOUNT_POINT"
    else
        log_error "NFS смонтирована, но недоступна для чтения"
        exit 1
    fi
else
    log_error "❌ Ошибка монтирования NFS"
    exit 1
fi




