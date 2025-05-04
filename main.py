from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, validator
from typing import List, Optional
import mysql.connector
from mysql.connector import Error
from passlib.context import CryptContext
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Database configuration
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),  # Remove hardcoded password
    'database': os.getenv('DB_NAME', 'task_manager')
}

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    created_at: str

class TaskCreate(BaseModel):
    title: str
    description: str = None
    status: str = 'pending'
    priority: str = 'medium'
    due_date: datetime = None

    @validator('status')
    def validate_status(cls, value):
        valid_statuses = {"pending", "in_progress", "completed"}
        if value not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_statuses}")
        return value

    @validator('priority')
    def validate_priority(cls, value):
        valid_priorities = {"low", "medium", "high"}
        if value not in valid_priorities:
            raise ValueError(f"Invalid priority: {value}. Must be one of {valid_priorities}")
        return value

class TaskResponse(TaskCreate):
    task_id: int
    user_id: int
    created_at: str
    updated_at: str

# Database connection helper
def get_db_connection():
    for attempt in range(3):
        try:
            connection = mysql.connector.connect(**DATABASE_CONFIG)
            if connection.is_connected():
                logging.info("Database connection established")
                return connection
        except Error as e:
            logging.error(f"Attempt {attempt + 1}: Error connecting to MySQL: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database connection error after multiple attempts"
    )

# User endpoints
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    query = """
    INSERT INTO users (username, email, password_hash)
    VALUES (%s, %s, %s)
    """
    params = (user.username, user.email, hashed_password)
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        connection.commit()
        user_id = cursor.lastrowid
        
        # Fetch the created user
        cursor.execute("SELECT user_id, username, email, created_at FROM users WHERE user_id = %s", (user_id,))
        new_user = cursor.fetchone()
        
        if not new_user:
            raise HTTPException(status_code=404, detail="User not found after creation")
            
        return new_user
    except Error as e:
        if "Duplicate entry" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username or email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

# Task endpoints
VALID_STATUSES = {"pending", "in_progress", "completed"}

@app.post("/users/{user_id}/tasks/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(user_id: int, task: TaskCreate):
    query = """
    INSERT INTO tasks (user_id, title, description, status, priority, due_date)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (
        user_id,
        task.title,
        task.description,
        task.status,
        task.priority,
        task.due_date
    )
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        cursor.execute(query, params)
        connection.commit()
        task_id = cursor.lastrowid
        
        # Fetch the created task
        cursor.execute("""
            SELECT task_id, user_id, title, description, status, priority, due_date, created_at, updated_at
            FROM tasks WHERE task_id = %s
        """, (task_id,))
        new_task = cursor.fetchone()
        
        if not new_task:
            raise HTTPException(status_code=404, detail="Task not found after creation")
            
        return new_task
    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@app.get("/users/{user_id}/tasks/", response_model=List[TaskResponse])
def get_user_tasks(user_id: int, status: Optional[str] = None):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status value")
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        if status:
            cursor.execute("""
                SELECT task_id, user_id, title, description, status, priority, due_date, created_at, updated_at
                FROM tasks WHERE user_id = %s AND status = %s
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT task_id, user_id, title, description, status, priority, due_date, created_at, updated_at
                FROM tasks WHERE user_id = %s
            """, (user_id,))
            
        tasks = cursor.fetchall()
        return tasks
    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@app.put("/tasks/{task_id}/", response_model=TaskResponse)
def update_task(task_id: int, task: TaskCreate):
    query = """
    UPDATE tasks
    SET title = %s, description = %s, status = %s, priority = %s, due_date = %s, updated_at = NOW()
    WHERE task_id = %s
    """
    params = (task.title, task.description, task.status, task.priority, task.due_date, task_id)
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Check if task exists
        cursor.execute("SELECT 1 FROM tasks WHERE task_id = %s", (task_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Task not found")
        
        cursor.execute(query, params)
        connection.commit()
        
        # Fetch the updated task
        cursor.execute("""
            SELECT task_id, user_id, title, description, status, priority, due_date, created_at, updated_at
            FROM tasks WHERE task_id = %s
        """, (task_id,))
        updated_task = cursor.fetchone()
        
        if not updated_task:
            raise HTTPException(status_code=404, detail="Task not found after update")
            
        return updated_task
    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()