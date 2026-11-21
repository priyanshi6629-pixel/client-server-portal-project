# Client-Server Client Portal Web Application

A full-stack Client Portal web application developed using Python Flask, SQLite, HTML, CSS, and JavaScript.

## Features

- User registration and login
- Password hashing
- Session-based authentication
- Interactive dashboard with statistics
- Project creation, completion and deletion
- Task management with priority and deadline
- Task filtering by status and priority
- Project search
- Document uploads and deletion
- Message management
- Notifications
- Profile management
- Dark mode
- Responsive design
- SQLite database persistence

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- Database: SQLite
- Authentication: Flask sessions
- Security: Password hashing, protected API routes, file type validation

## Installation

1. Clone this repository.
2. Open the folder in VS Code.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate it:
   `venv\Scripts\activate`
5. Install dependencies:
   `pip install -r requirements.txt`
6. Run the application:
   `python app.py`
7. Open `http://127.0.0.1:5000`

## Project Structure

- `app.py` – Flask backend and API
- `templates/` – HTML templates
- `static/` – CSS and JavaScript
- `uploads/` – Uploaded files (created automatically)
- `portal.db` – SQLite database (created automatically)

## Purpose

This project demonstrates full-stack development, backend API integration, database management, authentication, CRUD operations, and responsive UI design.

## Disclaimer

This is an educational portfolio project. Before production deployment, additional security features such as CSRF protection, secure cookie settings, rate limiting, production server configuration, and proper secrets management should be implemented.
