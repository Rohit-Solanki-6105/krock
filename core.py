import os
import sys
import json
import time
import re
import subprocess
import importlib.util
from urllib.parse import unquote
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer

DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")
IS_DEV = DEPLOYMENT == "dev"

class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

def resolve_alias(path, project_root):
    if path.startswith("@/"):
        return os.path.join(project_root, path.replace("@/", ""))
    return path


def get_imports(file_path, project_root):
    imports = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(r'import .* from [\'"](.*?)[\'"]', content)

    for imp in matches:
        if imp.startswith(".") or imp.startswith("@/"):
            full_path = resolve_alias(
                os.path.normpath(os.path.join(os.path.dirname(file_path), imp)),
                project_root
            )

            for ext in [".tsx", ".ts", ".jsx", ".js"]:
                if os.path.exists(full_path + ext):
                    imports.append(full_path + ext)
                    break

    return imports

class Krock:
    def __init__(self, pages_dir="pages"):
        self.pages_dir = os.path.abspath(pages_dir)
        self.routes = self._discover_routes()
        self.cache = {}
        self.dep_cache = {}

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

        print("\n[CORE] Krock Turbo Running")
       



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

        for root, _, files in os.walk(self.pages_dir):
            for file in files:

                if file.startswith("layout.") or file.startswith(".entry"):
                    continue

                if not file.endswith((".py", ".tsx", ".jsx")):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.pages_dir)

                parts = rel_path.replace("\\", "/").split("/")
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

    def _compile_tsx(self, file_path, params=None):
        if params is None:
            params = {}

        
        # ENV MODE
        
        DEPLOYMENT = os.getenv("DEPLOYMENT", "dev")
        IS_DEV = DEPLOYMENT == "dev"

        project_root = os.path.dirname(self.pages_dir)
        tmp_dir = os.path.join(project_root, ".krock_tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        print(f"[CORE] Compiling {file_path}")
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

            if check_dir == self.pages_dir:
                break

            parent = os.path.dirname(check_dir)
            if parent == check_dir:
                break

            check_dir = parent

        
        # Dependency graph
        deps = self.build_dependency_graph(file_path, project_root)

        timestamps = []

        for dep in deps:
            if os.path.exists(dep):
                timestamps.append(os.path.getmtime(dep))

        for l in layouts:
            if os.path.exists(l):
                timestamps.append(os.path.getmtime(l))

        latest_dep_time = max(timestamps) if timestamps else 0

        cache_key = f"{file_path}:{latest_dep_time}:{json.dumps(params, sort_keys=True)}"

        
        # DEV MODE → NO CACHE
        
        if not IS_DEV and cache_key in self.cache:
            print("[CACHE] HIT")
            return self.cache[cache_key]

        if IS_DEV:
            self.cache.clear()
            self.dep_cache.clear()

        
        # Layout wrappers
        
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

        
        # Safe name (dynamic routes safe)
        
        safe_name = file_name.replace("[", "").replace("]", "").replace(".", "_")

        page_rel = os.path.relpath(file_path, tmp_dir).replace("\\", "/")
        if not page_rel.startswith("."):
            page_rel = "./" + page_rel

        
        # CLIENT ENTRY
        
        entry_file = os.path.join(tmp_dir, f"entry_{safe_name}.tsx")

        entry_code = f"""
import React from 'react';
import ReactDOM from 'react-dom/client';
import Page from '{page_rel}';
{layout_imports}

const rootEl = document.getElementById("root");

function render(App) {{
    if (window.__KROCK_ROOT__) {{
        window.__KROCK_ROOT__.unmount();
    }}
    window.__KROCK_ROOT__ = ReactDOM.createRoot(rootEl);
    window.__KROCK_ROOT__.render(App);
}}

render({layout_wrappers_browser});

// Standard browser navigation will be used instead of SPA logic
"""

        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(entry_code)

        
        # SSR ENTRY
        
        ssr_file = os.path.join(tmp_dir, f"ssr_{safe_name}.tsx")

        ssr_code = f"""
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Page from '{page_rel}';
{layout_imports}

const params = JSON.parse(process.argv[2] || "{{}}");

const html = ReactDOMServer.renderToString(
    {layout_wrappers_ssr}
);

console.log(html);
"""

        with open(ssr_file, "w", encoding="utf-8") as f:
            f.write(ssr_code)

        
        # Bundle paths
        
        browser_bundle = os.path.join(tmp_dir, f"browser_{safe_name}.js")
        ssr_bundle = os.path.join(tmp_dir, f"ssr_{safe_name}.js")

        
        # DEV → force rebuild
        
        if IS_DEV:
            if os.path.exists(browser_bundle):
                os.remove(browser_bundle)
            if os.path.exists(ssr_bundle):
                os.remove(ssr_bundle)

        
        # Browser bundle
        
        if not os.path.exists(browser_bundle):
            subprocess.run([
                "node", 
                os.path.join(project_root, "esbuild_worker.js"),
                "browser", 
                entry_file, 
                browser_bundle
            ])

        with open(browser_bundle, "r", encoding="utf-8") as f:
            browser_js = f.read()

        
        # Read extracted CSS if present
        
        browser_css_file = browser_bundle.replace(".js", ".css")
        browser_css_tw_file = browser_css_file.replace(".css", "_tw.css")
        injected_css = ""
        
        if os.path.exists(browser_css_file):
            npx = "npx.cmd" if os.name == "nt" else "npx"
            cmd = [npx, "tailwindcss", "-i", browser_css_file, "-o", browser_css_tw_file]
            if not IS_DEV:
                cmd.append("--minify")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print("Tailwind Error:", result.stderr)
            
            if os.path.exists(browser_css_tw_file):
                with open(browser_css_tw_file, "r", encoding="utf-8") as f:
                    injected_css = f.read()
            else:
                with open(browser_css_file, "r", encoding="utf-8") as f:
                    injected_css = f.read()

        
        # SSR bundle
        
        if not os.path.exists(ssr_bundle):
            subprocess.run([
                "node", 
                os.path.join(project_root, "esbuild_worker.js"),
                "node", 
                ssr_file, 
                ssr_bundle
            ])

        
        # Run SSR
        
        result = subprocess.run(
            ["node", ssr_bundle, json.dumps(params)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        ssr_html = result.stdout

        print(f"[CORE] Built in {time.time() - start_time:.3f}s")

        
        # Cleanup temp entries
        
        # for f in [entry_file, ssr_file]:
        #     if os.path.exists(f):
        #         os.remove(f)

        
        # Final HTML
        
        final_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Krock</title>
<link rel="stylesheet" href="/styles/output.css">
<style>{injected_css}</style>
</head>
<body>

<div id="root">{ssr_html}</div>

<script data-params>
{json.dumps(params)}
</script>

<script>
{browser_js}
</script>

</body>
</html>
"""

        if not IS_DEV:
            self.cache[cache_key] = final_html

        return final_html
    def __call__(self, environ, start_response):

        method = environ.get("REQUEST_METHOD", "GET")
        path = unquote(environ.get("PATH_INFO", "/"))

        print(f"[{method}] {path}")

        # if path.startswith("/_bundle"):

        #     target = (
        #         path
        #         .replace("/_bundle", "")
        #         .replace(".js", "")
        #     )

        #     if target == "":
        #         target = "/"

        #     for regex, base, file_path, ext in self.routes:

        #         if base == target:

        #             js = self._compile_tsx(file_path)

        #             start_response(
        #                 '200 OK',
        #                 [
        #                     ('Content-type', 'application/javascript'),
        #                 ]
        #             )

        #             return (js.encode("utf-8"),)

        for regex, base, file_path, ext in self.routes:

            match = regex.match(path)

            if match:

                params = match.groupdict()

                if ext in ["tsx", "jsx"]:

                    html = self._compile_tsx(file_path, params)

                    start_response(
                        '200 OK',
                        [
                            ('Content-type', 'text/html'),
                        ]
                    )

                    return (html.encode("utf-8"),)
                elif ext == "py":

                    spec = importlib.util.spec_from_file_location(
                        "m",
                        file_path
                    )

                    m = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(m)

                    # if path.startswith("/api/"):
                    if hasattr(m, "handler"):
                        data = (
                            m.handler(environ, params)
                            if hasattr(m, "handler")
                            else {}
                        )

                        res = json.dumps(data).encode("utf-8")

                        start_response(
                            '200 OK',
                            [
                                ('Content-type', 'application/json'),
                            ]
                        )

                        return (res,)

                    if hasattr(m, "render"):
                    # else:
                        res = (
                            m.render(params)
                            if hasattr(m, "render")
                            else ""
                        ).encode("utf-8")

                        start_response(
                            '200 OK',
                            [
                                ('Content-type', 'text/html'),
                            ]
                        )

                        return (res,)

        start_response(
            '404 Not Found',
            [('Content-type', 'text/html')]
        )

        return (b"<h1>404 - Page Not Found</h1>",)