import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Zero-config default: fallback to 'dev' if DEPLOYMENT is not specified
DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")

# Handle CLI build command: `python run.py build`
if len(sys.argv) > 1 and sys.argv[1] == "build":
    print("\n[RUN] Triggering Ahead-Of-Time (AOT) Production Build...")
    os.environ["DEPLOYMENT"] = "prod"
    from core import Krock
    app = Krock()
    app.build_all()
    print("[RUN] AOT Build Finished Successfully!\n")
    sys.exit(0)

if DEPLOYMENT == "dev":
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        HAS_WATCHDOG = True
    except ImportError:
        HAS_WATCHDOG = False

    print("\n[RUN] Krock running in DEV mode (Hot Reload Enabled)")
    print("[RUN] Zero-Config Active - Defaulting to Port 3000\n")

    WATCH_DIRS = ["pages", "core.py", "server_runner.py", "components"]
    IGNORE = {".krock_tmp", "__pycache__", "node_modules", "venv", "styles", ".git"}
    VALID_EXTENSIONS = (".tsx", ".jsx", ".py", ".js", ".json", ".css")

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
            if self.should_ignore(path) or not path.endswith(VALID_EXTENSIONS):
                return
            now = time.time()
            if now - self.last_restart < 0.8:
                return
            self.last_restart = now
            print(f"\n[RUN] File modified: {path}")
            self.restart()

        def on_created(self, event):
            self.on_modified(event)

    def start_server():
        env = os.environ.copy()
        env["DEPLOYMENT"] = "dev"
        return subprocess.Popen([sys.executable, "server_runner.py"], env=env)

    def main():
        process = start_server()

        def restart():
            nonlocal process
            print("[RUN] Reloading server...")
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

            process = start_server()
            print("[RUN] Server reloaded.")

        if HAS_WATCHDOG:
            event_handler = ReloadHandler(restart)
            observer = Observer()
            for path in WATCH_DIRS:
                if os.path.exists(path):
                    observer.schedule(event_handler, path, recursive=True)
            observer.start()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                process.terminate()
            observer.join()
        else:
            print("[RUN] Watchdog module not found. Server running without hot-reload.")
            try:
                process.wait()
            except KeyboardInterrupt:
                process.terminate()

    if __name__ == "__main__":
        main()

else:
    print("\n[RUN] Krock running in PRODUCTION mode\n")
    import server_runner