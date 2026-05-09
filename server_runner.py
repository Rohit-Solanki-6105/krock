from waitress import serve
from core import Krock

app = Krock()

print("\n[SERVER] Server running at http://localhost:3000\n")

serve(
    app,
    host="0.0.0.0",
    port=3000,
    threads=8
)