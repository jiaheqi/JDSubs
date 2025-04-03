#!/bin/bash

function start_supervisor() {
    supervisord -c supervisor.conf
    echo "Supervisor已启动"
}

function stop_supervisor() {
    supervisorctl -c supervisor.conf shutdown
    echo "Supervisor已停止"
}

function restart_service() {
    supervisorctl -c supervisor.conf restart weather_monitor
    echo "天气监控服务已重启"
}

function check_status() {
    supervisorctl -c supervisor.conf status
}

function show_logs() {
    tail -f weather_supervisor.log
}

case "$1" in
    start)
        start_supervisor
        ;;
    stop)
        stop_supervisor
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

exit 0