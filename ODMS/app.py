from flask import Flask, jsonify, request, session, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, re
import pyodbc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

app = Flask(__name__)
app.secret_key = os.environ.get('ODMS_SECRET_KEY', 'change-this-secret-key-for-production')

# SQL Server settings can be changed in environment variables or .env.
DB_SERVER = os.environ.get('ODMS_DB_SERVER', r'localhost\SQLEXPRESS')
DB_NAME = os.environ.get('ODMS_DB_NAME', 'ODMS')
DB_DRIVER = os.environ.get('ODMS_DB_DRIVER', 'ODBC Driver 18 for SQL Server')
DB_TRUSTED = os.environ.get('ODMS_DB_TRUSTED', 'yes').lower() in ('1','true','yes')
DB_USER = os.environ.get('ODMS_DB_USER', '')
DB_PASSWORD = os.environ.get('ODMS_DB_PASSWORD', '')


def connection_string(database=None):
    db = database or DB_NAME
    if DB_TRUSTED:
        return f'DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={db};Trusted_Connection=yes;TrustServerCertificate=yes;'
    return f'DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={db};UID={DB_USER};PWD={DB_PASSWORD};TrustServerCertificate=yes;'


def get_db():
    return pyodbc.connect(connection_string(), autocommit=False)


def rows(cursor):
    cols = [c[0] for c in cursor.description] if cursor.description else []
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


def iso(v):
    return v.isoformat(sep=' ', timespec='seconds') if hasattr(v, 'isoformat') else v


def clean_user(row, include_password=False):
    if not row:
        return None
    d = dict(row)
    for k, v in list(d.items()):
        d[k] = iso(v)
    if not include_password:
        d.pop('password_hash', None)
    return d


def log_activity(conn, activity_type, name, email, role, details):
    conn.cursor().execute(
        'INSERT INTO Activities(activity_type,name,email,role,details) VALUES (?,?,?,?,?)',
        activity_type, name or '-', email or '-', role or 'Admin', details or ''
    )


def add_notification(conn, email, message, ntype='info'):
    conn.cursor().execute(
        'INSERT INTO Notifications(email,message,notification_type) VALUES (?,?,?)',
        email, message, ntype
    )


def current_user(conn):
    uid = session.get('user_id')
    if not uid:
        return None
    cur = conn.cursor()
    cur.execute('SELECT * FROM Users WHERE id=?', uid)
    return clean_user(cur.fetchone_dict if False else None)


def user_row(conn, uid):
    cur = conn.cursor()
    cur.execute('SELECT id,name,email,phone,age,gender,role,blood_group AS bloodGroup,city,organ,availability,requested_organ AS requestedOrgan,urgency,registered_at AS registeredAt FROM Users WHERE id=?', uid)
    r = cur.fetchone()
    if not r:
        return None
    return clean_user(dict(zip([c[0] for c in cur.description], r)))


def require_user(conn, role=None):
    u = user_row(conn, session.get('user_id')) if session.get('user_id') else None
    if not u:
        return None, ('Unauthorized', 401)
    if role and u['role'] != role:
        return None, ('Forbidden', 403)
    return u, None


def require_admin():
    return session.get('admin_logged_in') is True


@app.route('/')
def home():
    return redirect('/temp/index.html')

@app.route('/temp/<path:filename>')
def temp_files(filename):
    return send_from_directory(TEMP_DIR, filename)

@app.route('/css/<path:filename>')
def css_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def js_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)


@app.get('/api/me')
def api_me():
    conn = get_db()
    try:
        u = user_row(conn, session.get('user_id')) if session.get('user_id') else None
        return jsonify({'loggedIn': bool(u), 'user': u})
    finally:
        conn.close()

@app.post('/api/register')
def api_register():
    d = request.get_json(silent=True) or {}
    required = ['name','email','phone','age','gender','role','bloodGroup','city','password','confirmPassword']
    if any(not str(d.get(k,'' )).strip() for k in required):
        return jsonify(error='Please fill in all required fields.'), 400
    if not re.fullmatch(r'\d{10}', str(d['phone'])):
        return jsonify(error='Phone number must contain exactly 10 digits.'), 400
    if d['password'] != d['confirmPassword']:
        return jsonify(error='Password and confirm password do not match.'), 400
    if d['role'] not in ('Donor','Recipient'):
        return jsonify(error='Please select a valid role.'), 400
    if d['role']=='Donor' and not d.get('organ'):
        return jsonify(error='Please select the organ you want to donate.'), 400
    if d['role']=='Recipient' and not d.get('requestedOrgan'):
        return jsonify(error='Please select the organ you need.'), 400
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM Users WHERE LOWER(email)=LOWER(?)', d['email'].strip())
        if cur.fetchone():
            return jsonify(error='This email address is already registered.'), 409
        now = datetime.now()
        cur.execute('''INSERT INTO Users(name,email,phone,age,gender,role,blood_group,city,password_hash,organ,availability,requested_organ,urgency,registered_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    d['name'].strip(), d['email'].strip(), d['phone'].strip(), int(d['age']), d['gender'], d['role'], d['bloodGroup'], d['city'].strip(),
                    generate_password_hash(d['password']),
                    d.get('organ') if d['role']=='Donor' else None,
                    (d.get('availability') or 'Available') if d['role']=='Donor' else 'Not Applicable',
                    d.get('requestedOrgan') if d['role']=='Recipient' else None,
                    d.get('urgency') if d['role']=='Recipient' else None, now)
        log_activity(conn,'Registration',d['name'],d['email'],d['role'],f"{d['role']} account registered.")
        add_notification(conn,d['email'],f"Your {d['role'].lower()} registration was completed successfully.",'registration')
        conn.commit()
        return jsonify(message='Registration successful.'), 201
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@app.post('/api/login')
def api_login():
    d = request.get_json(silent=True) or {}
    email, password, role = d.get('email','').strip(), d.get('password',''), d.get('role','')
    if not email or not password or role not in ('Donor','Recipient'):
        return jsonify(error='Please enter email, password and select a role.'), 400
    conn = get_db()
    try:
        cur=conn.cursor(); cur.execute('SELECT * FROM Users WHERE LOWER(email)=LOWER(?) AND role=?',email,role); r=cur.fetchone()
        if not r or not check_password_hash(r.password_hash,password):
            return jsonify(error='Invalid email, password or role.'), 401
        session['user_id']=r.id
        session.pop('admin_logged_in',None)
        log_activity(conn,'Login',r.name,r.email,r.role,f'{role} logged into ODMS.')
        add_notification(conn,r.email,f'You logged in successfully as a {role}.','login')
        conn.commit()
        return jsonify(message='Login successful.', user=user_row(conn,r.id))
    finally: conn.close()

@app.post('/api/logout')
def api_logout():
    uid=session.get('user_id')
    if uid:
        conn=get_db()
        try:
            u=user_row(conn,uid)
            if u:
                log_activity(conn,'Logout',u['name'],u['email'],u['role'],'User logged out of ODMS.')
                conn.commit()
        finally: conn.close()
    session.pop('user_id',None)
    return jsonify(message='Logged out.')

@app.post('/api/admin/login')
def api_admin_login():
    d=request.get_json(silent=True) or {}
    email=d.get('email','').strip(); password=d.get('password','')
    conn=get_db()
    try:
        cur=conn.cursor(); cur.execute('SELECT * FROM Admins WHERE LOWER(email)=LOWER(?) AND is_active=1',email); r=cur.fetchone()
        if not r or not check_password_hash(r.password_hash,password):
            return jsonify(error='Invalid administrator email or password.'),401
        session.clear(); session['admin_logged_in']=True; session['admin_id']=r.id
        log_activity(conn,'Admin Login','Administrator',r.email,'Admin','Administrator logged into ODMS.')
        conn.commit(); return jsonify(message='Admin login successful.')
    finally: conn.close()

@app.post('/api/admin/logout')
def api_admin_logout():
    if session.get('admin_logged_in'):
        conn=get_db()
        try:
            log_activity(conn,'Admin Logout','Administrator','admin@odms.com','Admin','Administrator logged out.')
            conn.commit()
        finally: conn.close()
    session.clear(); return jsonify(message='Admin logged out.')

@app.get('/api/admin/me')
def api_admin_me():
    return jsonify({'loggedIn': require_admin()})

@app.get('/api/notifications')
def api_notifications():
    conn=get_db()
    try:
        u,err=require_user(conn)
        if err:return jsonify(error=err[0]),err[1]
        cur=conn.cursor();cur.execute('SELECT id,date_created AS date,message,notification_type AS type FROM Notifications WHERE email=? ORDER BY id DESC',u['email'])
        data=[]
        for r in rows(cur): data.append(clean_user(r))
        return jsonify(data=data)
    finally:conn.close()

@app.post('/api/organ-requests')
def api_organ_request():
    conn=get_db()
    try:
        u,err=require_user(conn,'Recipient')
        if err:return jsonify(error=err[0]),err[1]
        d=request.get_json(silent=True) or {}; organ=d.get('organ'); urgency=d.get('urgency'); notes=d.get('notes','').strip()
        if not organ or not urgency:return jsonify(error='Please select the organ and urgency.'),400
        cur=conn.cursor(); cur.execute('''INSERT INTO OrganRequests(recipient_id,organ,urgency,notes,status,requested_at) VALUES(?,?,?,?,?,?)''',u['id'],organ,urgency,notes,'Pending',datetime.now())
        req_id=cur.execute('SELECT CAST(SCOPE_IDENTITY() AS INT)').fetchone()[0]
        cur.execute('''SELECT id,name,email,blood_group,organ,availability FROM Users WHERE role='Donor' AND organ=? AND availability='Available' ''',organ)
        donors=rows(cur)
        status='Potential Match Found' if donors else 'Pending'
        cur.execute('UPDATE OrganRequests SET status=? WHERE id=?',status,req_id)
        if donors:
            add_notification(conn,u['email'],f'A matching donor is available for your requested {organ}. Please contact the hospital for the next step.','match')
            for dnr in donors:
                add_notification(conn,dnr['email'],f'A recipient has requested a {organ} that matches your registered organ. Hospital verification is required.','match')
        else:
            add_notification(conn,u['email'],f'Your {organ} request is registered. No available matching donor has been found yet.','info')
        add_notification(conn,u['email'],f'Your request for a {organ} has been submitted with {urgency} priority.','request')
        log_activity(conn,'Organ Request',u['name'],u['email'],u['role'],f'{organ} requested with {urgency} urgency.')
        conn.commit(); return jsonify(message='Organ request submitted successfully.',status=status),201
    except Exception:
        conn.rollback();raise
    finally:conn.close()

@app.get('/api/my-requests')
def api_my_requests():
    conn=get_db()
    try:
        u,err=require_user(conn,'Recipient')
        if err:return jsonify(error=err[0]),err[1]
        cur=conn.cursor();cur.execute('''SELECT id, 'REQ'+RIGHT('000000'+CAST(id AS VARCHAR(6)),6) AS requestId, organ, urgency, status, requested_at AS requestedAt, notes FROM OrganRequests WHERE recipient_id=? ORDER BY id DESC''',u['id'])
        data=rows(cur)
        return jsonify(data=[clean_user(x) for x in data])
    finally:conn.close()

@app.get('/api/donor-profile')
def donor_profile():
    conn=get_db()
    try:
        u,err=require_user(conn,'Donor')
        if err:return jsonify(error=err[0]),err[1]
        return jsonify(user=u)
    finally:conn.close()

@app.get('/api/recipient-profile')
def recipient_profile():
    conn=get_db()
    try:
        u,err=require_user(conn,'Recipient')
        if err:return jsonify(error=err[0]),err[1]
        return jsonify(user=u)
    finally:conn.close()


def compatibility(d,r):
    blood = 40 if d['blood_group']==r['blood_group'] else (25 if r['blood_group']=='AB+' or d['blood_group']=='O-' else 15)
    organ = 35 if d['organ']==r['requested_organ'] else 0
    av = 25 if d['availability']=='Available' else 0
    return {'blood':blood,'organ':organ,'av':av,'total':blood+organ+av}

@app.get('/api/admin/dashboard')
def admin_dashboard():
    if not require_admin(): return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Users WHERE role='Donor'"); donors=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Users WHERE role='Recipient'"); recipients=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM OrganRequests"); requests_count=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM OrganRequests WHERE status='Potential Match Found'"); matches=cur.fetchone()[0]
        cur.execute("SELECT organ,COUNT(*) AS count FROM OrganRequests GROUP BY organ"); organ_counts={r['organ']:r['count'] for r in rows(cur)}
        cur.execute('SELECT TOP 8 activity_type AS type,name,email,role,details,date_created AS time FROM Activities ORDER BY id DESC')
        recent=rows(cur)
        return jsonify(donors=donors,recipients=recipients,requests=requests_count,matches=matches,organCounts=organ_counts,recent=[clean_user(x) for x in recent])
    finally:conn.close()

@app.get('/api/admin/donors')
def admin_donors():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute("SELECT name,email,phone,blood_group AS bloodGroup,organ,city,availability,age,gender FROM Users WHERE role='Donor' ORDER BY id DESC")
        return jsonify(data=[clean_user(x) for x in rows(cur)])
    finally:conn.close()

@app.get('/api/admin/recipients')
def admin_recipients():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute("SELECT name,email,phone,blood_group AS bloodGroup,requested_organ AS requestedOrgan,urgency,city,age,gender FROM Users WHERE role='Recipient' ORDER BY id DESC")
        return jsonify(data=[clean_user(x) for x in rows(cur)])
    finally:conn.close()

@app.get('/api/admin/requests')
def admin_requests():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute('''SELECT 'REQ'+RIGHT('000000'+CAST(r.id AS VARCHAR(6)),6) AS id,u.name AS recipientName,u.email AS recipientEmail,r.organ,r.urgency,r.status,r.requested_at AS requestedAt FROM OrganRequests r JOIN Users u ON u.id=r.recipient_id ORDER BY r.id DESC''')
        return jsonify(data=[clean_user(x) for x in rows(cur)])
    finally:conn.close()

@app.get('/api/admin/matches')
def admin_matches():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute("SELECT id,name,email,blood_group,requested_organ,urgency FROM Users WHERE role='Recipient' ORDER BY id DESC"); recips=rows(cur)
        cur.execute("SELECT id,name,email,blood_group,organ,availability,city FROM Users WHERE role='Donor' AND availability='Available'"); donors=rows(cur)
        result=[]
        for r in recips:
            ms=[]
            for d in donors:
                if d['organ']==r['requested_organ']:
                    s=compatibility(d,r); ms.append({'id':d['id'],'name':d['name'],'email':d['email'],'bloodGroup':d['blood_group'],'organ':d['organ'],'city':d['city'],'score':s})
            ms.sort(key=lambda x:x['score']['total'],reverse=True)
            result.append({'email':r['email'],'name':r['name'],'bloodGroup':r['blood_group'],'requestedOrgan':r['requested_organ'],'urgency':r['urgency'],'donors':ms})
        return jsonify(data=result)
    finally:conn.close()

@app.get('/api/admin/activities')
def admin_activities():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute('SELECT activity_type AS type,name,email,role,details,date_created AS time FROM Activities ORDER BY id DESC')
        return jsonify(data=[clean_user(x) for x in rows(cur)])
    finally:conn.close()

@app.get('/api/admin/notifications')
def admin_notifications():
    if not require_admin():return jsonify(error='Unauthorized'),401
    conn=get_db()
    try:
        cur=conn.cursor();cur.execute('SELECT activity_type AS type,name,email,role,details,date_created AS time FROM Activities ORDER BY id DESC')
        return jsonify(data=[clean_user(x) for x in rows(cur)])
    finally:conn.close()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
