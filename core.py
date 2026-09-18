import os
import sys
import json
import time
import re
import inspect
import hashlib
import subprocess
import importlib.util
import traceback
from collections import OrderedDict
import threading
from urllib.parse import unquote, parse_qs
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer

DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")
IS_DEV = DEPLOYMENT == "dev"

class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

class LRUCache:
    def __init__(self, capacity=1000):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def clear(self):
        with self.lock:
            self.cache.clear()

    def __contains__(self, key):
        with self.lock:
            return key in self.cache

class SSRWorkerPipe:
    """Internal Stdio Pipe Worker for SSR - No HTTP server, no open ports."""
    def __init__(self, project_root):
        self.project_root = project_root
        self.worker_script = os.path.join(project_root, "ssr_worker.js")
        self.process = None
        self.lock = threading.Lock()

    def _ensure_process(self):
        if self.process is None or self.process.poll() is not None:
            if os.path.exists(self.worker_script):
                self.process = subprocess.Popen(
                    ["node", self.worker_script],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1
                )

    def render(self, ssr_bundle, params):
        if not os.path.exists(self.worker_script):
            return None

        with self.lock:
            try:
                self._ensure_process()
                if self.process and self.process.stdin and self.process.stdout:
                    payload = json.dumps({"bundle_path": ssr_bundle, "params": params})
                    self.process.stdin.write(payload + "\n")
                    self.process.stdin.flush()

                    response_line = self.process.stdout.readline()
                    if response_line:
                        data = json.loads(response_line)
                        if "html" in data:
                            return data["html"]
            except Exception:
                if self.process:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                    self.process = None
        return None

class KrockRequest:
    """Modern request wrapper around WSGI environ and route parameters."""
    def __init__(self, environ, params=None):
        self.environ = environ
        self.params = params or {}
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = unquote(environ.get("PATH_INFO", "/"))
        self.query_string = environ.get("QUERY_STRING", "")
        parsed_qs = parse_qs(self.query_string)
        self.query = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}
        self._json = None
        self._body = None

    def body(self) -> bytes:
        if self._body is None:
            try:
                content_length = int(self.environ.get('CONTENT_LENGTH', 0) or 0)
            except ValueError:
                content_length = 0
            if content_length > 0:
                self._body = self.environ['wsgi.input'].read(content_length)
            else:
                self._body = b""
        return self._body

    def json(self):
        if self._json is None:
            b = self.body()
            if b:
                try:
                    self._json = json.loads(b.decode('utf-8'))
                except Exception:
                    self._json = {}
            else:
                self._json = {}
        return self._json

    def text(self) -> str:
        return self.body().decode('utf-8', errors='ignore')

    def get(self, key, default=None):
        if key in self.params:
            return self.params[key]
        if key in self.query:
            return self.query[key]
        return default

def resolve_alias(path, project_root):
    if path.startswith("@/"):
        return os.path.join(project_root, path.replace("@/", ""))
    return path

def get_imports(file_path, project_root):
    imports = []
    if not os.path.exists(file_path):
        return imports

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        matches = re.findall(r'import .* from [\'"](.*?)[\'"]', content)
        matches += re.findall(r'import [\'"](.*?)[\'"]', content)

        for imp in matches:
            if imp.startswith(".") or imp.startswith("@/"):
                full_path = resolve_alias(
                    os.path.normpath(os.path.join(os.path.dirname(file_path), imp)),
                    project_root
                )

                for ext in [".tsx", ".ts", ".jsx", ".js", ".css"]:
                    if os.path.exists(full_path + ext):
                        imports.append(full_path + ext)
                        break
                    elif os.path.exists(full_path):
                        imports.append(full_path)
                        break
    except Exception:
        pass

    return imports

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8"
}

class Krock:
    def __init__(self, pages_dir="pages"):
        self.pages_dir = os.path.abspath(pages_dir)
        self.project_root = os.path.dirname(self.pages_dir)
        self.routes = self._discover_routes()
        self.cache = LRUCache(capacity=1000)
        self.dep_cache = {}
        self.ssr_pipe = SSRWorkerPipe(self.project_root)

        venv_dir = os.path.dirname(sys.executable)
        esbuild_exe = os.path.join(
            venv_dir,
            "esbuild.exe" if os.name == "nt" else "esbuild"
        )

        if os.path.exists(esbuild_exe):
            self.esbuild = [esbuild_exe]
        else:
            npx = "npx.cmd" if os.name == "nt" else "npx"
            self.esbuild = [npx, "--yes", "esbuild"]

        print(f"[CORE] Krock Engine Active ({DEPLOYMENT.upper()} mode - Single Server)")

    def build_dependency_graph(self, entry, project_root):
        if entry in self.dep_cache:
            return self.dep_cache[entry]

        visited = set()
        stack = [entry]

        while stack:
            file = stack.pop()
            if file in visited:
                continue
            visited.add(file)

            for dep in get_imports(file, project_root):
                stack.append(dep)

        self.dep_cache[entry] = list(visited)
        return self.dep_cache[entry]

    def _discover_routes(self):
        routes = []
        if not os.path.exists(self.pages_dir):
            return routes

        for root, dirs, files in os.walk(self.pages_dir):
            # Exclude hidden directories, _ directories, or 'components' folders from route discovery
            dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("_") and d != "components"]

            for file in files:
                if file.startswith(".") or file.startswith("_") or file.startswith("layout."):
                    continue

                if not file.endswith((".py", ".tsx", ".jsx")):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.pages_dir)

                parts = rel_path.replace("\\", "/").split("/")
                if any(p.startswith(".") or p.startswith("_") or p == "components" for p in parts):
                    continue

                clean_parts = [
                    p for p in parts
                    if not (p.startswith("(") and p.endswith(")"))
                ]

                base_route = "/".join(clean_parts).rsplit(".", 1)[0]

                if base_route.endswith("/index"):
                    base_route = base_route[:-6]

                if base_route == "" or base_route == "index":
                    base_route = "/"
                else:
                    base_route = "/" + base_route

                pattern = re.sub(
                    r'\[\.\.\.(.+?)\]',
                    r'(?P<\1>.+)',
                    base_route
                )

                pattern = re.sub(
                    r'\[(.+?)\]',
                    r'(?P<\1>[^/]+)',
                    pattern
                )

                regex = re.compile(f"^{pattern}/?$")

                routes.append(
                    (
                        regex,
                        base_route,
                        file_path,
                        file.split(".")[-1]
                    )
                )

        return sorted(
            routes,
            key=lambda x: (
                x[1].count('['),
                "..." in x[1]
            )
        )

    def build_all(self):
        """Ahead-Of-Time (AOT) pre-compilation for production."""
        print("[BUILD] Pre-compiling all pages Ahead-Of-Time...")
        count = 0
        for regex, base, file_path, ext in self.routes:
            if ext in ["tsx", "jsx"]:
                self._compile_tsx(file_path, params={}, force_build=True)
                count += 1
        print(f"[BUILD] Successfully pre-compiled {count} pages.")

    def _render_error_html(self, title, details, stack_trace=""):
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Krock Error - {title}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2rem; max-width: 900px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #ef4444; font-size: 1.75rem; margin-top: 0; display: flex; align-items: center; gap: 0.5rem; }}
        .badge {{ background: #991b1b; color: #fca5a5; font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; }}
        pre {{ background: #0f172a; padding: 1.25rem; border-radius: 8px; overflow-x: auto; color: #38bdf8; font-family: monospace; font-size: 0.9rem; line-height: 1.5; border: 1px solid #1e293b; }}
        .details {{ font-size: 1.1rem; color: #cbd5e1; margin-bottom: 1.5rem; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{title} <span class="badge">Development Error</span></h1>
        <div class="details">{details}</div>
        {f'<pre>{stack_trace}</pre>' if stack_trace else ''}
    </div>
</body>
</html>"""

    def _compile_tsx(self, file_path, params=None, force_build=False):
        if params is None:
            params = {}

        DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")
        IS_DEV = DEPLOYMENT == "dev"

        tmp_dir = os.path.join(self.project_root, ".krock_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        start_time = time.time()
        current_dir = os.path.dirname(os.path.abspath(file_path))
        file_name = os.path.basename(file_path)

        # Collect layouts
        layouts = []
        check_dir = current_dir

        while True:
            potential = os.path.join(check_dir, "layout.tsx")
            if os.path.exists(potential):
                layouts.append(potential)

            if check_dir == self.pages_dir or check_dir == os.path.dirname(self.pages_dir):
                break

            parent = os.path.dirname(check_dir)
            if parent == check_dir:
                break

            check_dir = parent

        # Dependency graph
        deps = self.build_dependency_graph(file_path, self.project_root)
        timestamps = [os.path.getmtime(dep) for dep in deps if os.path.exists(dep)]
        for l in layouts:
            if os.path.exists(l):
                timestamps.append(os.path.getmtime(l))

        latest_dep_time = max(timestamps) if timestamps else 0
        cache_key = f"{file_path}:{latest_dep_time}:{json.dumps(params, sort_keys=True)}"

        if not IS_DEV and not force_build:
            cached_html = self.cache.get(cache_key)
            if cached_html:
                return cached_html

        safe_name = file_name.replace("[", "").replace("]", "").replace(".", "_")
        browser_bundle = os.path.join(tmp_dir, f"browser_{safe_name}.js")
        ssr_bundle = os.path.join(tmp_dir, f"ssr_{safe_name}.js")

        layout_imports = ""
        layout_wrappers_browser = "React.createElement(Page, { params: window.__PARAMS__ })"
        layout_wrappers_ssr = "React.createElement(Page, { params })"

        for i, layout in enumerate(layouts):
            rel_layout = os.path.relpath(layout, tmp_dir).replace("\\", "/")
            if not rel_layout.startswith("."):
                rel_layout = "./" + rel_layout

            name = f"Layout{i}"
            layout_imports += f"import {name} from '{rel_layout}';\n"
            layout_wrappers_browser = f"React.createElement({name}, null, {layout_wrappers_browser})"
            layout_wrappers_ssr = f"React.createElement({name}, null, {layout_wrappers_ssr})"

        page_rel = os.path.relpath(file_path, tmp_dir).replace("\\", "/")
        if not page_rel.startswith("."):
            page_rel = "./" + page_rel

        # CLIENT ENTRY GENERATION WITH HYDRATION FIX
        entry_file = os.path.join(tmp_dir, f"entry_{safe_name}.tsx")
        entry_code = f"""
import React from 'react';
import ReactDOM from 'react-dom/client';
import Page from '{page_rel}';
{layout_imports}

const rootEl = document.getElementById("root");
const appElement = {layout_wrappers_browser};

if (rootEl) {{
    if (rootEl.hasChildNodes()) {{
        ReactDOM.hydrateRoot(rootEl, appElement);
    }} else {{
        ReactDOM.createRoot(rootEl).render(appElement);
    }}
}}
"""

        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(entry_code)

        # SSR ENTRY GENERATION
        ssr_file = os.path.join(tmp_dir, f"ssr_{safe_name}.tsx")
        ssr_code = f"""
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Page from '{page_rel}';
{layout_imports}

const params = JSON.parse(process.argv[2] || "{{}}");

try {{
    const html = ReactDOMServer.renderToString({layout_wrappers_ssr});
    console.log(html);
}} catch (err) {{
    console.error("SSR_RENDER_ERROR:", err.stack || err);
    process.exit(1);
}}
"""

        with open(ssr_file, "w", encoding="utf-8") as f:
            f.write(ssr_code)

        # Browser bundle rebuild check
        need_browser_rebuild = True
        if os.path.exists(browser_bundle) and os.path.getmtime(browser_bundle) >= latest_dep_time and not IS_DEV:
            need_browser_rebuild = False

        if need_browser_rebuild:
            res = subprocess.run([
                "node", 
                os.path.join(self.project_root, "esbuild_worker.js"),
                "browser", 
                entry_file, 
                browser_bundle
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if res.returncode != 0 and IS_DEV:
                return self._render_error_html(
                    "TypeScript / React Build Error",
                    f"Failed to bundle <code>{file_path}</code>",
                    res.stderr or res.stdout
                )

        browser_js = ""
        if os.path.exists(browser_bundle):
            with open(browser_bundle, "r", encoding="utf-8") as f:
                browser_js = f.read()

        # Tailwind CSS injection
        browser_css_file = browser_bundle.replace(".js", ".css")
        browser_css_tw_file = browser_css_file.replace(".css", "_tw.css")
        injected_css = ""

        if os.path.exists(browser_css_file):
            npx = "npx.cmd" if os.name == "nt" else "npx"
            cmd = [npx, "tailwindcss", "-i", browser_css_file, "-o", browser_css_tw_file]
            if not IS_DEV:
                cmd.append("--minify")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if os.path.exists(browser_css_tw_file):
                with open(browser_css_tw_file, "r", encoding="utf-8") as f:
                    injected_css = f.read()
            else:
                with open(browser_css_file, "r", encoding="utf-8") as f:
                    injected_css = f.read()

        # SSR bundling check
        need_ssr_rebuild = True
        if os.path.exists(ssr_bundle) and os.path.getmtime(ssr_bundle) >= latest_dep_time and not IS_DEV:
            need_ssr_rebuild = False

        if need_ssr_rebuild:
            res = subprocess.run([
                "node", 
                os.path.join(self.project_root, "esbuild_worker.js"),
                "node", 
                ssr_file, 
                ssr_bundle
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if res.returncode != 0 and IS_DEV:
                return self._render_error_html(
                    "SSR Bundle Build Error",
                    f"Failed to bundle SSR entry for <code>{file_path}</code>",
                    res.stderr or res.stdout
                )

        # 1. FAST STDIO PIPE SSR ATTEMPT (NO HTTP SERVER, NO EXTRA PORTS)
        ssr_html = self.ssr_pipe.render(ssr_bundle, params)

        # 2. FALLBACK TO DIRECT SINGLE-PASS NODE EXECUTION IF PIPE FAILS
        if ssr_html is None:
            result = subprocess.run(
                ["node", ssr_bundle, json.dumps(params)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            if result.returncode != 0 and IS_DEV:
                return self._render_error_html(
                    "React SSR Runtime Error",
                    f"Exception during Server-Side Rendering of <code>{file_path}</code>",
                    result.stderr
                )
            ssr_html = result.stdout.strip()

        build_time = time.time() - start_time
        rel_display = os.path.relpath(file_path, self.project_root).replace("\\", "/")
        print(f"[CORE] Rendered {rel_display} in {build_time:.3f}s")

        final_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Krock App</title>
<style>{injected_css}</style>
<script src="/lib/router.js" defer></script>
</head>
<body>

<div id="root">{ssr_html}</div>

<script data-params>
window.__PARAMS__ = {json.dumps(params)};
</script>

<script>
{browser_js}
</script>

</body>
</html>"""

        if not IS_DEV:
            self.cache.set(cache_key, final_html)

        return final_html

    def _serve_static_file(self, path, start_response, environ):
        """Serve static files with ETag and HTTP 304 conditional caching."""
        if path.startswith("/"):
            clean_path = path[1:]
        else:
            clean_path = path

        possible_paths = [
            os.path.join(self.project_root, clean_path),
            os.path.join(self.project_root, "public", clean_path),
            os.path.join(self.project_root, ".krock_tmp", clean_path)
        ]

        for file_path in possible_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                _, ext = os.path.splitext(file_path)
                content_type = MIME_TYPES.get(ext.lower(), "application/octet-stream")

                with open(file_path, "rb") as f:
                    content = f.read()

                etag = f'"{hashlib.md5(content).hexdigest()}"'
                if_none_match = environ.get("HTTP_IF_NONE_MATCH")

                if if_none_match and if_none_match == etag:
                    start_response("304 Not Modified", [("ETag", etag)])
                    return (b"",)

                start_response(
                    "200 OK",
                    [
                        ("Content-Type", content_type),
                        ("Content-Length", str(len(content))),
                        ("ETag", etag),
                        ("Cache-Control", "public, max-age=3600" if not IS_DEV else "no-cache")
                    ]
                )
                return (content,)

        return None

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = unquote(environ.get("PATH_INFO", "/"))

        # Serve static asset or client loader
        static_res = self._serve_static_file(path, start_response, environ)
        if static_res is not None:
            return static_res

        # Match dynamic routes
        for regex, base, file_path, ext in self.routes:
            match = regex.match(path)
            if match:
                params = match.groupdict()

                if ext in ["tsx", "jsx"]:
                    try:
                        html = self._compile_tsx(file_path, params)
                        etag = f'"{hashlib.md5(html.encode("utf-8")).hexdigest()}"'
                        if_none_match = environ.get("HTTP_IF_NONE_MATCH")

                        if if_none_match and if_none_match == etag:
                            start_response("304 Not Modified", [("ETag", etag)])
                            return (b"",)

                        start_response("200 OK", [
                            ("Content-type", "text/html; charset=utf-8"),
                            ("ETag", etag),
                            ("Cache-Control", "public, max-age=60" if not IS_DEV else "no-cache")
                        ])
                        return (html.encode("utf-8"),)
                    except Exception as e:
                        stack = traceback.format_exc()
                        print(f"[ERROR] TSX Page Error: {e}\n{stack}")
                        err_html = self._render_error_html("Framework Error", str(e), stack)
                        start_response("500 Internal Server Error", [("Content-type", "text/html; charset=utf-8")])
                        return (err_html.encode("utf-8"),)

                elif ext == "py":
                    try:
                        start_py_time = time.time()
                        spec = importlib.util.spec_from_file_location("m", file_path)
                        m = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(m)

                        rel_file = os.path.relpath(file_path, self.project_root).replace("\\", "/")

                        if hasattr(m, "handler"):
                            sig = inspect.signature(m.handler)
                            req = KrockRequest(environ, params)

                            if len(sig.parameters) == 1:
                                result = m.handler(req)
                            else:
                                result = m.handler(environ, params)

                            if isinstance(result, tuple) and len(result) == 2:
                                data, status_code = result
                            else:
                                data = result
                                status_code = "200 OK"

                            if isinstance(data, (dict, list)):
                                res_bytes = json.dumps(data).encode("utf-8")
                                content_type = "application/json; charset=utf-8"
                            elif isinstance(data, str):
                                res_bytes = data.encode("utf-8")
                                content_type = "text/html; charset=utf-8"
                            elif isinstance(data, bytes):
                                res_bytes = data
                                content_type = "application/octet-stream"
                            else:
                                res_bytes = json.dumps(data).encode("utf-8")
                                content_type = "application/json; charset=utf-8"

                            elapsed = time.time() - start_py_time
                            status_str = status_code if isinstance(status_code, str) else "200 OK"
                            print(f"[CORE] Executed [{method}] {rel_file} -> {status_str} in {elapsed:.3f}s")

                            etag = f'"{hashlib.md5(res_bytes).hexdigest()}"'
                            if_none_match = environ.get("HTTP_IF_NONE_MATCH")

                            if if_none_match and if_none_match == etag and method == "GET":
                                start_response("304 Not Modified", [("ETag", etag)])
                                return (b"",)

                            start_response(status_str, [
                                ("Content-type", content_type),
                                ("Content-Length", str(len(res_bytes))),
                                ("ETag", etag)
                            ])
                            return (res_bytes,)

                        elif hasattr(m, "render"):
                            res = m.render(params).encode("utf-8")
                            elapsed = time.time() - start_py_time
                            print(f"[CORE] Rendered {rel_file} in {elapsed:.3f}s")
                            start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
                            return (res,)

                    except Exception as e:
                        stack = traceback.format_exc()
                        print(f"[ERROR] API Route Error: {e}\n{stack}")
                        err_data = json.dumps({"error": str(e), "traceback": stack if IS_DEV else None})
                        start_response("500 Internal Server Error", [("Content-type", "application/json")])
                        return (err_data.encode("utf-8"),)

        start_response("404 Not Found", [("Content-type", "text/html; charset=utf-8")])
        return (b"<h1>404 - Page Not Found</h1>",)