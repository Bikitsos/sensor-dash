#!/bin/bash

# Sensor Dashboard Podman Management Script

set -e

PROJECT_NAME="sensor-dash"
CONTAINER_NAME="sensor-dashboard"

show_help() {
    echo "Sensor Dashboard Podman Management"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build the container image"
    echo "  start       Start the dashboard"
    echo "  stop        Stop the dashboard"
    echo "  restart     Restart the dashboard"
    echo "  logs        Show container logs"
    echo "  status      Show container status"
    echo "  shell       Open shell in running container"
    echo "  clean       Remove container and image"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build && $0 start    # Build and start"
    echo "  $0 logs -f              # Follow logs"
    echo "  $0 restart              # Restart the service"
}

build_image() {
    echo "Building sensor dashboard image..."
    podman build -t ${PROJECT_NAME}:latest .
    echo "✅ Build complete!"
}

start_container() {
    if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "Container ${CONTAINER_NAME} already exists. Starting..."
        podman start ${CONTAINER_NAME}
    else
        echo "Creating and starting new container..."
        podman run -d \
            --name ${CONTAINER_NAME} \
            --env-file .env \
            -p 8081:8081 \
            --restart unless-stopped \
            ${PROJECT_NAME}:latest
    fi
    echo "✅ Sensor dashboard started!"
    echo "🌐 Access at: http://localhost:8081"
    echo "🔑 Login: admin / sensor123"
}

stop_container() {
    echo "Stopping sensor dashboard..."
    podman stop ${CONTAINER_NAME} 2>/dev/null || echo "Container not running"
    echo "✅ Dashboard stopped!"
}

restart_container() {
    stop_container
    sleep 2
    start_container
}

show_logs() {
    podman logs ${CONTAINER_NAME} "$@"
}

show_status() {
    echo "=== Container Status ==="
    if podman ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q ${CONTAINER_NAME}; then
        podman ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAMES|${CONTAINER_NAME})"
    else
        echo "Container ${CONTAINER_NAME} not found"
    fi
    
    echo ""
    echo "=== Image Status ==="
    if podman images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.Created}}" | grep -q ${PROJECT_NAME}; then
        podman images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.Created}}" | grep -E "(REPOSITORY|${PROJECT_NAME})"
    else
        echo "Image ${PROJECT_NAME} not found"
    fi
}

open_shell() {
    echo "Opening shell in container..."
    podman exec -it ${CONTAINER_NAME} /bin/bash
}

clean_up() {
    echo "Cleaning up containers and images..."
    podman stop ${CONTAINER_NAME} 2>/dev/null || true
    podman rm ${CONTAINER_NAME} 2>/dev/null || true
    podman rmi ${PROJECT_NAME}:latest 2>/dev/null || true
    echo "✅ Cleanup complete!"
}

# Main script logic
case "${1:-help}" in
    build)
        build_image
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    status)
        show_status
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_up
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac