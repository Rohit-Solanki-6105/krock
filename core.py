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

#     def _compile_tsx(self, file_path):

#         print(f"[CORE] Compiling {file_path}")
#         start_time = time.time()

#         current_dir = os.path.dirname(
#             os.path.abspath(file_path)
#         )

#         dir_name = os.path.dirname(file_path)
#         file_name = os.path.basename(file_path)

#         # ----------------------------------------
#         # Collect all layouts (root -> child)
#         # ----------------------------------------
#         layouts = []
#         check_dir = current_dir

#         while True:

#             potential = os.path.join(
#                 check_dir,
#                 "layout.tsx"
#             )

#             if os.path.exists(potential):
#                 layouts.append(potential)

#             if check_dir == self.pages_dir:
#                 break

#             parent = os.path.dirname(check_dir)

#             if parent == check_dir:
#                 break

#             check_dir = parent

#         # root → child order
#         # layouts

#         # ----------------------------------------
#         # Generate layout imports & wrappers
#         # ----------------------------------------
#         layout_imports = ""
#         layout_wrappers = "React.createElement(Page, { params: window.__PARAMS__ })"

#         for i, layout in enumerate(layouts):

#             rel_layout = os.path.relpath(
#                 layout,
#                 dir_name
#             ).replace("\\", "/")

#             if not rel_layout.startswith("."):
#                 rel_layout = f"./{rel_layout}"

#             layout_name = f"Layout{i}"

#             layout_imports += f"import {layout_name} from '{rel_layout}';\n"

#             layout_wrappers = f"""
# React.createElement(
#     {layout_name},
#     null,
#     {layout_wrappers}
# )
#     """

#         # ----------------------------------------
#         # Create temporary entry file
#         # ----------------------------------------
#         entry_file = os.path.join(
#             dir_name,
#             f".entry_{file_name}"
#         )

#         entry_code = f"""
# import React from 'react';
# import ReactDOM from 'react-dom/client';
# import Page from './{file_name}';
# {layout_imports}

# ReactDOM.createRoot(
#     document.getElementById('root')
# ).render(
#     {layout_wrappers}
# );
#     """

#         with open(entry_file, "w", encoding="utf-8") as f:
#             f.write(entry_code)

#         # ----------------------------------------
#         # ESBuild compile
#         # ----------------------------------------
#         cmd = self.esbuild + [
#             entry_file,
#             "--bundle",
#             "--format=iife",
#             "--platform=browser",
#             "--loader:.tsx=tsx",
#             "--jsx=automatic"
#         ]

#         result = subprocess.run(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )

#         if result.stderr:
#             print("[CORE] ESBUILD ERROR:")
#             print(result.stderr)

#         print(f"[CORE] Built in {time.time() - start_time:.3f}s")

#         # ----------------------------------------
#         # Cleanup
#         # ----------------------------------------
#         if os.path.exists(entry_file):
#             os.remove(entry_file)

#         return result.stdout
#     def _compile_tsx(self, file_path, params=None):
#         if params == None:
#             params = {}

#         print(f"[CORE] Compiling {file_path}")
#         start_time = time.time()

#         current_dir = os.path.dirname(
#             os.path.abspath(file_path)
#         )

#         dir_name = os.path.dirname(file_path)
#         file_name = os.path.basename(file_path)

#         # ----------------------------------------
#         # Collect all layouts (root -> child)
#         # ----------------------------------------
#         layouts = []
#         check_dir = current_dir

#         while True:

#             potential = os.path.join(
#                 check_dir,
#                 "layout.tsx"
#             )

#             if os.path.exists(potential):
#                 layouts.append(potential)

#             if check_dir == self.pages_dir:
#                 break

#             parent = os.path.dirname(check_dir)

#             if parent == check_dir:
#                 break

#             check_dir = parent

#         # ----------------------------------------
#         # Generate layout imports & wrappers
#         # ----------------------------------------
#         layout_imports = ""
#         client_wrappers = "React.createElement(Page, { params: window.__PARAMS__ })"
#         server_wrappers = "React.createElement(Page, { params })"

#         for i, layout in enumerate(layouts):

#             rel_layout = os.path.relpath(
#                 layout,
#                 dir_name
#             ).replace("\\", "/")

#             if not rel_layout.startswith("."):
#                 rel_layout = f"./{rel_layout}"

#             layout_name = f"Layout{i}"

#             layout_imports += f"import {layout_name} from '{rel_layout}';\n"

#             client_wrappers = f"""
# React.createElement(
#     {layout_name},
#     null,
#     {client_wrappers}
# )
#         """

#             server_wrappers = f"""
# React.createElement(
#     {layout_name},
#     null,
#     {server_wrappers}
# )
#         """

#         # ----------------------------------------
#         # Create client entry
#         # ----------------------------------------
#         client_entry = os.path.join(
#             dir_name,
#             f".entry_client_{file_name}"
#         )

#         client_code = f"""
# import React from 'react';
# import {{ hydrateRoot }} from 'react-dom/client';
# import Page from './{file_name}';
# {layout_imports}

# hydrateRoot(
#     document.getElementById('root'),
#     {client_wrappers}
# );
#     """

#         with open(client_entry, "w", encoding="utf-8") as f:
#             f.write(client_code)

#         # ----------------------------------------
#         # Create SSR entry
#         # ----------------------------------------
#         ssr_entry = os.path.join(
#             dir_name,
#             f".entry_ssr_{file_name}"
#         )

#         ssr_code = f"""
# import React from 'react';
# import {{ renderToString }} from 'react-dom/server';
# import Page from './{file_name}';
# {layout_imports}

# const params = JSON.parse(process.argv[2] || '{{}}');

# const html = renderToString(
#     {server_wrappers}
# );

# console.log(html);
#     """

#         with open(ssr_entry, "w", encoding="utf-8") as f:
#             f.write(ssr_code)

#         # ----------------------------------------
#         # Build client bundle
#         # ----------------------------------------
#         client_cmd = self.esbuild + [
#             client_entry,
#             "--bundle",
#             "--format=iife",
#             "--platform=browser",
#             "--loader:.tsx=tsx",
#             "--jsx=automatic"
#         ]

#         client_result = subprocess.run(
#             client_cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )

#         if client_result.stderr:
#             print("[CORE] CLIENT BUILD ERROR:")
#             print(client_result.stderr)

#         client_js = client_result.stdout

#         # ----------------------------------------
#         # Build SSR bundle
#         # ----------------------------------------
#         ssr_bundle = ssr_entry + ".js"

#         ssr_cmd = self.esbuild + [
#             ssr_entry,
#             "--bundle",
#             "--platform=node",
#             "--format=cjs",
#             "--outfile=" + ssr_bundle,
#             "--loader:.tsx=tsx",
#             "--jsx=automatic"
#         ]

#         subprocess.run(ssr_cmd)

#         # ----------------------------------------
#         # Run SSR bundle
#         # ----------------------------------------
#         ssr_html = ""

#         try:
#             result = subprocess.run(
#                 ["node", ssr_bundle, json.dumps(params)],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True
#             )

#             ssr_html = result.stdout.strip()

#         except Exception as e:
#             print("[CORE] SSR ERROR:", e)

#         # ----------------------------------------
#         # Cleanup
#         # ----------------------------------------
#         for f in [client_entry, ssr_entry, ssr_bundle]:
#             if os.path.exists(f):
#                 os.remove(f)

#         print(f"[CORE] Built in {time.time() - start_time:.3f}s")

#     # ----------------------------------------
#     # Return SEO HTML
#     # ----------------------------------------
#         html = f"""
# <!DOCTYPE html>
# <html>

# <head>
# <meta charset="UTF-8">
# <meta name="viewport" content="width=device-width, initial-scale=1">

# <script>
# window.__PARAMS__ = {{}}
# </script>

# <link rel="stylesheet" href="/styles/output.css">

# </head>

# <body>

# <div id="root">
# {ssr_html}
# </div>

# <script>
# {client_js}
# </script>

# </body>
# </html>
# """

#         return html

    def _compile_tsx(self, file_path, params=None):
        project_root = os.path.dirname(self.pages_dir)

        tmp_dir = os.path.join(project_root, ".krypter_tmp")

        os.makedirs(tmp_dir, exist_ok=True)
        
        if params is None:
            params = {}

        print(f"[CORE] Compiling {file_path}")
        start_time = time.time()

        current_dir = os.path.dirname(os.path.abspath(file_path))
        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)

        # ----------------------------------------
        # Collect layouts
        # ----------------------------------------
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

        # layouts.reverse()

        # ----------------------------------------
        # Generate layout imports
        # ----------------------------------------
        layout_imports = ""
        layout_wrappers_browser = "React.createElement(Page, { params: window.__PARAMS__ })"
        layout_wrappers_ssr = "React.createElement(Page, { params })"

        for i, layout in enumerate(layouts):

            rel_layout = os.path.relpath(layout, tmp_dir).replace("\\", "/")

            if not rel_layout.startswith("."):
                rel_layout = f"./{rel_layout}"

            layout_name = f"Layout{i}"

            layout_imports += f"import {layout_name} from '{rel_layout}';\n"

            layout_wrappers_browser = f"""
React.createElement(
    {layout_name},
    null,
    {layout_wrappers_browser}
)
    """

            layout_wrappers_ssr = f"""
React.createElement(
    {layout_name},
    null,
    {layout_wrappers_ssr}
)
    """

        # ----------------------------------------
        # Browser Entry
        # ----------------------------------------
        safe_name = file_name.replace("[", "").replace("]", "").replace(".", "_")

        entry_file = os.path.join(tmp_dir, f"entry_{safe_name}.tsx")
        page_rel = os.path.relpath(file_path, tmp_dir).replace("\\", "/")

        if not page_rel.startswith("."):
            page_rel = "./" + page_rel
        entry_code = f"""
import React from 'react';
import ReactDOM from 'react-dom/client';
import Page from './{page_rel}';
{layout_imports}

ReactDOM.createRoot(
    document.getElementById('root')
).render(
    {layout_wrappers_browser}
);
    """

        with open(entry_file, "w", encoding="utf-8") as f:
            f.write(entry_code)

        # ----------------------------------------
        # SSR Entry
        # ----------------------------------------
        ssr_file = os.path.join(tmp_dir, f"ssr_{safe_name}.tsx")

        ssr_code = f"""
import React from 'react';
import ReactDOMServer from 'react-dom/server';
import Page from './{file_name}';
{layout_imports}

const params = JSON.parse(process.argv[2] || "{{}}");

const html = ReactDOMServer.renderToString(
    {layout_wrappers_ssr}
);

console.log(html);
    """

        with open(ssr_file, "w", encoding="utf-8") as f:
            f.write(ssr_code)

        # ----------------------------------------
        # Build browser bundle
        # ----------------------------------------
        browser_cmd = self.esbuild + [
            entry_file,
            "--bundle",
            "--format=iife",
            "--platform=browser",
            "--loader:.tsx=tsx",
            "--jsx=automatic"
        ]

        browser_result = subprocess.run(
            browser_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if browser_result.stderr:
            print("[CORE] ESBUILD ERROR:")
            print(browser_result.stderr)

        # ----------------------------------------
        # Build SSR bundle
        # ----------------------------------------
        ssr_bundle = os.path.join(tmp_dir, f"ssr_bundle_{safe_name}.js")

        ssr_cmd = self.esbuild + [
            ssr_file,
            "--bundle",
            "--platform=node",
            "--outfile=" + ssr_bundle,
            "--loader:.tsx=tsx",
            "--jsx=automatic"
        ]

        subprocess.run(ssr_cmd)

        # ----------------------------------------
        # Run SSR
        # ----------------------------------------
        result = subprocess.run(
            ["node", ssr_bundle, json.dumps(params)],
            stdout=subprocess.PIPE,
            text=True
        )

        ssr_html = result.stdout

        print(f"[CORE] Built in {time.time() - start_time:.3f}s")

        # ----------------------------------------
        # Cleanup
        # ----------------------------------------
        for f in [entry_file, ssr_file, ssr_bundle]:
            if os.path.exists(f):
                os.remove(f)

        # ----------------------------------------
        # Final HTML
        # ----------------------------------------
        final_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Krypter</title>
<link rel="stylesheet" href="/styles/output.css">
</head>
<body>

<div id="root">{ssr_html}</div>

<script>
window.__PARAMS__ = {json.dumps(params)}
</script>

<script>
{browser_result.stdout}
</script>

</body>
</html>
"""

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