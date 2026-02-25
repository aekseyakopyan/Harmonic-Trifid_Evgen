#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Переходим в директорию скрипта
cd "$(dirname "$0")"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Запуск Telegram AI Request Processor${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Виртуальное окружение не найдено!${NC}"
    echo -e "${YELLOW}Создайте его командой: python3 -m venv venv${NC}"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo -e "${YELLOW}Скопируйте .env.example в .env и заполните настройки${NC}"
    exit 1
fi

# Активация виртуального окружения
source venv/bin/activate
export PYTHONPATH=".:${PYTHONPATH}"

# Массив для хранения PID процессов
PIDS=()

# Функция для завершения всех процессов
cleanup() {
    echo -e "\n${YELLOW}Остановка всех процессов...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
        fi
    done
    echo -e "${GREEN}✓ Все процессы остановлены${NC}"
    exit 0
}

# Обработка Ctrl+C
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${GREEN}🚀 Запуск компонентов...${NC}"
echo ""

# Убеждаемся, что директория логов существует
mkdir -p logs

# Освобождение порта 8000 если занят (graceful → force)
if lsof -i:8000 -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Порт 8000 занят. Освобождаем...${NC}"
    kill -15 $(lsof -i:8000 -t) 2>/dev/null || true
    sleep 2
    if lsof -i:8000 -t >/dev/null 2>&1; then
        kill -9 $(lsof -i:8000 -t) 2>/dev/null || true
    fi
fi

# Запуск бота
echo -e "${BLUE}[1/2]${NC} Запуск Алексея (Userbot)..."
# Очистим лог перед запуском, чтобы не читать старые записи
> logs/alexey.log
python3 -m systems.alexey.main > logs/alexey.log 2>&1 &
BOT_PID=$!
PIDS+=($BOT_PID)

echo -e "${YELLOW}⏳ Ожидание полной инициализации Алексея...${NC}"

# Ожидание готовности (максимум 30 секунд)
MAX_RETRIES=30
COUNT=0
ALEXEY_READY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    if grep -q "Userbot is running" logs/alexey.log; then
        ALEXEY_READY=true
        break
    fi
    
    # Проверка, не упал ли процесс
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo -e "${RED}❌ Процесс Алексея завершился неожиданно!${NC}"
        tail -n 20 logs/alexey.log
        cleanup
    fi
    
    sleep 1
    COUNT=$((COUNT+1))
done

if [ "$ALEXEY_READY" = true ]; then
    echo -e "${GREEN}  ✓ Алексей успешно запущен и готов к работе (PID: $BOT_PID)${NC}"
else
    echo -e "${RED}  ✗ Тайм-аут ожидания запуска Алексея${NC}"
    tail -n 20 logs/alexey.log
    cleanup
fi

# Запуск веб-дашборда (только после успешного старта Алексея)
echo -e "${BLUE}[2/2]${NC} Запуск Дашборда..."
python3 systems/dashboard/main.py > logs/dashboard.log 2>&1 &
WEB_PID=$!
PIDS+=($WEB_PID)
sleep 2

if kill -0 $WEB_PID 2>/dev/null; then
    echo -e "${GREEN}  ✓ Дашборд запущен (PID: $WEB_PID)${NC}"
else
    echo -e "${RED}  ✗ Ошибка запуска Дашборда${NC}"
    tail -n 20 logs/dashboard.log
    cleanup
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Все системы запущены успешно!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📊 Веб-интерфейс:${NC} http://localhost:8000"
echo -e "${BLUE}📱 Telegram App:${NC}  http://localhost:8000/twa"
echo -e "${BLUE}📝 Логи Алексея:${NC}     tail -f logs/alexey.log"
echo -e "${BLUE}📝 Логи Дашборда:${NC}    tail -f logs/dashboard.log"
echo ""
echo -e "${YELLOW}Нажмите Ctrl+C для остановки всех процессов${NC}"
echo ""

# Ожидание завершения
wait
