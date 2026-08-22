import sqlite3

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing to-do tasks.",
    version="1.0"
)

DB_FILE = "tasks.db"


def get_connection():
    """Opens a new connection to the SQLite database file.

    check_same_thread=False lets FastAPI use this connection function
    from different request-handling threads safely for our simple case.
    row_factory makes rows behave like dictionaries (row["title"] instead
    of row[1]), which keeps our API responses looking the same as before.
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the tasks table if it doesn't exist yet, and seeds it
    with 3 example tasks only if the table is currently empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy milk", False),
                ("Read a book", True),
                ("Clean the house", False)
            ]
        )

    conn.commit()
    conn.close()


init_db()


@app.get(
    "/",
    summary="Get API information",
    description="Returns basic information about the Task API."
)
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }


@app.get(
    "/health",
    summary="Check API health",
    description="Returns the current health status of the API."
)
def health_check():
    return {"status": "ok"}


@app.get(
    "/tasks",
    summary="Get all tasks",
    description="Returns all tasks in the to-do list."
)
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()

    return [
        {"id": row["id"], "title": row["title"], "done": bool(row["done"])}
        for row in rows
    ]


@app.get(
    "/tasks/{task_id}",
    summary="Get a single task",
    description="Returns a task by its ID. Returns 404 if the task does not exist."
)
def get_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )

    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.post(
    "/tasks",
    status_code=201,
    summary="Create a task",
    description="Creates a new task with a title and sets done to false."
)
def create_task(task: dict):
    if "title" not in task or not task["title"].strip():
        raise HTTPException(
            status_code=400,
            detail="Title is required"
        )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task["title"], False)
    )
    conn.commit()

    new_id = cursor.lastrowid
    conn.close()

    return {"id": new_id, "title": task["title"], "done": False}


@app.put(
    "/tasks/{task_id}",
    summary="Update a task",
    description="Updates the title and/or completion status of an existing task."
)
def update_task(task_id: int, task: dict):
    if "title" not in task and "done" not in task:
        raise HTTPException(
            status_code=400,
            detail="At least title or done is required"
        )

    if "title" in task and not isinstance(task["title"], str):
        raise HTTPException(
            status_code=400,
            detail="Title must be text"
        )

    if "title" in task and not task["title"].strip():
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty"
        )

    if "done" in task and not isinstance(task["done"], bool):
        raise HTTPException(
            status_code=400,
            detail="Done must be true or false"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    existing_task = cursor.fetchone()

    if existing_task is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )

    new_title = task["title"] if "title" in task else existing_task["title"]
    new_done = task["done"] if "done" in task else bool(existing_task["done"])

    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (new_title, new_done, task_id)
    )
    conn.commit()
    conn.close()

    return {"id": task_id, "title": new_title, "done": new_done}


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task",
    description="Deletes an existing task by its ID."
)
def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    existing_task = cursor.fetchone()

    if existing_task is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return