ODMS - Microsoft SQL Server Version

This version uses:
- HTML/CSS/JavaScript frontend
- Python Flask backend
- Microsoft SQL Server database

Do NOT double-click the HTML files. Start Flask and open http://127.0.0.1:5000/ in the browser.

Quick setup:
1. Install Python, Microsoft SQL Server and ODBC Driver 18 for SQL Server.
2. Open this folder in VS Code.
3. Create a virtual environment: py -m venv venv
4. Activate it: .\venv\Scripts\Activate.ps1
5. Install packages: pip install -r requirements.txt
6. Create the database: python setup_database.py
7. Start the app: python app.py
8. Open: http://127.0.0.1:5000/

Default SQL Server connection: localhost\SQLEXPRESS using Windows Authentication.
If your SQL Server instance is different, see README_SQL_SERVER.md.

Demo administrator:
Email: admin@odms.com
Password: admin123

The database tables are Users, Admins, OrganRequests, Notifications and Activities.
