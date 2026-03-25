def handler(environ):
    # API routes return dictionaries which the framework will convert to JSON
    return {
        "status": "success",
        "message": "Hello from the PyNext API route!",
        "framework": "Python"
    }