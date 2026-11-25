
# ITUM Medical Center Management System

## Project Description

The ITUM Medical Center Management System is a web-based application developed to manage the medical center activities within the Institute of Technology, University of Moratuwa (ITUM).

The system provides a centralized platform for managing patients, doctors, appointments, medical submissions, medical records, prescriptions, notifications, and administrative activities.

## Main Features

- User Registration and Login
- Patient Management
- Doctor Management
- Appointment Booking and Management
- Medical Document Submission
- Medical Records Management
- Prescription Management
- Notification Management
- Admin Dashboard
- Reports Management

## User Roles

### 1. Patient (Student / Staff)
- Register and log in to the system.
- Book medical appointments.
- View appointment details and status.
- Submit medical documents.
- View medical records and prescriptions.
- View notifications.

### 2. Doctor
- Log in to the system.
- View appointment requests.
- Approve or reject appointments.
- Review medical submissions.
- Accept or reject medical submissions.
- Create medical records and prescriptions.

### 3. Administrator
- Manage patient information.
- Manage doctor information.
- Activate and deactivate doctors.
- Monitor appointments and medical submissions.
- Manage notifications.
- View system reports.

## Technologies Used

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- Flask
- Flask-CORS

### Database
- MySQL

### Development Tools
- Visual Studio Code
- WampServer
- Git and GitHub

## Project Structure

```text
Medical Center/
│
├── backend/
│   └── app.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── Other HTML files
│
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/thisuri2004/ITUM-Medical-Center-Management-System.git
```

### 2. Navigate to the Project Folder

```bash
cd ITUM-Medical-Center-Management-System
```

### 3. Create and Activate a Virtual Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
```

### 4. Install Required Dependencies

```bash
pip install flask flask-cors mysql-connector-python
```

### 5. Configure the MySQL Database

- Start MySQL using WampServer.
- Create the database named `itum_medical_center`.
- Import the database SQL file included in the project.
- Configure the database connection settings in the backend.

### 6. Run the Backend

```bash
cd backend
python app.py
```

The backend server will run at:

```text
http://127.0.0.1:5000
```

### 7. Run the Frontend

Open the frontend `index.html` file using a local development server or the project's configured frontend hosting method.

## Project Purpose

This project was developed as an academic software development project to improve the efficiency of medical center management within the university environment.

## Author

Developed by: H.N.M.T.D. Rathnapriya

Institute of Technology
University of Moratuwa
