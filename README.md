# library.db
# Task Manager API

A simple CRUD API for managing tasks, built with FastAPI and MySQL.

## Features

- User registration
- Task management (Create, Read, Update, Delete)
- Task filtering by status
- Secure password hashing

## Database Schema

![ER Diagram](https://images.wondershare.com/edrawmax/article2023/er-diagram-for-library-management-system/er-diagram-library-management-system-9.jpg) 

## Setup Instructions

1. **Prerequisites**:
   - Python 3.7+
   - MySQL Server
   - pip package manager

2. **Install dependencies**:pip install fastapi uvicorn mysql-connector-python passlib python-multipart
3. 
3. **Database setup**:
- Create a MySQL database
- Run the `task_manager.sql` script to create tables

4. **Configuration**:
- Update the database credentials in `main.py`

5. **Run the application**:uvicorn main:app --reload

   
## API Endpoints

- `POST /users/` - Create a new user
- `POST /users/{user_id}/tasks/` - Create a new task for a user
- `GET /users/{user_id}/tasks/` - Get all tasks for a user
- `PUT /tasks/{task_id}` - Update a task
- `DELETE /tasks/{task_id}` - Delete a task

## Example Requests

Create a user:
```json
POST /users/
{
 "username": "testuser",
 "email": "test@example.com",
 "password": "securepassword"
}
POST /users/1/tasks/
{
    "title": "Complete project",
    "description": "Finish the API implementation",
    "status": "pending",
    "priority": "high",
    "due_date": "2023-12-20"
}
