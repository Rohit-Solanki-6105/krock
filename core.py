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


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class PyNext:
    def __init__(self, pages_dir="pages"):
        self.pages_dir = os.path.abspath(pages_dir)
        self.routes = self._discover_routes()

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

        print("\n[CORE] PyNext Turbo Running")

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

#     def _compile_tsx(self, file_path):
#         print(f"⚙️ Compiling {file_path}")
#         start_time = time.time()
        
#         current_dir = os.path.dirname(
#             os.path.abspath(file_path)
#         )

#         layout_path = None
#         check_dir = current_dir

#         while check_dir.startswith(self.pages_dir):

#             potential = os.path.join(
#                 check_dir,
#                 "layout.tsx"
#             )

#             if os.path.exists(potential):
#                 layout_path = potential
#                 break

#             check_dir = os.path.dirname(check_dir)

#         dir_name = os.path.dirname(file_path)
#         file_name = os.path.basename(file_path)

#         entry_file = os.path.join(
#             dir_name,
#             f".entry_{file_name}"
#         )

#         if layout_path:

#             rel_layout = os.path.relpath(
#                 layout_path,
#                 dir_name
#             ).replace("\\", "/")

#             if not rel_layout.startswith("."):
#                 rel_layout = f"./{rel_layout}"

#             layout_import = f"import Layout from '{rel_layout}';"

#             render_logic = (
#                 "React.createElement(Layout,null,"
#                 "React.createElement(Page,{params:window.__PARAMS__}))"
#             )

#         else:

#             layout_import = ""
#             render_logic = (
#                 "React.createElement(Page,"
#                 "{params:window.__PARAMS__})"
#             )

#         entry_code = f"""
# import React from 'react';
# import ReactDOM from 'react-dom/client';
# import Page from './{file_name}';
# {layout_import}
# ReactDOM.createRoot(
# document.getElementById('root')
# ).render({render_logic});
# """

#         with open(entry_file, "w", encoding="utf-8") as f:
#             f.write(entry_code)

#         cmd = self.esbuild + [
#             entry_file,
#             "--bundle",
#             "--format=iife",
#             "--minify",
#             "--platform=browser"
#         ]

#         result = subprocess.run(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         print(f"⚡ Built in {time.time() - start_time:.3f}s")

#         if os.path.exists(entry_file):
#             os.remove(entry_file)
        

#         return result.stdout

    def _compile_tsx(self, file_path):

        print(f"[CORE] Compiling {file_path}")
        start_time = time.time()

        current_dir = os.path.dirname(
            os.path.abspath(file_path)
        )

        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)

        # ----------------------------------------
        # Collect all layouts (root -> child)
        # ----------------------------------------
        layouts = []
        check_dir = current_dir

        while True:

            potential = os.path.join(
                check_dir,
                "layout.tsx"
            )

            if os.path.exists(potential):
                layouts.append(potential)

            if check_dir == self.pages_dir:
                break

            parent = os.path.dirname(check_dir)

            if parent == check_dir:
                break

            check_dir = parent

        # root → child order
        # layouts

        # ----------------------------------------
        # Generate layout imports & wrappers
        # ----------------------------------------
        layout_imports = ""
        layout_wrappers = "React.createElement(Page, { params: window.__PARAMS__ })"

        for i, layout in enumerate(layouts):

            rel_layout = os.path.relpath(
                layout,
                dir_name
            ).replace("\\", "/")

            if not rel_layout.startswith("."):
                rel_layout = f"./{rel_layout}"

            layout_name = f"Layout{i}"

            layout_imports += f"import {layout_name} from '{rel_layout}';\n"

            layout_wrappers = f"""
React.createElement(
    {layout_name},
    null,
    {layout_wrappers}
)
    """

        # ----------------------------------------
        # Create temporary entry file
        # ----------------------------------------
        entry_file = os.path.join(
            dir_name,
            f".entry_{file_name}"
        )

        entry_code = f"""
import React from 'react';
import ReactDOM from 'react-dom/client';
import Page from './{file_name}';
{layout_imports}

ReactDOM.createRoot(
    document.getElementById('root')
).render(
    {layout_wrappers}
);
    """

        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(entry_code)

        # ----------------------------------------
        # ESBuild compile
        # ----------------------------------------
        cmd = self.esbuild + [
            entry_file,
            "--bundle",
            "--format=iife",
            "--platform=browser",
            "--loader:.tsx=tsx",
            "--jsx=automatic"
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.stderr:
            print("[CORE] ESBUILD ERROR:")
            print(result.stderr)

        print(f"[CORE] Built in {time.time() - start_time:.3f}s")

        # ----------------------------------------
        # Cleanup
        # ----------------------------------------
        if os.path.exists(entry_file):
            os.remove(entry_file)

        return result.stdout

    def __call__(self, environ, start_response):

        method = environ.get("REQUEST_METHOD", "GET")
        path = unquote(environ.get("PATH_INFO", "/"))

        print(f"[{method}] {path}")

        if path.startswith("/_bundle"):

            target = (
                path
                .replace("/_bundle", "")
                .replace(".js", "")
            )

            if target == "":
                target = "/"

            for regex, base, file_path, ext in self.routes:

                if base == target:

                    js = self._compile_tsx(file_path)

                    start_response(
                        '200 OK',
                        [
                            ('Content-type', 'application/javascript'),
                        ]
                    )

                    return (js.encode("utf-8"),)

        for regex, base, file_path, ext in self.routes:

            match = regex.match(path)

            if match:

                params = match.groupdict()

                if ext in ["tsx", "jsx"]:

                    js_url = (
                        f"/_bundle"
                        f"{base if base != '/' else ''}"
                        ".js"
                    )

                    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script>
window.__PARAMS__ = {json.dumps(params)};
</script>
</head>
<body>
<div id="root"></div>
<script src="{js_url}"></script>
</body>
</html>"""

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

                    if path.startswith("/api/"):

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

                    else:

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