# FitZone — Gym & Fitness Website

A beginner-friendly Flask + SQLite + Bootstrap 5 project. It includes public pages, hashed-password authentication, CSRF protection, memberships with a clearly labelled simulated checkout, class booking/cancellation, trainer appointments, workout logs, and a role-protected admin dashboard.

> **Payment note:** Membership checkout is a demo only. It does not charge real money. The app does not store card details. To accept real payments, integrate a provider such as Razorpay in test mode and verify orders/signatures on the backend before activating a membership.

## Requirements
- Python 3.10+
- VS Code (recommended)

## Run on Windows / VS Code
1. Extract the `fitzone` folder and open it in VS Code (`File → Open Folder`).
2. Open **Terminal → New Terminal** and run:

```bat
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

3. Open `.env` and replace `SECRET_KEY` with a long random secret for your own environment. `SEED_DEMO=1` enables demo data and creates the development admin account; use `SEED_DEMO=0` in production.
4. Run the app:

```bat
python app.py
```

5. Open http://127.0.0.1:5000.

### Development-only admin
When `SEED_DEMO=1`, the seed process creates `admin@fitzone.local` with password `Admin123!ChangeMe`. **Change/remove this account before deployment. Never enable demo seeding in production.**

## Included features
- Home, About, Gyms, Memberships, Classes, Trainers, Contact, Register, Login, User Dashboard, Admin Dashboard
- Password hashing, sessions, CSRF protection, role checks, server-side validation
- SQLite foreign keys and unique class-booking constraint
- Demo membership payments and payment history
- Class booking capacity checks and duplicate-booking prevention
- Trainer appointments with same-trainer/time conflict check
- User profile editing, workout logging, booking and payment history
- Admin: summary stats, users activate/deactivate, add gyms/trainers/plans/classes, activate/deactivate records, view bookings/payments/contact messages

## Database
The database is created automatically at `instance/fitzone.db`. To reset demo data, stop the server and delete that file, then restart with `SEED_DEMO=1`. Do not delete a database containing real user data.

## Tests
Install dependencies, then run:

```bat
python -m unittest discover -s tests -v
```

## Deployment on Render
- Push this folder to a private/public Git repository after checking `.gitignore`. Never commit `.env` or a database with private information.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Set `SECRET_KEY` to a secure random value and `SEED_DEMO=0`.
- The default SQLite file on many hosted instances may be ephemeral and can be lost on redeploy. Use a persistent disk mounted to a path such as `/var/data`, then set `DATABASE_PATH=/var/data/fitzone.db`, or use a managed production database for multi-instance/high-traffic use. Back up persistent data.
- Set `COOKIE_SECURE=1` when deployed behind HTTPS.

## Scope / honest limitations
This is a working starter project, not a production-certified gym business platform. Demo payment records are not real transactions. Trainer scheduling is a simple exact-time conflict check; add time-zone-aware scheduling, cancellation policies, email notifications, rate limiting, audit logging, backups, and production database migrations before commercial use. File uploads are not enabled, so there is no unsafe upload endpoint to exploit.
