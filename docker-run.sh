#!/bin/bash

# Скрипт для управления Telegram-ботом через Docker
# Использование: ./docker-run.sh [команда]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверяем наличие Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
        exit 1
    fi
}

# Проверяем наличие .env файла
check_env() {
    if [ ! -f ".env" ]; then
        print_warning "Файл .env не найден. Создаем из примера..."
        if [ -f "env.example" ]; then
            cp env.example .env
            print_info "Файл .env создан. Отредактируйте его и добавьте BOT_TOKEN и ADMIN_ID"
        else
            print_error "Файл env.example не найден. Создайте .env файл вручную."
        fi
        exit 1
    fi
}

# Создаем необходимые директории
create_directories() {
    print_info "Создание необходимых директорий..."
    mkdir -p bot/data
    mkdir -p logs
    print_success "Директории созданы"
}

# Сборка образа
build() {
    print_info "Сборка Docker образа..."
    docker-compose build
    print_success "Образ собран успешно"
}

# Запуск бота
start() {
    print_info "Запуск Telegram-бота..."
    docker-compose up -d
    print_success "Бот запущен в фоновом режиме"
    print_info "Используйте 'docker-compose logs -f' для просмотра логов"
}

# Остановка бота
stop() {
    print_info "Остановка Telegram-бота..."
    docker-compose down
    print_success "Бот остановлен"
}

# Перезапуск бота
restart() {
    print_info "Перезапуск Telegram-бота..."
    docker-compose restart
    print_success "Бот перезапущен"
}

# Просмотр логов
logs() {
    print_info "Просмотр логов бота..."
    docker-compose logs -f
}

# Просмотр статуса
status() {
    print_info "Статус контейнеров:"
    docker-compose ps
}

# Очистка
clean() {
    print_warning "Остановка и удаление контейнеров..."
    docker-compose down
    print_info "Удаление образов..."
    docker-compose down --rmi all
    print_success "Очистка завершена"
}

# Обновление
update() {
    print_info "Обновление бота..."
    docker-compose pull
    docker-compose build --no-cache
    docker-compose up -d
    print_success "Бот обновлен и перезапущен"
}

# Вход в контейнер
shell() {
    print_info "Вход в контейнер бота..."
    docker-compose exec telegram-bot /bin/bash
}

# Показать справку
help() {
    echo "🐳 Управление Telegram-ботом через Docker"
    echo ""
    echo "Использование: $0 [команда]"
    echo ""
    echo "Команды:"
    echo "  build     - Собрать Docker образ"
    echo "  start     - Запустить бота"
    echo "  stop      - Остановить бота"
    echo "  restart   - Перезапустить бота"
    echo "  logs      - Просмотр логов"
    echo "  status    - Статус контейнеров"
    echo "  shell     - Войти в контейнер"
    echo "  update    - Обновить и перезапустить"
    echo "  clean     - Остановить и удалить все"
    echo "  help      - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 build && $0 start    # Собрать и запустить"
    echo "  $0 logs                 # Просмотр логов"
    echo "  $0 restart              # Перезапуск"
}

# Основная логика
main() {
    check_docker
    create_directories
    
    case "${1:-help}" in
        build)
            check_env
            build
            ;;
        start)
            check_env
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        logs)
            logs
            ;;
        status)
            status
            ;;
        shell)
            shell
            ;;
        update)
            check_env
            update
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            help
            ;;
        *)
            print_error "Неизвестная команда: $1"
            help
            exit 1
            ;;
    esac
}

# Запуск основной функции
main "$@"
