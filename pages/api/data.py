def handler(environ, params):
    # API routes return dictionaries which the framework will convert to JSON
    return {
        "status": "success",
        "message": "Hello from the Krock API route!",
        "framework": "Python"
    }