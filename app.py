import os, re, secrets
from datetime import datetime, timedelta, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()
from database import get_db, init_db
app=Flask(__name__, instance_relative_config=True)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY','dev-only-change-me'), SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','0')=='1')
CSRFProtect(app)

@app.context_processor
def inject_globals():
    return {'current_user': current_user(), 'year': datetime.now().year}

def current_user():
    uid=session.get('user_id')
    if not uid: return None
    with get_db() as db: return db.execute('SELECT id,name,email,phone,role,is_active FROM users WHERE id=?',(uid,)).fetchone()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not current_user(): flash('Please log in to continue.','warning'); return redirect(url_for('login',next=request.path))
        return fn(*a,**kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        user=current_user()
        if not user or user['role']!='admin': abort(403)
        return fn(*a,**kw)
    return wrapped

def valid_email(email): return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email or ''))

@app.route('/')
def home():
    with get_db() as db:
        plans=db.execute('SELECT * FROM membership_plans WHERE is_active=1 ORDER BY price').fetchall()
        classes=db.execute('''SELECT c.*,t.name trainer,g.city gym_city FROM fitness_classes c LEFT JOIN trainers t ON t.id=c.trainer_id LEFT JOIN gyms g ON g.id=c.gym_id WHERE c.is_active=1 ORDER BY c.starts_at LIMIT 3''').fetchall()
        trainers=db.execute('SELECT * FROM trainers WHERE is_active=1 ORDER BY id LIMIT 3').fetchall()
    return render_template('index.html',plans=plans,classes=classes,trainers=trainers)

@app.route('/about')
def about(): return render_template('about.html')
@app.route('/gyms')
def gyms():
    q=request.args.get('q','').strip()
    with get_db() as db: rows=db.execute('SELECT * FROM gyms WHERE is_active=1 AND (city LIKE ? OR name LIKE ? OR address LIKE ?) ORDER BY city', (f'%{q}%',)*3).fetchall()
    return render_template('gyms.html',gyms=rows,q=q)
@app.route('/memberships')
def memberships():
    with get_db() as db: plans=db.execute('SELECT * FROM membership_plans WHERE is_active=1 ORDER BY price').fetchall()
    return render_template('memberships.html',plans=plans)
@app.route('/classes')
def classes():
    q=request.args.get('q','').strip()
    with get_db() as db:
        rows=db.execute('''SELECT c.*,t.name trainer,g.name gym_name,g.city, (SELECT COUNT(*) FROM class_bookings b WHERE b.class_id=c.id AND b.status='booked') booked_count FROM fitness_classes c LEFT JOIN trainers t ON t.id=c.trainer_id LEFT JOIN gyms g ON g.id=c.gym_id WHERE c.is_active=1 AND (c.name LIKE ? OR t.name LIKE ? OR g.city LIKE ?) ORDER BY c.starts_at''',(f'%{q}%',)*3).fetchall()
    return render_template('classes.html',classes=rows,q=q)
@app.route('/trainers')
def trainers():
    with get_db() as db: rows=db.execute('SELECT * FROM trainers WHERE is_active=1 ORDER BY name').fetchall()
    return render_template('trainers.html',trainers=rows)

@app.route('/contact',methods=['GET','POST'])
def contact():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); subject=request.form.get('subject','').strip(); message=request.form.get('message','').strip()
        if not name or not valid_email(email) or not subject or len(message)<10:
            flash('Please complete all fields and enter a valid email. Message must be at least 10 characters.','danger')
        else:
            with get_db() as db: db.execute('INSERT INTO contact_messages(name,email,subject,message) VALUES(?,?,?,?)',(name,email,subject,message))
            flash('Thanks! Your message has been saved. Our team will contact you.','success'); return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); phone=request.form.get('phone','').strip(); password=request.form.get('password',''); confirm=request.form.get('confirm_password','')
        errors=[]
        if len(name)<2: errors.append('Name must contain at least 2 characters.')
        if not valid_email(email): errors.append('Enter a valid email address.')
        if not re.fullmatch(r'[0-9+() -]{8,18}',phone): errors.append('Enter a valid phone number.')
        if len(password)<8: errors.append('Password must be at least 8 characters.')
        if password!=confirm: errors.append('Passwords do not match.')
        with get_db() as db:
            if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): errors.append('An account with this email already exists.')
            if errors:
                for e in errors: flash(e,'danger')
            else:
                db.execute('INSERT INTO users(name,email,phone,password_hash) VALUES(?,?,?,?)',(name,email,phone,generate_password_hash(password)))
                flash('Account created. You can now log in.','success'); return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        with get_db() as db: user=db.execute('SELECT * FROM users WHERE email=? AND is_active=1',(email,)).fetchone()
        if user and check_password_hash(user['password_hash'],password):
            session.clear(); session['user_id']=user['id']; flash(f"Welcome back, {user['name']}!",'success')
            dest=request.args.get('next','')
            if dest.startswith('/') and not dest.startswith('//'): return redirect(dest)
            return redirect(url_for('admin_dashboard' if user['role']=='admin' else 'dashboard'))
        flash('Invalid email or password, or the account is inactive.','danger')
    return render_template('login.html')
@app.route('/logout',methods=['POST'])
def logout(): session.clear(); flash('You have been logged out.','success'); return redirect(url_for('home'))

@app.route('/membership/buy/<int:plan_id>',methods=['POST'])
@login_required
def buy_membership(plan_id):
    with get_db() as db:
        plan=db.execute('SELECT * FROM membership_plans WHERE id=? AND is_active=1',(plan_id,)).fetchone()
        if not plan: abort(404)
        # Explicit demo checkout: no real money is charged.
        start=date.today(); expiry=start+timedelta(days=plan['duration_days'])
        db.execute("UPDATE memberships SET status='expired' WHERE user_id=? AND status='active'",(current_user()['id'],))
        cur=db.execute('INSERT INTO memberships(user_id,plan_id,starts_at,expires_at,status) VALUES(?,?,?,?,?)',(current_user()['id'],plan_id,start.isoformat(),expiry.isoformat(),'active'))
        mid=cur.lastrowid
        db.execute('INSERT INTO payments(user_id,membership_id,amount,method,status,reference) VALUES(?,?,?,?,?,?)',(current_user()['id'],mid,plan['price'],'demo','demo_success','DEMO-'+secrets.token_hex(8).upper()))
    flash('Demo purchase successful. No real payment was taken.','success'); return redirect(url_for('dashboard'))

@app.route('/membership/cancel',methods=['POST'])
@login_required
def cancel_membership():
    # Cancellation stops the current membership immediately; prior payment history is retained.
    with get_db() as db:
        cur=db.execute("UPDATE memberships SET status='cancelled' WHERE user_id=? AND status='active'",(current_user()['id'],))
    flash('Membership cancelled.' if cur.rowcount else 'You do not have an active membership.', 'success' if cur.rowcount else 'warning')
    return redirect(url_for('dashboard'))

@app.route('/classes/book/<int:class_id>',methods=['POST'])
@login_required
def book_class(class_id):
    with get_db() as db:
        cls=db.execute('SELECT * FROM fitness_classes WHERE id=? AND is_active=1',(class_id,)).fetchone()
        if not cls: abort(404)
        if datetime.fromisoformat(cls['starts_at']) < datetime.now(): flash('This class has already started.','warning')
        else:
            count=db.execute("SELECT COUNT(*) FROM class_bookings WHERE class_id=? AND status='booked'",(class_id,)).fetchone()[0]
            existing=db.execute('SELECT id,status FROM class_bookings WHERE user_id=? AND class_id=?',(current_user()['id'],class_id)).fetchone()
            if existing and existing['status']=='booked': flash('You already booked this class.','warning')
            elif count>=cls['capacity']: flash('Sorry, this class is full.','danger')
            elif existing: db.execute("UPDATE class_bookings SET status='booked',created_at=CURRENT_TIMESTAMP WHERE id=?",(existing['id'],)); flash('Class booking confirmed.','success')
            else: db.execute('INSERT INTO class_bookings(user_id,class_id) VALUES(?,?)',(current_user()['id'],class_id)); flash('Class booking confirmed.','success')
    return redirect(request.referrer or url_for('classes'))
@app.route('/classes/cancel/<int:booking_id>',methods=['POST'])
@login_required
def cancel_class(booking_id):
    with get_db() as db:
        cur=db.execute("UPDATE class_bookings SET status='cancelled' WHERE id=? AND user_id=? AND status='booked'",(booking_id,current_user()['id']))
        flash('Booking cancelled.' if cur.rowcount else 'Booking not found.', 'success' if cur.rowcount else 'warning')
    return redirect(url_for('dashboard'))

@app.route('/trainers/book/<int:trainer_id>',methods=['POST'])
@login_required
def book_trainer(trainer_id):
    when=request.form.get('appointment_at','').strip()
    try: dt=datetime.fromisoformat(when)
    except ValueError: dt=None
    if not dt or dt<=datetime.now(): flash('Choose a valid future appointment time.','danger'); return redirect(url_for('trainers'))
    with get_db() as db:
        tr=db.execute('SELECT * FROM trainers WHERE id=? AND is_active=1',(trainer_id,)).fetchone()
        if not tr: abort(404)
        clash=db.execute("SELECT 1 FROM trainer_appointments WHERE trainer_id=? AND appointment_at=? AND status='booked'",(trainer_id,dt.isoformat(timespec='minutes'))).fetchone()
        if clash: flash('That trainer time is already booked. Choose another time.','warning')
        else:
            db.execute('INSERT INTO trainer_appointments(user_id,trainer_id,appointment_at,price) VALUES(?,?,?,?)',(current_user()['id'],trainer_id,dt.isoformat(timespec='minutes'),tr['session_price']))
            flash('Training appointment booked. Payment is not collected in this demo.','success')
    return redirect(url_for('dashboard'))
@app.route('/trainer-appointments/cancel/<int:appointment_id>',methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    with get_db() as db: cur=db.execute("UPDATE trainer_appointments SET status='cancelled' WHERE id=? AND user_id=? AND status='booked'",(appointment_id,current_user()['id']))
    flash('Appointment cancelled.' if cur.rowcount else 'Appointment not found.','success' if cur.rowcount else 'warning'); return redirect(url_for('dashboard'))

@app.route('/dashboard',methods=['GET','POST'])
@login_required
def dashboard():
    user=current_user()
    if request.method=='POST':
        action=request.form.get('action')
        if action=='profile':
            name=request.form.get('name','').strip(); phone=request.form.get('phone','').strip()
            if len(name)<2 or not re.fullmatch(r'[0-9+() -]{8,18}',phone): flash('Enter a valid name and phone number.','danger')
            else:
                with get_db() as db: db.execute('UPDATE users SET name=?,phone=? WHERE id=?',(name,phone,user['id']))
                flash('Profile updated.','success')
            return redirect(url_for('dashboard'))
        if action=='workout':
            activity=request.form.get('activity','').strip(); day=request.form.get('workout_date',''); notes=request.form.get('notes','').strip()
            try: mins=int(request.form.get('minutes','0'))
            except ValueError: mins=0
            if not activity or not day or mins<1 or mins>1440: flash('Enter a valid workout and duration.','danger')
            else:
                with get_db() as db: db.execute('INSERT INTO workout_logs(user_id,workout_date,activity,minutes,notes) VALUES(?,?,?,?,?)',(user['id'],day,activity,mins,notes))
                flash('Workout saved.','success')
            return redirect(url_for('dashboard'))
    with get_db() as db:
        member=db.execute('''SELECT m.*,p.name plan_name FROM memberships m JOIN membership_plans p ON p.id=m.plan_id WHERE m.user_id=? AND m.status='active' ORDER BY m.id DESC LIMIT 1''',(user['id'],)).fetchone()
        bookings=db.execute('''SELECT b.id booking_id,b.status,c.name,c.starts_at,c.duration_minutes,g.city FROM class_bookings b JOIN fitness_classes c ON c.id=b.class_id LEFT JOIN gyms g ON g.id=c.gym_id WHERE b.user_id=? ORDER BY c.starts_at DESC''',(user['id'],)).fetchall()
        appointments=db.execute('''SELECT a.*,t.name trainer,t.specialization FROM trainer_appointments a JOIN trainers t ON t.id=a.trainer_id WHERE a.user_id=? ORDER BY a.appointment_at DESC''',(user['id'],)).fetchall()
        payments=db.execute('SELECT * FROM payments WHERE user_id=? ORDER BY id DESC',(user['id'],)).fetchall()
        workouts=db.execute('SELECT * FROM workout_logs WHERE user_id=? ORDER BY workout_date DESC,id DESC',(user['id'],)).fetchall()
    return render_template('dashboard.html',user=user,membership=member,bookings=bookings,appointments=appointments,payments=payments,workouts=workouts)

@app.route('/admin',methods=['GET','POST'])
@admin_required
def admin_dashboard():
    if request.method=='POST':
        action=request.form.get('action')
        try:
            with get_db() as db:
                if action=='gym': db.execute('INSERT INTO gyms(name,address,city,facilities) VALUES(?,?,?,?)',(request.form['name'].strip(),request.form['address'].strip(),request.form['city'].strip(),request.form.get('facilities','').strip()))
                elif action=='trainer': db.execute('INSERT INTO trainers(name,specialization,experience,qualifications,availability,session_price) VALUES(?,?,?,?,?,?)',(request.form['name'].strip(),request.form['specialization'].strip(),int(request.form.get('experience',1)),request.form.get('qualifications','').strip(),request.form.get('availability','').strip(),float(request.form.get('session_price',500))))
                elif action=='plan': db.execute('INSERT INTO membership_plans(name,price,duration_days,benefits) VALUES(?,?,?,?)',(request.form['name'].strip(),float(request.form['price']),int(request.form['duration_days']),request.form['benefits'].strip()))
                elif action=='class': db.execute('INSERT INTO fitness_classes(name,trainer_id,gym_id,starts_at,duration_minutes,capacity,description) VALUES(?,?,?,?,?,?,?)',(request.form['name'].strip(),int(request.form['trainer_id']),int(request.form['gym_id']),request.form['starts_at'],int(request.form['duration_minutes']),int(request.form['capacity']),request.form.get('description','').strip()))
                elif action=='toggle_user': db.execute('UPDATE users SET is_active=1-is_active WHERE id=? AND role!=\'admin\'',(int(request.form['user_id']),))
                elif action=='toggle_gym': db.execute('UPDATE gyms SET is_active=1-is_active WHERE id=?',(int(request.form['id']),))
                elif action=='toggle_trainer': db.execute('UPDATE trainers SET is_active=1-is_active WHERE id=?',(int(request.form['id']),))
                elif action=='toggle_class': db.execute('UPDATE fitness_classes SET is_active=1-is_active WHERE id=?',(int(request.form['id']),))
                elif action=='toggle_plan': db.execute('UPDATE membership_plans SET is_active=1-is_active WHERE id=?',(int(request.form['id']),))
            flash('Admin change saved.','success')
        except (ValueError,KeyError) as e: flash('Please check the submitted values.','danger')
        except Exception: flash('Could not save that change. Check for duplicate plan names and valid references.','danger')
        return redirect(url_for('admin_dashboard'))
    with get_db() as db:
        stats={k:db.execute(q).fetchone()[0] for k,q in {'users':'SELECT COUNT(*) FROM users WHERE role=\'user\'','gyms':'SELECT COUNT(*) FROM gyms','trainers':'SELECT COUNT(*) FROM trainers','classes':'SELECT COUNT(*) FROM fitness_classes','bookings':"SELECT COUNT(*) FROM class_bookings WHERE status='booked'",'revenue':"SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='demo_success'"}.items()}
        users=db.execute('SELECT id,name,email,phone,is_active,created_at FROM users ORDER BY id DESC').fetchall()
        gyms=db.execute('SELECT * FROM gyms ORDER BY city').fetchall(); trainers=db.execute('SELECT * FROM trainers ORDER BY name').fetchall()
        plans=db.execute('SELECT * FROM membership_plans ORDER BY price').fetchall()
        classes=db.execute('SELECT c.*,t.name trainer,g.name gym_name FROM fitness_classes c LEFT JOIN trainers t ON t.id=c.trainer_id LEFT JOIN gyms g ON g.id=c.gym_id ORDER BY starts_at DESC').fetchall()
        bookings=db.execute('SELECT b.id,b.status,u.name user_name,c.name class_name,c.starts_at FROM class_bookings b JOIN users u ON u.id=b.user_id JOIN fitness_classes c ON c.id=b.class_id ORDER BY b.id DESC LIMIT 100').fetchall()
        payments=db.execute('SELECT p.*,u.name user_name FROM payments p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 100').fetchall()
        messages=db.execute('SELECT * FROM contact_messages ORDER BY id DESC LIMIT 50').fetchall()
    return render_template('admin_dashboard.html',stats=stats,users=users,gyms=gyms,trainers=trainers,plans=plans,classes=classes,bookings=bookings,payments=payments,messages=messages)

@app.errorhandler(403)
def forbidden(e): return render_template('error.html',code=403,message='You do not have permission to view this page.'),403
@app.errorhandler(404)
def not_found(e): return render_template('error.html',code=404,message='The page or record you requested was not found.'),404

with app.app_context(): init_db(seed=True)
if __name__=='__main__': app.run(debug=os.getenv('FLASK_DEBUG','0')=='1')
