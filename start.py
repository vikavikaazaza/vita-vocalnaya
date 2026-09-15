import subprocess
import sys
import signal
import time

processes = []


def stop_all(*_):
    print("Останавливаем процессы...")

    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    sys.exit(0)


signal.signal(signal.SIGTERM, stop_all)
signal.signal(signal.SIGINT, stop_all)


print("Запускаем dashboard.py...")
dashboard = subprocess.Popen(
    [sys.executable, "dashboard.py"]
)
processes.append(dashboard)


print("Запускаем bot.py...")
bot = subprocess.Popen(
    [sys.executable, "bot.py"]
)
processes.append(bot)


print("Dashboard и Telegram-бот запущены.")


while True:
    time.sleep(5)

    # Если один процесс неожиданно завершился,
    # останавливаем второй, чтобы BotHost перезапустил проект целиком.
    for process in processes:
        if process.poll() is not None:
            print("Один из процессов завершился. Перезапускаем проект...")
            stop_all()