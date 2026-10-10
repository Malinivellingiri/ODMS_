# ODMS - Local Setup with Microsoft SQL Server

This version keeps the existing HTML/CSS/JavaScript interface and replaces browser Local Storage with a Flask/Python backend and Microsoft SQL Server database.

## Architecture

Browser (HTML/CSS/JavaScript) -> Flask/Python API -> Microsoft SQL Server

## Requirements

1. Windows 10/11
2. Python 3.9+ (Python 3.11/3.12 is recommended)
3. Microsoft SQL Server Express/Developer/LocalDB
4. SQL Server Management Studio (SSMS) is recommended
5. Microsoft ODBC Driver 18 for SQL Server

## 1. Check SQL Server

If you installed SQL Server Express with the default instance, the server is usually:

`localhost\\SQLEXPRESS`

If your SQL Server has another instance name, change `ODMS_DB_SERVER` in the environment or in `app.py`.

## 2. Open the project

Open this folder in VS Code:

`ODMS`

## 3. Create virtual environment

Open Terminal in VS Code:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

```cmd
venv\Scripts\activate.bat
```

## 4. Install Python packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Create database

Make sure SQL Server is running. Then:

```powershell
python setup_database.py
```

This creates:

- ODMS database
- Users table
- Admins table
- OrganRequests table
- Notifications table
- Activities table
- Demo administrator

## 6. Start the application

```powershell
python app.py
```

Open Chrome and visit:

`http://127.0.0.1:5000/`

Do not double-click the HTML file for this version. Run Flask first.

## Demo administrator

Email: `admin@odms.com`

Password: `admin123`

## If your SQL Server uses SQL authentication

Set these environment variables before starting Flask:

```powershell
$env:ODMS_DB_SERVER="localhost\\SQLEXPRESS"
$env:ODMS_DB_TRUSTED="no"
$env:ODMS_DB_USER="your_sql_username"
$env:ODMS_DB_PASSWORD="your_sql_password"
```

Then run:

```powershell
python app.py
```

## Main database flow

Registration -> Users

Organ request -> OrganRequests

Matching -> Users + OrganRequests

Notifications -> Notifications

Admin activity -> Activities

## Important

The matching score in this demo is the same simple configured scoring logic from the original frontend:

- Blood group factor: 40%
- Organ factor: 35%
- Availability factor: 25%

This is an application demonstration rule, not a medical transplant-allocation algorithm. Real clinical matching requires validated medical rules and authorized clinical systems.
