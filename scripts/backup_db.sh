#!/bin/bash

BACKUP_DIR="/Users/set/.gemini/antigravity/playground/Evgeniy/backups"
DB_PATH="/Users/set/.gemini/antigravity/playground/Evgeniy/data/db/vacancies.db"
DATE=$(date +%Y-%m-%d_%H-%M)

mkdir -p "$BACKUP_DIR"

# Проверка существования БД
if [ ! -f "$DB_PATH" ]; then
    echo "❌ База данных не найдена: $DB_PATH"
    exit 1
fi

# Копирование БД
echo "📦 Создание бэкапа..."
cp "$DB_PATH" "$BACKUP_DIR/vacancies_$DATE.db"

# Сжатие
gzip "$BACKUP_DIR/vacancies_$DATE.db"

# Удаление бэкапов старше 30 дней
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "✅ Backup создан: vacancies_$DATE.db.gz"
echo "📊 Размер: $(du -h "$BACKUP_DIR/vacancies_$DATE.db.gz" | cut -f1)"
echo "📁 Всего бэкапов: $(ls -1 "$BACKUP_DIR"/*.gz 2>/dev/null | wc -l)"
