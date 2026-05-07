from waitress import serve
from core import Krypter

app = Krypter()

print("\n[SERVER] Server running at http://localhost:3000\n")

serve(
    app,
    host="0.0.0.0",
    port=3000,
    threads=8
)