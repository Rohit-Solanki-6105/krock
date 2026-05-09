from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
import sys
import os
import importlib

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from db import Base
# from models import Todo

# --- AUTOMATIC MODEL DISCOVERY ---
IGNORE_DIRS = {".git", "venv", "node_modules", "__pycache__", "alembic", ".krock_tmp", "styles"}

def discover_models():
    """Scans the project for files named *model*.py or *schema*.py and imports them"""
    for root, dirs, files in os.walk(project_root):
        # Prune ignored directories from the walk
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith(".py") and ("model" in file.lower() or "schema" in file.lower()):
                filepath = os.path.join(root, file)
                # Convert file path to python module path (e.g., pages.todos.models)
                module_name = os.path.relpath(filepath, project_root).replace(os.sep, '.')[:-3]
                try:
                    importlib.import_module(module_name)
                    print(f"[ALEMBIC] Auto-discovered models in: {module_name}")
                except Exception as e:
                    print(f"[ALEMBIC WARNING] Failed to import {module_name}: {e}")

# Run discovery before setting target_metadata
discover_models()
target_metadata = Base.metadata
# t1 = Todo.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
