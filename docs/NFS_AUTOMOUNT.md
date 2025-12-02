# Автоматическое монтирование NFS шары

Этот документ описывает различные способы автоматизации монтирования NFS шары для приложения S3 Backup Manager.

## Обзор

Приложение использует NFS шару по пути `/mnt/veeam_nfs` для чтения файлов бэкапов. Для обеспечения надежной работы необходимо настроить автоматическое монтирование NFS.

## Варианты решения

### 1. Systemd Mount Unit (Рекомендуется) ⭐

**Преимущества:**
- Автоматическое монтирование при загрузке системы
- Автоматическое перемонтирование при сбоях сети
- Управление через стандартные systemd команды
- Интеграция с системными зависимостями

**Установка:**

```bash
# 1. Установите NFS клиент (если не установлен)
sudo apt-get update
sudo apt-get install nfs-common

# 2. Используйте скрипт автоматической установки
sudo ./scripts/install-nfs-automount.sh

# Или вручную:
# 2.1. Создайте точку монтирования
sudo mkdir -p /mnt/veeam_nfs
sudo chmod 755 /mnt/veeam_nfs

# 2.2. Скопируйте systemd unit файл
sudo cp systemd/mnt-veeam_nfs.mount /etc/systemd/system/

# 2.3. Отредактируйте файл и укажите ваш NFS сервер
sudo nano /etc/systemd/system/mnt-veeam_nfs.mount
# Измените строку: What=YOUR_NFS_SERVER:/path

# 2.4. Включите и запустите
sudo systemctl daemon-reload
sudo systemctl enable mnt-veeam_nfs.mount
sudo systemctl start mnt-veeam_nfs.mount
```

**Управление:**

```bash
# Проверка статуса
sudo systemctl status mnt-veeam_nfs.mount

# Ручное монтирование
sudo systemctl start mnt-veeam_nfs.mount

# Размонтирование
sudo systemctl stop mnt-veeam_nfs.mount

# Просмотр логов
sudo journalctl -u mnt-veeam_nfs.mount -f
```

**Настройка NFS сервера:**

Отредактируйте файл `/etc/systemd/system/mnt-veeam_nfs.mount` и измените строку:
```
What=YOUR_NFS_SERVER:/path
```

Например:
```
What=172.20.129.1:/backups
```

### 2. Скрипт ручного монтирования

Для разовых операций или тестирования:

```bash
# Дайте права на выполнение
chmod +x scripts/mount-nfs.sh

# Использование
sudo ./scripts/mount-nfs.sh NFS_SERVER:/path /mnt/veeam_nfs

# Пример
sudo ./scripts/mount-nfs.sh 172.20.129.1:/backups /mnt/veeam_nfs
```

### 3. /etc/fstab (Альтернативный способ)

Можно добавить запись в `/etc/fstab`:

```bash
sudo nano /etc/fstab
```

Добавьте строку:
```
172.20.129.1:/backups  /mnt/veeam_nfs  nfs  vers=4.1,soft,timeo=30,retrans=3,noatime  0  0
```

Применение:
```bash
# Проверка синтаксиса
sudo mount -a

# Монтирование конкретной точки
sudo mount /mnt/veeam_nfs
```

**Недостатки:**
- Может блокировать загрузку системы, если NFS недоступен
- Менее гибкое управление, чем systemd

### 4. Systemd Automount (Ленивое монтирование)

Для монтирования только при обращении:

```bash
# 1. Установите mount unit (как в варианте 1)

# 2. Установите automount unit
sudo cp systemd/mnt-veeam_nfs.automount /etc/systemd/system/

# 3. Включите automount (НЕ mount!)
sudo systemctl daemon-reload
sudo systemctl enable mnt-veeam_nfs.automount
sudo systemctl start mnt-veeam_nfs.automount
```

**Преимущества:**
- NFS монтируется только при первом обращении
- Автоматическое размонтирование при неиспользовании
- Меньше нагрузки на сеть

### 5. Проверка в приложении

Приложение автоматически проверяет доступность NFS при старте. Можно добавить автоматическое монтирование через скрипт:

```python
# В run.py или app/web/app.py можно добавить:
from app.utils.nfs_mount import ensure_nfs_mounted

# При старте приложения
nfs_server = os.getenv('NFS_SERVER', '172.20.129.1:/backups')
mount_point = os.getenv('NFS_PATH', '/mnt/veeam_nfs')
auto_mount = os.getenv('AUTO_MOUNT_NFS', 'false').lower() == 'true'

if auto_mount:
    success, message = ensure_nfs_mounted(
        nfs_server=nfs_server,
        mount_point=mount_point,
        auto_mount=True
    )
    if not success:
        logger.warning(f"NFS недоступна: {message}")
```

**Примечание:** Для автоматического монтирования из приложения потребуются права root или настройка sudo без пароля.

## Настройка опций NFS

Рекомендуемые опции монтирования:

**Для стабильной сети:**
```
vers=4.1,hard,timeo=30,retrans=3,noatime
```

**Для нестабильной сети:**
```
vers=4.1,soft,timeo=30,retrans=3,noatime
```

**Опции:**
- `vers=4.1` - версия NFS протокола
- `soft` - не блокировать при недоступности NFS (предпочтительно для автономных систем)
- `hard` - ждать восстановления NFS (предпочтительно для критичных систем)
- `timeo=30` - таймаут в десятых долях секунды (3 секунды)
- `retrans=3` - количество попыток
- `noatime` - не обновлять время доступа (улучшает производительность)

## Диагностика проблем

### Проверка доступности NFS сервера

```bash
# Проверка подключения к NFS серверу
ping NFS_SERVER_IP

# Просмотр доступных NFS экспортов
showmount -e NFS_SERVER_IP

# Тестовое монтирование
sudo mount -t nfs -o vers=4.1 NFS_SERVER:/path /tmp/test_mount
```

### Проверка монтирования

```bash
# Список всех NFS монтирований
mount | grep nfs

# Статус systemd mount
sudo systemctl status mnt-veeam_nfs.mount

# Логи монтирования
sudo journalctl -u mnt-veeam_nfs.mount -n 50

# Проверка доступности точки монтирования
ls -la /mnt/veeam_nfs
```

### Частые проблемы

1. **"Connection refused"**
   - Проверьте доступность NFS сервера
   - Проверьте, запущен ли NFS сервис на сервере
   - Проверьте firewall правила

2. **"Permission denied"**
   - Проверьте права доступа на NFS сервере
   - Проверьте экспорты: `showmount -e SERVER`

3. **"Stale file handle"**
   - NFS соединение разорвано, нужно перемонтировать:
     ```bash
     sudo systemctl restart mnt-veeam_nfs.mount
     ```

## Docker окружение

Если приложение запускается в Docker, NFS должна быть смонтирована на хосте, а затем передана в контейнер через volume:

```yaml
# docker-compose.yml
volumes:
  - /mnt/veeam_nfs:/mnt/veeam_nfs:ro
```

Убедитесь, что NFS смонтирована на хосте перед запуском контейнера.

## Рекомендации

1. **Используйте systemd mount unit** - это наиболее надежный и стандартный способ
2. **Настройте мониторинг** - добавьте проверку доступности NFS в вашу систему мониторинга
3. **Используйте soft mount** - для автономных систем, чтобы избежать блокировок
4. **Настройте автоматическое перемонтирование** - systemd делает это автоматически
5. **Логируйте проблемы** - отслеживайте логи systemd для диагностики

## Переменные окружения

Для настройки через переменные окружения:

```bash
export NFS_SERVER="172.20.129.1:/backups"
export NFS_PATH="/mnt/veeam_nfs"
export AUTO_MOUNT_NFS="true"  # Включить автоматическое монтирование из приложения
```




