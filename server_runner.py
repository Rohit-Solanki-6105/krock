import os
from waitress import serve
from core import Krock

app = Krock()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 3000))
DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")

def start(host=HOST, port=PORT):
    print("\n" + "=" * 55)
    print(f"KROCK FRAMEWORK ({DEPLOYMENT.upper()} MODE)")
    print("=" * 55)
    print(f"  Local URL:   http://localhost:{port}")
    print(f"  Network URL: http://{host}:{port}")
    print(f"  Dynamic Routes Discovered: {len(app.routes)}")

    for _, base, file_path, ext in app.routes:
        print(f"   - {base.ljust(25)} -> {os.path.basename(file_path)}")

    print("=" * 55 + "\n")

    serve(
        app,
        host=host,
        port=port,
        threads=8
    )

if __name__ == "__main__":
    start()