from core import PyNext
app = PyNext()
# Mock the environ for WSGI
environ = {
    "REQUEST_METHOD": "GET",
    "PATH_INFO": "/",
}
def start_response(status, headers):
    print("Status:", status)

html = app(environ, start_response)
html_str = html[0].decode('utf-8')
if "<style>" in html_str and ".text-4xl" in html_str and ".text-green-400" in html_str:
    print("SUCCESS")
else:
    print("FAILED")
    print(html_str[:500])
