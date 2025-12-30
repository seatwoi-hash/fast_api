from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import Optional
import sqlite3

api_v1 = APIRouter(prefix="/api/v1")


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


conn = sqlite3.connect("todo.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE
)
""")
conn.commit()

app = FastAPI(title="todo_app")


@api_v1.post("/task")
def create_task(task: TaskCreate):
    cur.execute(
        "INSERT INTO tasks (title, description, completed) VALUES (?, ?, ?)",
        (task.title, task.description, task.completed)
    )
    conn.commit()

    task_id = cur.lastrowid

    return {"id": task_id}


@api_v1.get("/tasks")
def get_all_tasks():
    tasks = cur.execute("SELECT * FROM tasks WHERE is_deleted = ?", (False,)).fetchall()
    return tasks


@api_v1.get("/task/{task_id}")
def get_task(task_id: int):
    task = cur.execute("SELECT * FROM tasks WHERE id = ? AND is_deleted = ?", (task_id, False,)).fetchone()
    return task


@api_v1.patch("/tasks/{task_id}")
def update_task(task_id: int, task_update: TaskUpdate):
    update_data = task_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Нет данных для обновления"
        )

    task = cur.execute("SELECT id FROM tasks WHERE id = ? AND is_deleted = ?", (task_id, False)).fetchone()

    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    update_fields = []
    update_values = []

    for field, value in update_data.items():
        if value is not None:
            update_fields.append(f"{field} = ?")
            update_values.append(value)

    update_values.append(task_id)

    sql = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
    cur.execute(sql, update_values)
    conn.commit()

    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = cur.fetchone()

    return updated_task


@api_v1.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    task = cur.execute("SELECT id FROM tasks WHERE id = ? AND is_deleted = ?", (task_id, False)).fetchone()

    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    cur.execute("UPDATE tasks SET is_deleted = ? WHERE id = ?", (True, task_id,))
    conn.commit()
    return {"id": task_id}


app.include_router(api_v1)


@app.get("/")
def root():
    return {"message": "TodoApp API", "docs": "/docs"}
