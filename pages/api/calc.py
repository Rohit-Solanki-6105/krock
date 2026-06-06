import json
import math


def safe_eval(expr):

    allowed = {
        "sqrt": math.sqrt,
        "pow": pow,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log
    }

    return eval(expr, {"__builtins__": {}}, allowed)


def handler(environ, params):

    method = environ.get("REQUEST_METHOD")

    try:

        # -------- POST --------
        if method == "POST":

            length = int(environ.get("CONTENT_LENGTH", 0))
            body = environ["wsgi.input"].read(length).decode("utf-8")

            data = json.loads(body)
            formula = data.get("formula", "")

            if not formula:
                return {
                    "status": "error",
                    "message": "No formula provided"
                }

            result = safe_eval(formula)

            return {
                "status": "success",
                "formula": formula,
                "result": result
            }

        # -------- GET --------
        elif method == "GET":

            query = environ.get("QUERY_STRING", "")
            formula = ""

            if "formula=" in query:
                formula = query.split("formula=")[1]

            if not formula:
                return {
                    "status": "error",
                    "message": "No formula"
                }

            result = safe_eval(formula)

            return {
                "status": "success",
                "formula": formula,
                "result": result
            }

        else:

            return {
                "status": "error",
                "message": "Method not allowed"
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }