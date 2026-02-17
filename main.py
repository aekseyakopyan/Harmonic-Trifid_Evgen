import argparse
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в пути импорта
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config.settings import settings

def run_monitor():
    """Запуск единого мониторинга."""
    from apps.unified_monitor import monitor
    monitor()

def run_parser_today():
    """Запуск ежедневного парсера."""
    from apps.today_parser import main
    asyncio.run(main())

def run_parser_history():
    """Запуск исторического парсера."""
    from apps.history_parser import main
    asyncio.run(main())

def run_gwen():
    """Запуск Гвен (Коммандер/Уведомления)."""
    from systems.gwen.commander import main
    asyncio.run(main())

def run_celery_worker():
    """Запуск Celery worker через CLI."""
    import subprocess
    print("=== Starting Celery Worker ===")
    try:
        subprocess.run([
            "celery", "-A", "systems.parser.celery_config", 
            "worker", 
            "--loglevel=info", 
            "--concurrency=4", 
            "--queues=leads,notifications,maintenance"
        ])
    except KeyboardInterrupt:
        print("\nCelery worker stopped")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Управление системой Amigos Bot")
    subparsers = parser.add_subparsers(dest="command", help="Команды")

    # Command: monitor
    subparsers.add_parser("monitor", help="Запуск мониторинга в реальном времени")

    # Command: parse
    parse_parser = subparsers.add_parser("parse", help="Запуск парсинга")
    parse_parser.add_argument("type", choices=["today", "history"], help="Тип парсинга (сегодняшний или исторический)")

    # Command: gwen
    subparsers.add_parser("gwen", help="Запуск системы Gwen (Коммандер)")

    # Command: worker
    subparsers.add_parser("worker", help="Запуск Celery worker")

    args = parser.parse_args()

    if args.command == "monitor":
        run_monitor()
    elif args.command == "parse":
        if args.type == "today":
            run_parser_today()
        else:
            run_parser_history()
    elif args.command == "gwen":
        run_gwen()
    elif args.command == "worker":
        run_celery_worker()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
