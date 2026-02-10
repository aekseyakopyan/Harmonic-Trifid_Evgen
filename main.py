import argparse
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).parent))

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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
