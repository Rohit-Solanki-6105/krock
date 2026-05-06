def handler(environ, params):
    # API routes return dictionaries which the framework will convert to JSON
    return {
        "status": "success",
        "message": "Hello from the Krypter API route!",
        "framework": "Python"
    }