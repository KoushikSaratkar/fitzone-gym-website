'SQLite setup and demo data for FitZone.'
import os, sqlite3
from contextlib import contextmanager
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "instance" / "fitzone.db"))

@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(seed=False):
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          phone TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
          is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS gyms (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, address TEXT NOT NULL,
          city TEXT NOT NULL, facilities TEXT NOT NULL DEFAULT '', is_active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS trainers (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, specialization TEXT NOT NULL,
          experience INTEGER NOT NULL DEFAULT 1, qualifications TEXT NOT NULL DEFAULT '',
          availability TEXT NOT NULL DEFAULT 'Contact for availability', session_price REAL NOT NULL DEFAULT 500,
          photo_url TEXT NOT NULL DEFAULT '', is_active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS membership_plans (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, price REAL NOT NULL,
          duration_days INTEGER NOT NULL, benefits TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS fitness_classes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, trainer_id INTEGER REFERENCES trainers(id),
          gym_id INTEGER REFERENCES gyms(id), starts_at TEXT NOT NULL, duration_minutes INTEGER NOT NULL DEFAULT 45,
          capacity INTEGER NOT NULL DEFAULT 15, description TEXT NOT NULL DEFAULT '', is_active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS class_bookings (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          class_id INTEGER NOT NULL REFERENCES fitness_classes(id), status TEXT NOT NULL DEFAULT 'booked',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, class_id));
        CREATE TABLE IF NOT EXISTS memberships (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          plan_id INTEGER NOT NULL REFERENCES membership_plans(id), starts_at TEXT NOT NULL,
          expires_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS payments (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          membership_id INTEGER REFERENCES memberships(id), amount REAL NOT NULL, method TEXT NOT NULL DEFAULT 'demo',
          status TEXT NOT NULL, reference TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS workout_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          workout_date TEXT NOT NULL, activity TEXT NOT NULL, minutes INTEGER NOT NULL, notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS trainer_appointments (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          trainer_id INTEGER NOT NULL REFERENCES trainers(id), appointment_at TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'booked', price REAL NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS contact_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
          subject TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        ''')
        if seed:
            if db.execute('SELECT COUNT(*) FROM gyms').fetchone()[0] == 0:
                cities=['Bengaluru','Indore','Betul','Pune','Hyderabad']
                for i,city in enumerate(cities,1):
                    db.execute('INSERT INTO gyms(name,address,city,facilities) VALUES(?,?,?,?)',
                        (f'FitZone {city}',f'{10+i} Fitness Avenue',city,'Weights, Cardio, Locker rooms, Showers'))
            if db.execute('SELECT COUNT(*) FROM trainers').fetchone()[0] == 0:
                specs=['Strength Training','Yoga','Zumba','HIIT','Weight Loss','Pilates','Cardio','Mobility','Functional Fitness','Nutrition']
                for i,s in enumerate(specs,1):
                    db.execute('INSERT INTO trainers(name,specialization,experience,qualifications,availability,session_price) VALUES(?,?,?,?,?,?)',
                        (f'Trainer {i:02d}',s,2+i%7,'Certified Fitness Professional','Mon-Sat, 7 AM - 7 PM',400+i*50))
            if db.execute('SELECT COUNT(*) FROM membership_plans').fetchone()[0] == 0:
                for row in [('Basic',999,30,'Gym access, Locker access'),('Premium',1999,30,'All Basic benefits, Group classes, Fitness assessment'),('Elite',4999,90,'All Premium benefits, 4 personal training sessions, Priority booking')]:
                    db.execute('INSERT INTO membership_plans(name,price,duration_days,benefits) VALUES(?,?,?,?)',row)
            if db.execute('SELECT COUNT(*) FROM fitness_classes').fetchone()[0] == 0:
                names=['Yoga','Zumba','Cardio Blast','Weight Training','HIIT','Pilates','Morning Yoga','Dance Fitness','Core Strength','Power HIIT','Beginner Weights','Stretch & Mobility','Pilates Flow','Zumba Express','Full Body Circuit']
                gyms=db.execute('SELECT id FROM gyms ORDER BY id').fetchall(); trainers=db.execute('SELECT id FROM trainers ORDER BY id').fetchall()
                from datetime import datetime, timedelta
                base=datetime.now().replace(second=0,microsecond=0)+timedelta(days=1)
                for i,name in enumerate(names):
                    start=(base+timedelta(days=i%7,hours=(i%5)*2)).strftime('%Y-%m-%dT%H:%M')
                    db.execute('INSERT INTO fitness_classes(name,trainer_id,gym_id,starts_at,duration_minutes,capacity,description) VALUES(?,?,?,?,?,?,?)',
                        (name,trainers[i%len(trainers)]['id'],gyms[i%len(gyms)]['id'],start,45+(i%3)*15,12+(i%4)*3,f'Coach-led {name.lower()} session for all levels.'))
            if os.getenv('SEED_DEMO','0') == '1' and not db.execute("SELECT id FROM users WHERE email='admin@fitzone.local'").fetchone():
                db.execute('INSERT INTO users(name,email,phone,password_hash,role) VALUES(?,?,?,?,?)',
                    ('FitZone Admin','admin@fitzone.local','9999999999',generate_password_hash('Admin123!ChangeMe'),'admin'))
