import os
import sys
import time
import subprocess
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

load_dotenv()

DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")

if DEPLOYMENT in ("dev", "development"):

    print("\n[RUN] Krock running in DEV mode (Hot Reload Enabled)\n")

    WATCH_DIRS = ["pages", "core.py", "server_runner.py"]

    IGNORE = {
        ".krock_tmp",
        "__pycache__",
        "node_modules",
        "venv",
        "styles",
        ".git"
    }

    VALID_EXTENSIONS = (
        ".tsx",
        ".jsx",
        ".py",
        ".js",
        ".json",
        ".css"
    )


    class ReloadHandler(FileSystemEventHandler):

        def __init__(self, restart):
            self.restart = restart
            self.last_restart = 0

        def should_ignore(self, path):

            for ignore in IGNORE:
                if ignore in path:
                    return True

            return False

        def on_modified(self, event):

            if event.is_directory:
                return

            path = event.src_path

            if self.should_ignore(path):
                return

            if not path.endswith(VALID_EXTENSIONS):
                return

            now = time.time()

            # debounce (1 second)
            if now - self.last_restart < 1:
                return

            self.last_restart = now

            print(f"\n[RUN] File changed: {path}")
            self.restart()

        def on_created(self, event):
            self.on_modified(event)


    def start_server():
        return subprocess.Popen(
            [sys.executable, "server_runner.py"]
        )


    def main():

        process = start_server()

        def restart():

            nonlocal process

            print("[RUN] Restarting server...")

            process.terminate()
            process.wait()

            # ✅ clear cache BEFORE restarting
            try:
                import core
                if hasattr(core, "app") and hasattr(core.app, "cache"):
                    core.app.cache.clear()
                    print("[CACHE] Cleared")
            except:
                pass

            process = start_server()

            print("[RUN] Server restarted")

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

    print("\n[RUN] Krock running in PRODUCTION mode\n")

    from server_runner import start
    start()