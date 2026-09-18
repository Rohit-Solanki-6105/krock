import os
from waitress import serve
from core import Krock

app = Krock()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 3000))
DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")
CPU_COUNT = os.cpu_count() or 4
WORKER_THREADS = min(32, max(8, CPU_COUNT * 4))

def start(host=HOST, port=PORT):
    print("\n" + "=" * 60)
    print(f"KROCK ULTRA-SCALE ENGINE ({DEPLOYMENT.upper()} MODE)")
    print("=" * 60)
    print(f"  Local URL:       http://localhost:{port}")
    print(f"  Network URL:     http://{host}:{port}")
    print(f"  Worker Threads:  {WORKER_THREADS} (Auto-Tuned for {CPU_COUNT} CPU cores)")
    print(f"  Routes Loaded:   {len(app.routes)}")

    for _, base, file_path, ext in app.routes:
        print(f"   - {base.ljust(25)} -> {os.path.basename(file_path)}")

    print("=" * 60 + "\n")

    serve(
        app,
        host=host,
        port=port,
        threads=WORKER_THREADS
    )

if __name__ == "__main__":
    start()