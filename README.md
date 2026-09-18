# Krock Framework

Krock is a high-performance, hybrid full-stack web framework combining a Python backend with a React 19 and TypeScript frontend compiled via esbuild and styled with Tailwind CSS.

It provides a Next.js-like developer experience—complete with file-system routing, automatic Tailwind CSS processing, React 19 SSR and hydration, Ahead-Of-Time (AOT) production bundling, bounded LRU caching, and an intuitive Python API engine.

---

## Getting Started

### Option 1: Create App CLI (Recommended)

You can generate a brand new Krock project instantly using `create-krock-app`:

```bash
npx create-krock-app@latest
```

Follow the interactive prompts to set your project name and directory.

### Option 2: Manual Setup

If you prefer setting up manually or adding Krock to an existing project:

1. **Clone or Download the Repository**
   ```bash
   git clone https://github.com/your-repo/krock.git
   cd krock
   ```

2. **Install Node Dependencies**
   ```bash
   npm install
   ```

3. **Set Up Python Environment & Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the Development Server**
   ```bash
   python run.py
   ```
   *Starts the dev server with hot-reloading at http://localhost:3000.*

---

## Production Deployment

For production environments, pre-compile all static bundles and SSR templates Ahead-Of-Time (AOT):

```bash
# 1. Pre-compile all bundles
python run.py build

# 2. Launch in Production mode
DEPLOYMENT=prod python run.py
```

---

## Features Overview

- **File-System Routing**: Add `.tsx` files in `pages/` for UI pages, or `.py` files in `pages/api/` for backend API routes.
- **React 19 SSR & Hydration**: Full server-side HTML rendering with `ReactDOM.hydrateRoot` for zero-flicker client hydration.
- **Python Request Wrapper (`KrockRequest`)**: Clean API helper providing `req.json()`, `req.query`, `req.method`, `req.params`, and status tuple responses.
- **Zero-Config Dev Mode**: Runs out of the box on port 3000 with hot-reloading without requiring a `.env` file.
- **Bounded LRU Cache**: Thread-safe memory caching preventing memory leaks on dynamic routes.
- **Tailwind CSS Built-In**: Automatic CSS extraction, bundling, and hot-injection.
- **Database Ready**: Pre-configured with SQLAlchemy and Alembic (defaults to SQLite, supports PostgreSQL, MySQL, MongoDB).
- **Client Utilities**: Includes `lib/krock.ts` for typed API fetches (`krockFetch`) and parameter extraction (`getKrockParams`).

---

## Project Directory Structure

```text
krock/
├── pages/                  # Frontend pages & Backend APIs
│   ├── api/                # Python API routes
│   │   └── todos.py        # Accessible at http://localhost:3000/api/todos
│   ├── layout.tsx          # Global React layout wrapper
│   ├── globals.css         # Global CSS & Tailwind imports
│   └── index.tsx           # Entry page (http://localhost:3000/)
├── components/             # Reusable React components
├── lib/                    # Client-side TypeScript utilities
│   └── krock.ts            # Typed API fetch & parameter helpers
├── alembic/                # Database migration scripts
├── db.py                   # Database connection setup
├── models.py               # SQLAlchemy ORM models
├── core.py                 # Core Krock routing & WSGI engine
├── run.py                  # Dev server launcher & build runner
└── server_runner.py        # Waitress WSGI server runner
```

---

## Usage Guide & Code Examples

### 1. Creating Backend API Routes (`pages/api/`)

Create a Python file inside `pages/api/`. Use the `KrockRequest` object for simple, clean request handling:

```python
# pages/api/hello.py

def handler(req):
    method = req.method

    if method == "GET":
        name = req.get("name", "World")
        return {"message": f"Hello, {name}!"}

    if method == "POST":
        data = req.json()
        title = data.get("title", "")
        if not title:
            return {"error": "Title is required"}, "400 Bad Request"
        
        return {"status": "created", "title": title}, "201 Created"
```

*Note*: Legacy WSGI signature `def handler(environ, params):` is also supported for backward compatibility.

### 2. Creating Frontend Pages (`pages/`)

Create a React component exported as `default` inside `pages/`:

```tsx
// pages/about.tsx
import React from 'react';

export default function About({ params }: { params: any }) {
    return (
        <div className="p-8 max-w-2xl mx-auto">
            <h1 className="text-3xl font-bold text-blue-600 mb-4">About Us</h1>
            <p className="text-gray-700 text-lg">
                Welcome to our application built with Krock!
            </p>
        </div>
    );
}
```

### 3. Fetching API Data in Components (`lib/krock.ts`)

Use `krockFetch` for typed client-side API requests:

```tsx
// pages/todos.tsx
import React, { useEffect, useState } from 'react';
import { krockFetch } from '@/lib/krock';

export default function TodosPage() {
    const [todos, setTodos] = useState<any[]>([]);

    useEffect(() => {
        krockFetch('/api/todos')
            .then((data) => setTodos(data))
            .catch((err) => console.error(err));
    }, []);

    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold mb-4">Todo List</h1>
            <ul className="space-y-2">
                {todos.map((todo) => (
                    <li key={todo.id} className="p-3 bg-white rounded shadow">
                        {todo.title}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

---

## Database Configuration (SQLAlchemy + Alembic)

Krock comes pre-configured with SQLAlchemy ORM and Alembic migrations.

### 1. Define Models
Define database tables in `models.py`:

```python
# models.py
from sqlalchemy import Column, Integer, String, Boolean
from db import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
```

### 2. Run Database Migrations

```bash
# Generate a new migration script
alembic revision --autogenerate -m "Add Task table"

# Apply migrations to database
alembic upgrade head
```

### 3. Switch to PostgreSQL or MySQL

To use PostgreSQL or MySQL instead of the default SQLite:

Update `SQLALCHEMY_DATABASE_URL` in both `db.py` and `alembic.ini`:

```python
# PostgreSQL Example
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"

# MySQL Example
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://user:password@localhost/dbname"
```

---

## License

MIT License. Contributions and feedback are welcome!