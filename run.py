import os
import sys
from dotenv import load_dotenv
load_dotenv()

DEPLOYMENT = os.getenv("DEPLOYMENT", "prod")


if DEPLOYMENT == "dev":
    print("\n🟡 PyNext running in DEV mode (Hot Reload Enabled)\n")

    import time
    import subprocess
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    WATCH_DIRS = ["pages", "core.py", "server_runner.py"]


    class ReloadHandler(FileSystemEventHandler):

        def __init__(self, restart):
            self.restart = restart

        def on_any_event(self, event):

            if event.is_directory:
                return

            filename = os.path.basename(event.src_path)

            if filename.startswith(".entry"):
                return

            if filename.startswith("__pycache__"):
                return

            if filename.endswith((".pyc", ".log")):
                return

            if event.src_path.endswith(
                (".tsx", ".jsx", ".py", ".js", ".json")
            ):
                print(f"\n🔄 File changed: {event.src_path}")
                self.restart()


    def start_server():
        return subprocess.Popen(
            [sys.executable, "server_runner.py"]
        )


    def main():

        process = start_server()

        def restart():

            nonlocal process

            print("♻️ Restarting server...")

            process.terminate()
            process.wait()

            process = start_server()

            print("✅ Server restarted")

        event_handler = ReloadHandler(restart)
        observer = Observer()

        for path in WATCH_DIRS:
            if os.path.exists(path):
                observer.schedule(
                    event_handler,
                    path,
                    recursive=True
                )

        observer.start()

        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:

            observer.stop()
            process.terminate()

        observer.join()


    if __name__ == "__main__":
        main()

else:
    print("\n🟢 PyNext running in PRODUCTION mode\n")

    from server_runner import start
    start()