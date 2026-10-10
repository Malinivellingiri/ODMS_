"""Create the ODMS database/tables and seed the demo administrator.
Run after installing ODBC Driver 18 and pyodbc.
"""
import os
import pyodbc
from werkzeug.security import generate_password_hash

SERVER=os.environ.get('ODMS_DB_SERVER',r'localhost\SQLEXPRESS')
DRIVER=os.environ.get('ODMS_DB_DRIVER','ODBC Driver 18 for SQL Server')
DB='ODMS'

def master_conn():
    return pyodbc.connect(f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE=master;Trusted_Connection=yes;TrustServerCertificate=yes;', autocommit=True)

def db_conn():
    return pyodbc.connect(f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DB};Trusted_Connection=yes;TrustServerCertificate=yes;', autocommit=False)

print(f'Connecting to SQL Server: {SERVER}')
try:
    c=master_conn(); cur=c.cursor(); cur.execute("IF DB_ID(?) IS NULL EXEC('CREATE DATABASE [ODMS]')",DB); c.close()
except Exception as e:
    print('\nCould not connect to SQL Server.')
    print('Check that SQL Server/SQL Server Express is installed and running, and update ODMS_DB_SERVER if needed.')
    print('Error:',e); raise

schema=open(os.path.join(os.path.dirname(__file__),'database.sql'),encoding='utf-8').read()
# Run statements separated by GO. The CREATE DATABASE part is harmless after the DB exists.
parts=[]
for p in schema.split('\nGO'):
    p=p.strip()
    if p and not p.startswith('/*'):
        parts.append(p)
conn=db_conn(); cur=conn.cursor()
for p in parts:
    p=p.replace("CREATE DATABASE ODMS;","")
    p=p.replace("USE ODMS;","")
    if p.strip(): cur.execute(p)
# Seed admin.
cur.execute('SELECT id FROM Admins WHERE email=?','admin@odms.com')
if not cur.fetchone():
    cur.execute('INSERT INTO Admins(name,email,password_hash,is_active) VALUES (?,?,?,1)', 'Administrator','admin@odms.com',generate_password_hash('admin123'))
conn.commit(); conn.close()
print('\nODMS database setup completed.')
print('Admin email: admin@odms.com')
print('Admin password: admin123')
