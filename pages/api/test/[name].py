def handler(environ, params):
    slug = params.get('name')
    # You can now use the slug to query a database
    return {
        "status": "success",
        "data": {
            "title": f"Viewing post: {slug}",
            "content": "This data was fetched using a dynamic Python route!"
        }
    }