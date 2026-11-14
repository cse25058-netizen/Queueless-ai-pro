import os, sqlite3, secrets, hashlib, hmac, re, time, io
from datetime import datetime, date, timedelta
from functools import wraps
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, session, render_template, g, abort, send_file
from werkzeug.middleware.proxy_fix import ProxyFix

BASE=os.path.dirname(__file__); DB=os.environ.get('DATABASE_PATH',os.path.join(BASE,'queueless.db')); TZ=ZoneInfo(os.getenv('APP_TIMEZONE','Asia/Kolkata'))
app=Flask(__name__); app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1)
secret=os.getenv('SECRET_KEY')
if not secret and os.getenv('FLASK_ENV')=='production': raise RuntimeError('SECRET_KEY must be set in production')
app.secret_key=secret or 'dev-only-'+secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true',PERMANENT_SESSION_LIFETIME=timedelta(hours=8),MAX_CONTENT_LENGTH=1_000_000)
SCHEMA='''
CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY,name TEXT NOT NULL,slug TEXT UNIQUE NOT NULL,address TEXT DEFAULT '',city TEXT DEFAULT '',phone TEXT DEFAULT '',email TEXT NOT NULL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,tenant_id INTEGER,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,phone TEXT DEFAULT '',password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'patient',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(tenant_id) REFERENCES tenants(id));
CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY,tenant_id INTEGER NOT NULL,name TEXT NOT NULL,description TEXT DEFAULT '',active INTEGER DEFAULT 1,UNIQUE(tenant_id,name),FOREIGN KEY(tenant_id) REFERENCES tenants(id));
CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY,tenant_id INTEGER NOT NULL,user_id INTEGER,name TEXT NOT NULL,department_id INTEGER NOT NULL,avg_minutes INTEGER DEFAULT 12,available INTEGER DEFAULT 1,FOREIGN KEY(tenant_id) REFERENCES tenants(id),FOREIGN KEY(department_id) REFERENCES departments(id));
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY,tenant_id INTEGER NOT NULL,token TEXT UNIQUE NOT NULL,patient_id INTEGER NOT NULL,patient_name TEXT NOT NULL,doctor_id INTEGER,department_id INTEGER NOT NULL,visit_date TEXT NOT NULL,slot TEXT NOT NULL,status TEXT DEFAULT 'waiting',priority INTEGER DEFAULT 0,checked_in INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(tenant_id) REFERENCES tenants(id),FOREIGN KEY(patient_id) REFERENCES users(id),FOREIGN KEY(department_id) REFERENCES departments(id),FOREIGN KEY(doctor_id) REFERENCES doctors(id));
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY,tenant_id INTEGER,actor_id INTEGER,action TEXT,entity TEXT,entity_id INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_appt_queue ON appointments(tenant_id,visit_date,department_id,status,id);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id,role);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,tenant_id INTEGER NOT NULL,appointment_id INTEGER NOT NULL,provider TEXT NOT NULL,provider_order_id TEXT UNIQUE,status TEXT NOT NULL DEFAULT 'created',amount_paise INTEGER NOT NULL,currency TEXT NOT NULL DEFAULT 'INR',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(tenant_id) REFERENCES tenants(id),FOREIGN KEY(appointment_id) REFERENCES appointments(id));
'''
def db():
 if 'db' not in g:
  g.db=sqlite3.connect(DB,timeout=20);g.db.row_factory=sqlite3.Row;g.db.execute('PRAGMA foreign_keys=ON');g.db.execute('PRAGMA busy_timeout=20000')
 return g.db
@app.teardown_appcontext
def close_db(e):
 c=g.pop('db',None)
 if c:c.close()
def init_db():
 os.makedirs(os.path.dirname(DB) or '.',exist_ok=True);c=sqlite3.connect(DB);c.execute('PRAGMA journal_mode=WAL');c.executescript(SCHEMA);c.commit();c.close()
init_db()
def hash_pw(p):
 s=secrets.token_hex(16);return s+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),310000).hex()
def verify_pw(p,v):
 try:s,h=v.split('$',1);return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),310000).hex(),h)
 except:return False
def current():
 if not session.get('uid'):return None
 r=db().execute('SELECT id,tenant_id,name,email,phone,role FROM users WHERE id=?',(session['uid'],)).fetchone();return dict(r) if r else None
def login_required(f):
 @wraps(f)
 def w(*a,**k):
  if not current():return jsonify(error='Please sign in first.'),401
  return f(*a,**k)
 return w
def roles(*rs):
 def d(f):
  @wraps(f)
  @login_required
  def w(*a,**k):
   if current()['role'] not in rs:return jsonify(error='Not authorised.'),403
   return f(*a,**k)
  return w
 return d
def audit(action,entity,eid=None):
 u=current();db().execute('INSERT INTO audit_log(tenant_id,actor_id,action,entity,entity_id) VALUES(?,?,?,?,?)',(u['tenant_id'],u['id'],action,entity,eid));db().commit()
def valid_day(s):
 try:d=date.fromisoformat(s);today=datetime.now(TZ).date();return today<=d<=today+timedelta(days=180)
 except:return False
@app.before_request
def origin_guard():
 if request.method in ('POST','PATCH','DELETE'):
  if request.headers.get('Origin'):
   from urllib.parse import urlparse
   if urlparse(request.headers['Origin']).netloc!=request.host:return jsonify(error='Cross-origin request blocked.'),403
  if request.endpoint not in ('tenant_signup','signup','login'):
   token=session.get('csrf_token'); supplied=request.headers.get('X-CSRF-Token','')
   if not token or not hmac.compare_digest(token,supplied):return jsonify(error='Security token expired. Refresh the page and try again.'),403
@app.before_request
def ensure_csrf():
 if 'csrf_token' not in session:session['csrf_token']=secrets.token_urlsafe(32)
@app.after_request
def headers(r):
 r.headers['X-Content-Type-Options']='nosniff';r.headers['X-Frame-Options']='DENY';r.headers['Referrer-Policy']='strict-origin-when-cross-origin';r.headers['Permissions-Policy']='camera=(self), microphone=(self), geolocation=()';r.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";return r
@app.get('/')
def home():return render_template('index.html',csrf_token=session['csrf_token'])
@app.get('/health')
def health():
 try:db().execute('SELECT 1');return jsonify(status='ok',database='connected',service='QueueLess AI Multi-Hospital')
 except:return jsonify(status='error'),503
@app.get('/api/me')
def me():return jsonify(user=current())
@app.post('/api/tenant/signup')
def tenant_signup():
 x=request.get_json(silent=True) or {};name=str(x.get('hospital_name','')).strip();owner=str(x.get('owner_name','')).strip();email=str(x.get('email','')).strip().lower();pw=str(x.get('password',''));phone=str(x.get('phone',''))[:30];city=str(x.get('city','')).strip();address=str(x.get('address','')).strip()
 if len(name)<3 or len(owner)<2 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(pw)<12:return jsonify(error='Hospital, owner, valid email and a password of at least 12 characters are required.'),400
 slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')[:40] or 'hospital';c=db()
 try:
  c.execute('BEGIN IMMEDIATE');n=slug;i=2
  while c.execute('SELECT 1 FROM tenants WHERE slug=?',(n,)).fetchone():n=f'{slug}-{i}';i+=1
  tid=c.execute('INSERT INTO tenants(name,slug,address,city,phone,email) VALUES(?,?,?,?,?,?)',(name,n,address,city,phone,email)).lastrowid
  uid=c.execute("INSERT INTO users(tenant_id,name,email,phone,password,role) VALUES(?,?,?,?,?,'hospital_admin')",(tid,owner,email,phone,hash_pw(pw))).lastrowid
  for d in ['General Medicine','Cardiology','Paediatrics','Orthopaedics','Dermatology','Diagnostics','Emergency']:c.execute('INSERT INTO departments(tenant_id,name) VALUES(?,?)',(tid,d))
  c.commit();csrf=session.get('csrf_token') or secrets.token_urlsafe(32);session.clear();session['csrf_token']=csrf;session['uid']=uid;session.permanent=True
 except sqlite3.IntegrityError:return jsonify(error='An account already exists with this email.'),409
 return jsonify(user=current(),tenant={'id':tid,'name':name,'slug':n}),201
@app.post('/api/signup')
def signup():
 x=request.get_json(silent=True) or {};name=str(x.get('name','')).strip();email=str(x.get('email','')).strip().lower();pw=str(x.get('password',''));phone=str(x.get('phone',''))[:30]
 if len(name)<2 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(pw)<10:return jsonify(error='Enter a valid name/email and password of at least 10 characters.'),400
 try:uid=db().execute("INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,'patient')",(name,email,phone,hash_pw(pw))).lastrowid;db().commit()
 except sqlite3.IntegrityError:return jsonify(error='An account with this email already exists.'),409
 csrf=session.get('csrf_token') or secrets.token_urlsafe(32);session.clear();session['csrf_token']=csrf;session['uid']=uid;session.permanent=True;return jsonify(user=current()),201
@app.post('/api/login')
def login():
 x=request.get_json(silent=True) or {};em=str(x.get('email','')).strip().lower();r=db().execute('SELECT * FROM users WHERE email=?',(em,)).fetchone()
 if not r or not verify_pw(str(x.get('password','')),r['password']):return jsonify(error='Incorrect email or password.'),401
 csrf=session.get('csrf_token') or secrets.token_urlsafe(32);session.clear();session['csrf_token']=csrf;session['uid']=r['id'];session.permanent=True;return jsonify(user=current())
@app.post('/api/logout')
def logout():
 csrf=session.get('csrf_token') or secrets.token_urlsafe(32);session.clear();session['csrf_token']=csrf;return jsonify(ok=True)
@app.get('/api/hospitals')
def hospitals():
 q='%'+request.args.get('q','')[:80]+'%';rows=db().execute('SELECT id,name,slug,address,city,phone FROM tenants WHERE active=1 AND (name LIKE ? OR city LIKE ? OR address LIKE ?) ORDER BY name',(q,q,q)).fetchall();return jsonify(items=[dict(r) for r in rows])
def tenant_id():
 raw=request.args.get('tenant_id') or (request.get_json(silent=True) or {}).get('tenant_id');
 try:return int(raw) if raw else (current() or {}).get('tenant_id')
 except:return None
@app.get('/api/departments')
def departments():
 tid=tenant_id()
 if not tid:return jsonify(items=[])
 return jsonify(items=[dict(r) for r in db().execute('SELECT id,name,description FROM departments WHERE tenant_id=? AND active=1 ORDER BY name',(tid,))])
@app.get('/api/doctors')
def doctors():
 tid=tenant_id()
 if not tid:return jsonify(items=[])
 return jsonify(items=[dict(r) for r in db().execute('SELECT d.id,d.name,d.department_id,p.name department,d.avg_minutes FROM doctors d JOIN departments p ON p.id=d.department_id WHERE d.tenant_id=? AND d.available=1 ORDER BY d.name',(tid,))])
@app.post('/api/book')
@login_required
def book():
 u=current();x=request.get_json(silent=True) or {};tid=x.get('tenant_id');day=str(x.get('visit_date',''));slot=str(x.get('slot',''))[:30]
 try:tid=int(tid)
 except:return jsonify(error='Choose a hospital.'),400
 c=db();dept=c.execute('SELECT id FROM departments WHERE id=? AND tenant_id=? AND active=1',(x.get('department_id'),tid)).fetchone()
 if not dept or not valid_day(day) or not slot:return jsonify(error='Choose a valid hospital, department, date and time.'),400
 doc=None
 if x.get('doctor_id'):
  doc=c.execute('SELECT id FROM doctors WHERE id=? AND tenant_id=? AND department_id=? AND available=1',(x['doctor_id'],tid,dept['id'])).fetchone()
  if not doc:return jsonify(error='Selected doctor is not available at this hospital/department.'),400
 c.execute('BEGIN IMMEDIATE');ahead=c.execute("SELECT COUNT(*) FROM appointments WHERE tenant_id=? AND department_id=? AND visit_date=? AND status IN ('waiting','serving','booked')",(tid,dept['id'],day)).fetchone()[0];token='QL-'+datetime.now(TZ).strftime('%y%m%d')+'-'+secrets.token_hex(3).upper();aid=c.execute("INSERT INTO appointments(tenant_id,token,patient_id,patient_name,doctor_id,department_id,visit_date,slot,status) VALUES(?,?,?,?,?,?,?,?,'waiting')",(tid,token,u['id'],u['name'],doc['id'] if doc else None,dept['id'],day,slot)).lastrowid;c.commit();return jsonify(id=aid,token=token,position=ahead+1,message='Booking confirmed.'),201
@app.get('/api/my-appointments')
@login_required
def my_appointments():
 rows=db().execute('SELECT a.*,t.name hospital,d.name department,dr.name doctor FROM appointments a JOIN tenants t ON t.id=a.tenant_id JOIN departments d ON d.id=a.department_id LEFT JOIN doctors dr ON dr.id=a.doctor_id WHERE a.patient_id=? ORDER BY a.visit_date DESC,a.id DESC',(current()['id'],)).fetchall();return jsonify(items=[dict(r) for r in rows])
@app.post('/api/appointments/<int:aid>/cancel')
@login_required
def cancel(aid):
 cur=db().execute("UPDATE appointments SET status='cancelled' WHERE id=? AND patient_id=? AND status IN ('waiting','booked')",(aid,current()['id']));db().commit();return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Appointment cannot be cancelled.'),400))
@app.get('/api/queue')
def queue():
 tid=tenant_id();day=request.args.get('date') or datetime.now(TZ).date().isoformat();dep=request.args.get('department_id')
 if not tid:return jsonify(error='Select a hospital to view its queue.'),400
 sql="SELECT a.token,a.status,a.slot,d.name department,a.priority FROM appointments a JOIN departments d ON d.id=a.department_id WHERE a.tenant_id=? AND a.visit_date=? AND a.status IN ('waiting','serving','booked')";args=[tid,day]
 if dep:sql+=' AND a.department_id=?';args.append(dep)
 rows=[dict(r) for r in db().execute(sql+' ORDER BY a.priority DESC,a.id',args)];waiting=sum(r['status']=='waiting' for r in rows);serving=next((r['token'] for r in rows if r['status']=='serving'),None);return jsonify(items=rows,waiting=waiting,serving=serving,estimated_wait_minutes=waiting*12,estimate_method='waiting count × configured default 12-minute consultation; indicative only')
@app.get('/api/admin/summary')
@roles('hospital_admin','doctor')
def admin_summary():
 u=current();tid=u['tenant_id'];day=datetime.now(TZ).date().isoformat();c=db();return jsonify(hospital=c.execute('SELECT name FROM tenants WHERE id=?',(tid,)).fetchone()['name'],total=c.execute('SELECT COUNT(*) FROM appointments WHERE tenant_id=? AND visit_date=?',(tid,day)).fetchone()[0],waiting=c.execute("SELECT COUNT(*) FROM appointments WHERE tenant_id=? AND visit_date=? AND status IN ('waiting','booked')",(tid,day)).fetchone()[0],completed=c.execute("SELECT COUNT(*) FROM appointments WHERE tenant_id=? AND visit_date=? AND status='completed'",(tid,day)).fetchone()[0])
@app.get('/api/admin/appointments')
@roles('hospital_admin','doctor')
def admin_appointments():
 u=current();day=request.args.get('date') or datetime.now(TZ).date().isoformat();sql='SELECT a.id,a.token,a.patient_name,a.visit_date,a.slot,a.status,a.checked_in,d.name department,dr.name doctor FROM appointments a JOIN departments d ON d.id=a.department_id LEFT JOIN doctors dr ON dr.id=a.doctor_id WHERE a.tenant_id=? AND a.visit_date=?';args=[u['tenant_id'],day]
 if u['role']=='doctor':
  dr=db().execute('SELECT id FROM doctors WHERE user_id=? AND tenant_id=?',(u['id'],u['tenant_id'])).fetchone()
  if not dr:return jsonify(items=[])
  sql+=' AND a.doctor_id=?';args.append(dr['id'])
 rows=db().execute(sql+' ORDER BY a.id',args).fetchall();return jsonify(items=[dict(r) for r in rows])
@app.patch('/api/admin/appointments/<int:aid>')
@roles('hospital_admin','doctor')
def admin_update(aid):
 u=current();x=request.get_json(silent=True) or {};status=x.get('status')
 if status not in ('waiting','serving','completed','cancelled','no_show'):return jsonify(error='Invalid status.'),400
 if u['role']=='doctor':
  dr=db().execute('SELECT id FROM doctors WHERE user_id=? AND tenant_id=?',(u['id'],u['tenant_id'])).fetchone()
  if not dr:return jsonify(error='Doctor profile not linked.'),403
  cur=db().execute('UPDATE appointments SET status=? WHERE id=? AND tenant_id=? AND doctor_id=?',(status,aid,u['tenant_id'],dr['id']))
 else:cur=db().execute('UPDATE appointments SET status=? WHERE id=? AND tenant_id=?',(status,aid,u['tenant_id']))
 db().commit();return (jsonify(ok=True) if cur.rowcount else (jsonify(error='Appointment not found.'),404))
@app.post('/api/admin/departments')
@roles('hospital_admin')
def add_department():
 u=current();x=request.get_json(silent=True) or {};name=str(x.get('name','')).strip()
 if len(name)<2:return jsonify(error='Department name is required.'),400
 try:db().execute('INSERT INTO departments(tenant_id,name,description) VALUES(?,?,?)',(u['tenant_id'],name,str(x.get('description',''))[:200]));db().commit()
 except sqlite3.IntegrityError:return jsonify(error='Department already exists.'),409
 return jsonify(ok=True),201
@app.post('/api/admin/doctors')
@roles('hospital_admin')
def add_doctor():
 u=current();x=request.get_json(silent=True) or {};name=str(x.get('name','')).strip();email=str(x.get('email','')).strip().lower();pw=str(x.get('password',''));dep=db().execute('SELECT id FROM departments WHERE id=? AND tenant_id=?',(x.get('department_id'),u['tenant_id'])).fetchone()
 if len(name)<2 or not dep or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(pw)<12:return jsonify(error='Enter doctor name, valid email, a 12+ character temporary password and a department in this hospital.'),400
 try:
  cur=db().execute("INSERT INTO users(tenant_id,name,email,password,role) VALUES(?,?,?,?,'doctor')",(u['tenant_id'],name,email,hash_pw(pw)));uid=cur.lastrowid
  cur=db().execute('INSERT INTO doctors(tenant_id,user_id,name,department_id,avg_minutes) VALUES(?,?,?,?,?)',(u['tenant_id'],uid,name,dep['id'],max(5,min(60,int(x.get('avg_minutes',12))))));db().commit()
 except sqlite3.IntegrityError:return jsonify(error='This email is already registered.'),409
 return jsonify(id=cur.lastrowid,doctor_user_id=uid),201
@app.get('/api/admin/departments')
@roles('hospital_admin')
def admin_departments():return jsonify(items=[dict(r) for r in db().execute('SELECT * FROM departments WHERE tenant_id=? ORDER BY name',(current()['tenant_id'],))])
@app.get('/api/admin/doctors')
@roles('hospital_admin')
def admin_doctors():return jsonify(items=[dict(r) for r in db().execute('SELECT d.*,p.name department FROM doctors d JOIN departments p ON p.id=d.department_id WHERE d.tenant_id=? ORDER BY d.name',(current()['tenant_id'],))])
@app.get('/api/appointments/<int:aid>/qr')
@login_required
def appointment_qr(aid):
 u=current();row=db().execute('SELECT id,token,patient_id FROM appointments WHERE id=?',(aid,)).fetchone()
 if not row or (u['role']=='patient' and row['patient_id']!=u['id']) or (u['role']!='patient' and (u['tenant_id'] is None or not db().execute('SELECT 1 FROM appointments WHERE id=? AND tenant_id=?',(aid,u['tenant_id'])).fetchone())):return jsonify(error='Appointment not found.'),404
 try:
  import qrcode
  img=qrcode.make(row['token']);buf=io.BytesIO();img.save(buf,format='PNG');buf.seek(0);return send_file(buf,mimetype='image/png',download_name='queueless-token.png')
 except ImportError:return jsonify(error='QR support is not installed.'),503
@app.post('/api/admin/check-in')
@roles('hospital_admin','doctor')
def check_in():
 u=current();x=request.get_json(silent=True) or {};token=str(x.get('token','')).strip()[:80]
 row=db().execute("SELECT id,doctor_id FROM appointments WHERE token=? AND tenant_id=? AND visit_date=? AND status IN ('waiting','booked')",(token,u['tenant_id'],datetime.now(TZ).date().isoformat())).fetchone()
 if not row:return jsonify(error='Active token not found for today.'),404
 if u['role']=='doctor':
  dr=db().execute('SELECT id FROM doctors WHERE user_id=? AND tenant_id=?',(u['id'],u['tenant_id'])).fetchone()
  if not dr or row['doctor_id']!=dr['id']:return jsonify(error='This token is not assigned to your doctor account.'),403
 db().execute('UPDATE appointments SET checked_in=1 WHERE id=?',(row['id'],));db().commit();audit('check_in','appointment',row['id']);return jsonify(ok=True)

@app.errorhandler(500)
def internal(e):return jsonify(error='Unexpected server error. Please try again.'),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=False)
