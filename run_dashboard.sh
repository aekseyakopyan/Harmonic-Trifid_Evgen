#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Запуск Telegram Web App Dashboard (Без Юзербота)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Активация виртуального окружения
if [ -d "venv" ]; then
    source venv/bin/activate
fi
export PYTHONPATH=".:${PYTHONPATH}"

# Освобождение порта 8000
if lsof -t -i:8000 >/dev/null; then
    echo -e "${YELLOW}⚠️ Порт 8000 занят. Освобождаем...${NC}"
    lsof -t -i:8000 | xargs kill -9
fi

echo -e "${GREEN}🚀 Запуск FastAPI сервера...${NC}"
python3 systems/dashboard/main.py > logs/dashboard.log 2>&1 &
DASH_PID=$!

echo -e "${YELLOW}⏳ Ожидание запуска (5 сек)...${NC}"
sleep 5

if kill -0 $DASH_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Дашборд успешно запущен!${NC}"
    echo ""
    echo -e "${BLUE}📊 TWA Interface:${NC} http://localhost:8000/twa"
    echo -e "${BLUE}🔗 API Base:${NC}      http://localhost:8000/api"
    echo ""
    echo -e "${YELLOW}Нажмите Ctrl+C для остановки${NC}"
    wait $DASH_PID
else
    echo -e "${RED}✗ Ошибка запуска! Проверьте logs/dashboard.log${NC}"
    cat logs/dashboard.log
fi
