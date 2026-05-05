import json
from urllib.parse import parse_qs
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import db
from models import Todo

def handler(environ, params):
    method = environ.get("REQUEST_METHOD", "GET")
    session = db.get_db()

    try:
        if method == "GET":
            todos = session.query(Todo).order_by(Todo.id.desc()).all()
            return [todo.to_dict() for todo in todos]

        elif method == "POST":
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(content_length)
            data = json.loads(body)
            
            title = data.get("title", "").strip()
            if not title:
                return {"error": "Title is required"}

            new_todo = Todo(title=title)
            session.add(new_todo)
            session.commit()
            session.refresh(new_todo)
            return new_todo.to_dict()

        elif method == "PUT":
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(content_length)
            data = json.loads(body)
            
            todo_id = data.get("id")
            completed = data.get("completed", False)
            
            if not todo_id:
                return {"error": "ID is required"}

            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if not todo:
                return {"error": "Not found"}

            todo.completed = completed
            session.commit()
            session.refresh(todo)
            return todo.to_dict()

        elif method == "DELETE":
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                body = environ['wsgi.input'].read(content_length)
                data = json.loads(body)
                todo_id = data.get("id")
            else:
                query_string = environ.get('QUERY_STRING', '')
                query_params = parse_qs(query_string)
                todo_id = query_params.get("id", [None])[0]

            if not todo_id:
                return {"error": "ID is required"}

            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if todo:
                session.delete(todo)
                session.commit()
            
            return {"success": True}

        return {"error": "Method not allowed"}
    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
