#!/usr/bin/env python3
"""
Скрипт для создания полного резервного кода (Backup) системы.
Сохраняет:
1. Базы данных (vacancies.db, bot_data.db)
2. Конфигурацию (.env)
3. Исходный код (systems, core, scripts, apps)
4. Документацию (docs)

Результат сохраняется в директорию backups/YYYY-MM-DD_HH-MM-SS.
"""

import os
import sys
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, os.getcwd())
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)

def create_backup():
    # 1. Определяем директории
    project_root = Path(os.getcwd())
    backup_root = project_root / "backups"
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = backup_root / timestamp
    
    # Создаем директорию для бэкапа
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📦 Starting backup to: {backup_dir}")
    logger.info("backup_started", path=str(backup_dir))
    
    try:
        # 2. Бэкап баз данных (копируем файлы)
        print("💾 Backing up databases...")
        db_files = ["vacancies.db", "bot_data.db"]
        
        for db_file in db_files:
            src = project_root / db_file
            if src.exists():
                shutil.copy2(src, backup_dir / db_file)
                print(f"   ✅ Copied {db_file}")
            else:
                print(f"   ⚠️ File {db_file} not found, skipping")

        # 3. Бэкап конфигурации
        print("⚙️ Backing up configuration...")
        config_files = [".env", "requirements.txt"]
        for conf in config_files:
            src = project_root / conf
            if src.exists():
                shutil.copy2(src, backup_dir / conf)
                print(f"   ✅ Copied {conf}")
        
        # 4. Бэкап исходного кода (архивируем)
        print("📚 Archiving source code...")
        source_dirs = ["systems", "core", "scripts", "apps", "docs"]
        archive_name = backup_dir / "source_code.tar.gz"
        
        with tarfile.open(archive_name, "w:gz") as tar:
            for source_dir in source_dirs:
                src_path = project_root / source_dir
                if src_path.exists():
                    tar.add(src_path, arcname=source_dir)
                    print(f"   ✅ Archived {source_dir}")
                else:
                    print(f"   ⚠️ Directory {source_dir} not found")
        
        # 5. Создаем манифест
        with open(backup_dir / "manifest.txt", "w") as f:
            f.write(f"Backup created at: {datetime.now().isoformat()}\n")
            f.write(f"Contains:\n")
            f.write(f"- Databases: {', '.join(db_files)}\n")
            f.write(f"- Source code archive: source_code.tar.gz\n")
            f.write(f"- Config files: {', '.join(config_files)}\n")
            
        print(f"\n✅ Backup completed successfully!")
        print(f"📂 Path: {backup_dir}")
        logger.info("backup_completed", path=str(backup_dir))
        
    except Exception as e:
        print(f"\n❌ Backup failed: {e}")
        logger.error("backup_failed", error=str(e))
        # Очистка при ошибке (опционально, пока оставляем)

if __name__ == "__main__":
    create_backup()
