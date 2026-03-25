import os
import sys
import json
import time
import re
import subprocess
import importlib.util
from urllib.parse import parse_qs, unquote
from wsgiref.simple_server import make_server, WSGIServer
from socketserver import ThreadingMixIn

# Multi-threaded server for handling concurrent HTML and JS requests
class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

class PyNext:
    def __init__(self, pages_dir="pages"):
        self.pages_dir = os.path.abspath(pages_dir)
        self.cache = {}
        self.routes = self._discover_routes()
        print("\n🚀 PyNext Turbo: Dynamic Routing Active")

    def _discover_routes(self):
        """Scans the pages directory and maps file patterns like [slug] to Regex."""
        routes = []
        for root, _, files in os.walk(self.pages_dir):
            for file in files:
                if file.startswith("layout.") or file.startswith(".entry"): continue
                if file.endswith((".py", ".tsx", ".jsx")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.pages_dir)
                    
                    # 1. Standard Route Cleaning
                    parts = rel_path.replace("\\", "/").split("/")
                    clean_parts = [p for p in parts if not (p.startswith("(") and p.endswith(")"))]
                    base_route = "/".join(clean_parts).rsplit(".", 1)[0]
                    if base_route.endswith("/index"): base_route = base_route[:-6]
                    
                    if base_route == "" or base_route == "index": base_route = "/"
                    else: base_route = "/" + base_route

                    # 2. Convert to Regex Pattern for matching URLs
                    # Handle Catch-all [...slug]
                    pattern = re.sub(r'\[\.\.\.(.+?)\]', r'(?P<\1>.+)', base_route)
                    # Handle standard [slug]
                    pattern = re.sub(r'\[(.+?)\]', r'(?P<\1>[^/]+)', pattern)
                    
                    # Ensure exact matching and allow optional trailing slash
                    regex = re.compile(f"^{pattern}/?$")
                    
                    routes.append({
                        "regex": regex,
                        "base": base_route, 
                        "file": file_path,
                        "ext": file.split(".")[-1]
                    })
        
        # Sort: Static routes first, then dynamic [slug], then catch-all [...slug]
        return sorted(routes, key=lambda x: (x['base'].count('['), "..." in x['base']))

    def _compile_tsx(self, file_path):
        # --- Closest Layout Logic ---
        current_dir = os.path.dirname(os.path.abspath(file_path))
        layout_path = None
        check_dir = current_dir
        while check_dir.startswith(self.pages_dir):
            potential = os.path.join(check_dir, "layout.tsx")
            if os.path.exists(potential):
                layout_path = potential
                break
            check_dir = os.path.dirname(check_dir)

        page_mtime = os.path.getmtime(file_path)
        layout_mtime = os.path.getmtime(layout_path) if layout_path else 0
        cache_key = f"{file_path}_{page_mtime}_{layout_mtime}"
        if cache_key in self.cache: return self.cache[cache_key]

        print(f"⚙️  [MISS] Compiling {file_path}...")
        start_time = time.time()
        dir_name, file_name = os.path.dirname(file_path), os.path.basename(file_path)
        entry_file_path = os.path.join(dir_name, f".entry_{file_name}")
        
        # Entry Point wrapping Page with Params
        if layout_path:
            rel_layout = os.path.relpath(layout_path, dir_name).replace("\\", "/")
            if not rel_layout.startswith("."): rel_layout = f"./{rel_layout}"
            layout_import = f"import Layout from '{rel_layout}';"
            render_logic = "React.createElement(Layout, null, React.createElement(Page, {params: window.__PARAMS__}))"
        else:
            layout_import, render_logic = "", "React.createElement(Page, {params: window.__PARAMS__})"

        entry_code = f"import React from 'react'; import ReactDOM from 'react-dom/client'; import Page from './{file_name}'; {layout_import} ReactDOM.createRoot(document.getElementById('root')).render({render_logic});"
        with open(entry_file_path, "w", encoding="utf-8") as f: f.write(entry_code)

        venv_dir = os.path.dirname(sys.executable)
        esbuild_exe = os.path.join(venv_dir, "esbuild.exe" if os.name == "nt" else "esbuild")
        if os.path.exists(esbuild_exe):
            cmd = [esbuild_exe, entry_file_path, "--bundle", "--format=iife", "--minify", "--platform=browser"]
        else:
            npx = "npx.cmd" if os.name == "nt" else "npx"
            cmd = [npx, "--yes", "esbuild", entry_file_path, "--bundle", "--format=iife", "--minify", "--platform=browser"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(entry_file_path): os.remove(entry_file_path)
        print(f"⚡ Built in {time.time() - start_time:.3f}s")
        self.cache[cache_key] = result.stdout
        return result.stdout

    def __call__(self, environ, start_response):
        path = unquote(environ.get("PATH_INFO", "/")) # Fixes bracket encoding issues

        # --- 1. THE BUNDLE HANDLER ---
        if path.startswith("/_bundle"):
            # Clean the path to find the base route name
            target = path.replace("/_bundle", "").replace(".js", "")
            if target == "": target = "/"
            
            for route in self.routes:
                if route['base'] == target:
                    js = self._compile_tsx(route['file'])
                    start_response('200 OK', [('Content-type', 'application/javascript'), ('Cache-Control', 'no-cache')])
                    return [js.encode("utf-8")]

        # --- 2. THE DYNAMIC PAGE DISPATCHER ---
        for route in self.routes:
            match = route['regex'].match(path)
            if match:
                params = match.groupdict()
                
                if route['ext'] in ["tsx", "jsx"]:
                    js_url = f"/_bundle{route['base'] if route['base'] != '/' else ''}.js?v={int(time.time())}"
                    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
                    <script>window.__PARAMS__ = {json.dumps(params)};</script>
                    </head><body><div id="root"></div><script src="{js_url}"></script></body></html>"""
                    start_response('200 OK', [('Content-type', 'text/html')])
                    return [html.encode("utf-8")]

                elif route['ext'] == "py":
                    spec = importlib.util.spec_from_file_location("m", route['file'])
                    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
                    
                    if path.startswith("/api/"):
                        data = m.handler(environ, params) if hasattr(m, "handler") else {}
                        res = json.dumps(data).encode("utf-8")
                        start_response('200 OK', [('Content-type', 'application/json')])
                        return [res]
                    else:
                        res = (m.render(params) if hasattr(m, "render") else "").encode("utf-8")
                        start_response('200 OK', [('Content-type', 'text/html')])
                        return [res]

        start_response('404 Not Found', [('Content-type', 'text/html')])
        return [b"<h1>404 - Page Not Found</h1>"]

if __name__ == "__main__":
    with make_server('', 3000, PyNext(), server_class=ThreadedWSGIServer) as httpd:
        print("\n🚀 Server: http://localhost:3000")
        httpd.serve_forever()