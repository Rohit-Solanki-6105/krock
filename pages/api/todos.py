import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import db
from models import Todo

def handler(req):
    """Refactored API handler using KrockRequest for clean, modern Python API design."""
    method = req.method
    session = db.get_db()

    try:
        if method == "GET":
            todos = session.query(Todo).order_by(Todo.id.desc()).all()
            return [todo.to_dict() for todo in todos]

        elif method == "POST":
            data = req.json()
            title = data.get("title", "").strip()
            if not title:
                return {"error": "Title is required"}, "400 Bad Request"

            new_todo = Todo(title=title)
            session.add(new_todo)
            session.commit()
            session.refresh(new_todo)
            return new_todo.to_dict(), "201 Created"

        elif method == "PUT":
            data = req.json()
            todo_id = data.get("id")
            completed = data.get("completed", False)

            if not todo_id:
                return {"error": "ID is required"}, "400 Bad Request"

            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if not todo:
                return {"error": "Not found"}, "404 Not Found"

            todo.completed = completed
            session.commit()
            session.refresh(todo)
            return todo.to_dict()

        elif method == "DELETE":
            todo_id = req.get("id")
            if not todo_id and req.body():
                todo_id = req.json().get("id")

            if not todo_id:
                return {"error": "ID is required"}, "400 Bad Request"

            todo = session.query(Todo).filter(Todo.id == todo_id).first()
            if todo:
                session.delete(todo)
                session.commit()

            return {"success": True}

        return {"error": "Method not allowed"}, "405 Method Not Allowed"
    except Exception as e:
        session.rollback()
        return {"error": str(e)}, "500 Internal Server Error"
    finally:
        session.close()
