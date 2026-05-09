# Krock Framework

**Krock** is an ultra-fast, hybrid full-stack framework. It combines the simplicity and speed of a **Python WSGI backend** with the modern, component-driven experience of **React & TypeScript** on the frontend. 

It provides a Next.js-like developer experience—complete with hot-reloading, filesystem-based routing, Tailwind CSS integration, and a built-in SQLAlchemy database layer!

## Installation

```npm
npx create-krock-app@latest
```

`Note: first of all it will ask for project name : . = current folder`

---

## Features
- **Filesystem Routing**: Drop a `.tsx` file in the `/pages` folder and it becomes a route.
- **Python API Routes**: Drop a `.py` file in `/pages/api` and handle backend logic natively.
- **Tailwind CSS Built-in**: Seamless utility-first styling with auto-injection and hot-reloading.
- **React 19 & TypeScript**: Native support out of the box via `esbuild`.
- **Database Ready**: Pre-configured with SQLAlchemy & Alembic (defaults to SQLite, supports Postgres, MySQL, etc.).
- **Hot Reloading**: Instant updates when you modify React components, CSS, or Python backend files.

---

## Getting Started

1. **Install Dependencies**
   Ensure you have both Node.js and Python installed.
   ```bash
   # Install Node packages (React, esbuild, Tailwind)
   npm install

   # Install Python packages
   pip install -r requirements.txt
   ```

2. **Run the Development Server**
   ```bash
   npm run dev
   ```
   *This starts the Python watcher and the esbuild bundler in development mode. Head over to `http://localhost:3000` to see your app!*

---

## Project Structure

```text
krock/
├── pages/                  # Frontend pages & Backend APIs
│   ├── api/                # Python API routes
│   │   └── todos.py        # Example: http://localhost:3000/api/todos
│   ├── layout.tsx          # Global React layout wrapper
│   ├── globals.css         # Global CSS & Tailwind imports
│   └── index.tsx           # Entry page (http://localhost:3000/)
├── components/             # Reusable React components
├── alembic/                # Database migration scripts
├── db.py                   # Database connection setup
├── models.py               # SQLAlchemy ORM models
├── core.py                 # Core routing & WSGI engine (Do not edit)
└── run.py                  # Dev server and Hot-reloader
```

---

## Pages & Routing (Frontend)

Routing is entirely determined by your filesystem in the `pages/` directory. 

### Creating a Page
To create a new route, simply create a React component:
```tsx
// pages/about.tsx
import React from 'react';

export default function About() {
    return <h1 className="text-2xl text-blue-500">About Us</h1>;
}
```
*Navigating to `/about` will render this component.*

### The Layout
`pages/layout.tsx` is a special file that wraps all of your pages. Use this for your Navigation bar, Footer, and global imports.
```tsx
import "./globals.css"; // Your Tailwind CSS
export default function Layout({ children }) {
    return (
        <div>
            <nav>My App Navbar</nav>
            <main>{children}</main>
        </div>
    );
}
```

---

## API Routes (Backend)

You can write full Python backend logic alongside your frontend! Any `.py` file inside `pages/api/` becomes an endpoint.

### Creating an API Endpoint
```python
# pages/api/hello.py
import json

def handler(environ, params):
    # environ contains all standard WSGI request data
    method = environ.get("REQUEST_METHOD", "GET")

    if method == "GET":
        return {"message": "Hello from Python!"}
    
    if method == "POST":
        # Read JSON body
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        body = environ['wsgi.input'].read(content_length)
        data = json.loads(body)
        return {"status": "success", "received": data}
```
*This is accessible at `http://localhost:3000/api/hello`.*

---

## Styling with Tailwind CSS

Tailwind v3 is deeply integrated. 
1. Write your standard Tailwind classes directly inside your `.tsx` files.
2. Ensure `globals.css` includes the Tailwind directives:
   ```css
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```
3. Import `globals.css` inside your `layout.tsx`.

The framework automatically bundles your CSS and injects it into the page to prevent unstyled flashes (FOUC).

---

## Database & ORM (SQLAlchemy + Alembic)

Krock comes pre-configured with **SQLAlchemy** (for querying) and **Alembic** (for migrations).

### 1. Defining Models
Define your database tables in `models.py`:
```python
# models.py
from sqlalchemy import Column, Integer, String
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
```

### 2. Database Migrations
Whenever you change `models.py`, you must generate a migration script to update the database schema:
```bash
# 1. Generate the migration script
alembic revision --autogenerate -m "Added User table"

# 2. Apply the migration to the database
alembic upgrade head
```

### 3. Switching Databases (SQLite, Postgres, MySQL)
By default, the framework uses **SQLite** (`todos.db`). You can easily switch to a production database like **PostgreSQL** or **MySQL**.

To switch, simply update the `sqlalchemy.url` in **two places**:
1. **`db.py`**
2. **`alembic.ini`**

**PostgreSQL Example:**
```python
# Install psycopg2: pip install psycopg2-binary
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"
```
**MySQL Example:**
```python
# Install PyMySQL: pip install pymysql
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://user:password@localhost/dbname"
```

### Using MongoDB?
If you prefer NoSQL like MongoDB, you can safely delete `alembic/`, `alembic.ini`, and remove SQLAlchemy. Instead, use `pymongo` or `mongoengine` directly inside your `db.py`.

---

## 🚀 Production Deployment

When you are ready to deploy to production, set your environment variable:

```bash
# Windows
set DEPLOYMENT=prod
python run.py

# Linux/Mac
DEPLOYMENT=prod python run.py
```
In `prod` mode, the framework turns off hot-reloading, minifies the JavaScript and CSS bundles via `esbuild`, and optimizes serving speeds for a production environment!

`Note: currently i am developing it properly, anyone can contribute to make it better, i am open to suggestions also.`