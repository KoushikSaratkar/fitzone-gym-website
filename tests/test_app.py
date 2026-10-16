import os, tempfile, unittest, uuid
from app import app
from database import DB_PATH

class FitZoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_testing=app.config.get('TESTING')
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, SECRET_KEY='test-key')
        cls.client=app.test_client()
    def test_home_and_public_pages(self):
        for path in ['/', '/about','/gyms','/memberships','/classes','/trainers','/contact']:
            r=self.client.get(path); self.assertEqual(r.status_code,200,path)
    def test_register_login_logout_and_dashboard_protection(self):
        r=self.client.get('/dashboard'); self.assertEqual(r.status_code,302)
        r=self.client.post('/register',data={'name':'Test Person','email':f'test-{uuid.uuid4().hex}@example.com','phone':'9876543210','password':'StrongPass123','confirm_password':'StrongPass123'},follow_redirects=True)
        self.assertEqual(r.status_code,200)
        r=self.client.post('/login',data={'email':f'test-{uuid.uuid4().hex}@example.com','password':'StrongPass123'},follow_redirects=True)
        self.assertEqual(r.status_code,200); self.assertIn(b'Your dashboard',r.data)
        r=self.client.post('/logout',follow_redirects=True); self.assertEqual(r.status_code,200)
    def test_demo_membership_requires_login(self):
        with app.app_context():
            from database import get_db
            with get_db() as db: plan=db.execute('SELECT id FROM membership_plans LIMIT 1').fetchone()
        r=self.client.post(f'/membership/buy/{plan[0]}'); self.assertEqual(r.status_code,302)

if __name__=='__main__': unittest.main()
